"""Unattended local production run for one plan: sheets -> plates -> keyframes -> clips -> cut.

Usage (from the repository root):
  uv run --python 3.12 python -m scripts.mvvm_gen.run <stage|all> scripts/mvvm_gen/plans/i-ran-pilot.json [--force ID ...]

Every artifact is written under .runtime/gen/<plan>/ and recorded in manifest.json
(prompt id, seed, graph hash, elapsed seconds). Existing artifacts are reused, so an
interrupted run resumes where it stopped. One GPU job runs at a time.
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

from . import comfy, graphs, timing

STAGES = ("sheets", "keyframes", "clips", "check", "cut")
SWARM_HISTORY = os.environ.get("MVVM_SWARM_HISTORY", r"D:\output\local\MVVM")


def gpu_memory_mib():
    """Whole-device used memory after a job (includes other processes); None if unavailable."""
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=10).stdout
        return int(out.split()[0])
    except (OSError, ValueError, IndexError, subprocess.SubprocessError):
        return None


def seed_for(*parts):
    return int(hashlib.sha256("/".join(parts).encode()).hexdigest()[:12], 16)


class Run:
    def __init__(self, plan_path, force=()):
        with open(plan_path, encoding="utf-8") as fh:
            self.plan = json.load(fh)
        self.name = self.plan["name"]
        self.root = os.path.join(".runtime", "gen", self.name)
        self.manifest_path = os.path.join(self.root, "manifest.json")
        self.manifest = {}
        if os.path.exists(self.manifest_path):
            with open(self.manifest_path, encoding="utf-8") as fh:
                self.manifest = json.load(fh)
        self.force = set(force)
        self.uploads = {}

    def save_manifest(self):
        os.makedirs(self.root, exist_ok=True)
        tmp = self.manifest_path + ".part"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(self.manifest, fh, indent=2)
        os.replace(tmp, self.manifest_path)

    def path(self, *parts):
        return os.path.join(self.root, *parts)

    def upload(self, local):
        if local not in self.uploads:
            self.uploads[local] = comfy.upload_image(local)
        return self.uploads[local]

    def generate(self, key, graph, dest, seed):
        """Run one graph unless `dest` already exists; download its first output to `dest`."""
        if os.path.exists(dest) and key not in self.force:
            return dest
        digest = hashlib.sha256(json.dumps(graph, sort_keys=True).encode()).hexdigest()[:16]
        print(f"[{key}] submitting ({digest})", flush=True)
        started = time.monotonic()
        prompt_id = comfy.submit(graph)
        try:
            record = comfy.wait(prompt_id, timeout=self.plan.get("job_timeout_s", 1200))
        except comfy.LostPrompt as err:
            # A backend crash/restart drops queued work; wait for SwarmUI to bring 7821 back, then resubmit once.
            print(f"[{key}] {err}; resubmitting once", flush=True)
            comfy.wait_for_backend()  # uploads are content-named in the persistent input dir
            prompt_id = comfy.submit(graph)
            record = comfy.wait(prompt_id, timeout=self.plan.get("job_timeout_s", 1200))
        files = comfy.output_files(record)
        if not files:
            raise comfy.ComfyError(f"{key}: prompt {prompt_id} completed without saved output")
        comfy.download(files[0], dest)
        elapsed = round(time.monotonic() - started, 1)
        models = sorted({v for n in graph.values() for k, v in n["inputs"].items()
                         if k in ("unet_name", "clip_name", "vae_name", "lora_name") and isinstance(v, str)})
        self.manifest[key] = {"prompt_id": prompt_id, "seed": seed, "graph": digest, "elapsed_s": elapsed,
                              "models": models, "gpu_mib_after": gpu_memory_mib(), "backend": comfy.BASE,
                              "output": dest, "status": "generated_unverified"}
        self.save_manifest()
        mirror = os.path.join(SWARM_HISTORY, self.name, os.path.basename(os.path.dirname(dest)))
        try:
            os.makedirs(mirror, exist_ok=True)
            shutil.copy2(dest, os.path.join(mirror, os.path.basename(dest)))
        except OSError as err:
            print(f"[{key}] Swarm history copy skipped: {err}", flush=True)
        print(f"[{key}] done in {elapsed}s -> {dest}", flush=True)
        return dest

    # --- stages ---------------------------------------------------------------

    def panel(self, cid, view):
        return self.path("sheets", cid, f"{view}.png")

    def sheets(self):
        """Build each sheet from separately rendered panels so every view gets full resolution.

        A three-quarter-length anchor (not part of the sheet) fixes identity and outfit; the
        close-up and each full-body view are rendered from that anchor alone (never by
        re-editing a whole sheet, and never with a second reference, both of which made Qwen 2.1
        drift into mottled skin and noisy backgrounds). Panels are then joined side by side.
        """
        spec = self.plan["sheet"]
        height = spec["height"]
        for cid, char in self.plan["characters"].items():
            seed = seed_for(self.name, "sheet", cid)
            who = f"{char['identity']} Outfit: {char['look']}"
            # Qwen 2.1 breaks up (mottled skin, noisy grain) above ~1.6 MP, so every render stays
            # under that and the close-up is resampled to sheet height afterwards.
            aw, ah = spec["anchor_size"]
            self.generate(f"sheet:{cid}:anchor", graphs.qwen21_image(
                f"{spec['anchor']} The person is the one from <image1>: {who}",
                [self.upload(char["identity_ref"])], aw, ah, seed,
                f"mvvm/{self.name}/sheet-{cid}-anchor"), self.panel(cid, "anchor"), seed)
            anchor = self.upload(self.panel(cid, "anchor"))
            for view in ("closeup", "front", "back", "side"):
                w, h = spec["closeup_size"] if view == "closeup" else (spec["body_width"], height)
                self.generate(f"sheet:{cid}:{view}", graphs.qwen21_image(
                    f"{spec[view]} The exact same person as <image1>: identical face, skin tone, hair and body. {who}",
                    [anchor], w, h, seed, f"mvvm/{self.name}/sheet-{cid}-{view}"),
                    self.panel(cid, view), seed)
            portrait = self.panel(cid, "portrait")
            if not os.path.exists(portrait) or f"sheet:{cid}:closeup" in self.force:
                subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", self.panel(cid, "closeup"),
                                "-vf", f"scale=-2:{height}:flags=lanczos", portrait], check=True)
            sheet = self.path("sheets", f"{cid}.png")
            if not os.path.exists(sheet) or any(k.startswith(f"sheet:{cid}") for k in self.force):
                panels = [portrait] + [self.panel(cid, v) for v in ("front", "back", "side")]
                args = [a for p in panels for a in ("-i", p)]
                subprocess.run(["ffmpeg", "-y", "-v", "error", *args, "-filter_complex",
                                "".join(f"[{i}:v]" for i in range(4)) + "hstack=inputs=4", sheet], check=True)
                print(f"[sheet:{cid}] joined -> {sheet}", flush=True)

    def plates(self):
        w, h = self.plan["frame_size"]
        for lid, loc in self.plan["locations"].items():
            seed = seed_for(self.name, "plate", lid)
            prompt = f"{loc['prompt']} {self.plan['style']} No people in the foreground, no text."
            self.generate(f"plate:{lid}", graphs.qwen21_image(prompt, [], w, h, seed, f"mvvm/{self.name}/plate-{lid}"),
                          self.path("plates", f"{lid}.png"), seed)

    def keyframes(self):
        """Character references only; every background is generated fresh from text.

        Passing a location plate as a reference made every shot reuse the same copied
        background and pasted the cast in at the wrong scale.
        """
        w, h = self.plan.get("keyframe_size", self.plan["frame_size"])
        unet = self.plan.get("keyframe_unet")
        for shot in self.plan["shots"]:
            sid = shot["id"]
            seed = seed_for(self.name, "keyframe", sid)
            refs, names = [], []
            for cid in shot.get("characters", []):
                # The close-up carries the face; the front panel carries the whole outfit.
                panels = self.plan["characters"][cid].get("ref_panels", ["portrait", "front"])
                refs += [self.upload(self.panel(cid, p)) for p in panels]
                tags = " and ".join(f"<image{len(refs) - len(panels) + i + 1}>" for i in range(len(panels)))
                names.append(f"{tags} show {self.plan['characters'][cid]['name']}")
            cast = ("; ".join(names) + " (keep exactly the same face, skin tone, hair and outfit). ") if names else ""
            background = self.plan["locations"][shot["location"]]["prompt"]
            prompt = (f"{cast}{shot['framing']} Shot: {shot['still']} Background: {background} "
                      f"{self.plan['style']} {self.plan.get('keyframe_rules', '') if names else ''} "
                      "Single cinematic film still, not a character sheet, no text.")
            self.generate(f"keyframe:{sid}", graphs.qwen21_image(prompt, refs, w, h, seed, f"mvvm/{self.name}/kf-{sid}",
                                                                 unet=unet),
                          self.path("keyframes", f"{sid}.png"), seed)

    def clips(self):
        if self.plan.get("clip_mode") == "ref2v":
            return self.ref_clips()
        w, h = self.plan["frame_size"]
        frames = self.shot_frames()
        for shot, count in zip(self.plan["shots"], frames):
            sid = shot["id"]
            seed = seed_for(self.name, "clip", sid)
            prompt = graphs.h3_prompt(shot["still"], shot["motion"], shot["camera"])
            graph = graphs.h3_i2v(self.upload(self.path("keyframes", f"{sid}.png")), prompt, seed,
                                  f"mvvm/{self.name}/clip-{sid}", w, h, count / timing.FPS + 0.5,
                                  steps=self.plan.get("clip_steps", 20))
            self.generate(f"clip:{sid}", graph, self.path("clips", f"{sid}.mp4"), seed)

    def ref_clips(self):
        """H3 reference-to-video straight from the character sheet panels (no composited keyframe)."""
        w, h = self.plan["frame_size"]
        extras = self.plan.get("extras", "")
        for shot, count in zip(self.plan["shots"], self.shot_frames()):
            sid = shot["id"]
            seed = seed_for(self.name, "clip", sid)
            refs, subjects = [], []
            for cid in shot.get("characters", []):
                char = self.plan["characters"][cid]
                panels = char.get("ref_panels", ["portrait", "front"])
                start = len(refs) + 1
                refs += [self.upload(self.panel(cid, p)) for p in panels]
                subjects.append((f"{char['name']}. {char['identity']} Outfit: {char['look']}",
                                 list(range(start, len(refs) + 1))))
            location = self.plan["locations"][shot["location"]]
            background = location["prompt"]
            crowd = extras if location.get("crowd", True) else "No other people are anywhere in the shot."
            summary = f"One uninterrupted music-video shot. {shot['summary']}"
            description = (f"{shot['framing']} {shot['still']} {shot['motion']} {shot['camera']} "
                           f"Background: {background} {crowd if subjects else ''} "
                           "There is no cut, zoom, scene change, text overlay or logo.")
            hints = [""] + self.plan.get("variation_hints", [])
            for take in range(shot.get("takes", self.plan.get("takes", 1))):
                # Take 0 is the base; later takes re-roll the seed and nudge camera/motion wording.
                prompt = graphs.h3_ref2v_prompt(
                    subjects, summary, self.plan["style"], f"{description} {hints[take % len(hints)]}".strip(),
                    self.plan.get("soundscape", "Muffled festival bass and crowd ambience, no dialogue."))
                seconds = min(count / timing.FPS + 0.5, self.plan.get("max_clip_seconds", 12))
                graph = graphs.h3_ref2v(refs, prompt, seed + take, f"mvvm/{self.name}/clip-{sid}-t{take}", w, h,
                                        seconds, steps=self.plan.get("clip_steps", 20),
                                        loras=[tuple(x) for x in self.plan.get("clip_loras", [])],
                                        sampler=self.plan.get("clip_sampler", "res_multistep"))
                self.generate(self.take_key(sid, take), graph, self.take_path(sid, take), seed + take)

    @staticmethod
    def take_key(sid, take):
        return f"clip:{sid}" if take == 0 else f"clip:{sid}:t{take}"

    def take_path(self, sid, take):
        return self.path("clips", f"{sid}.mp4" if take == 0 else f"{sid}-t{take}.mp4")

    def check(self):
        """Technical self-check of each picked take; writes check/report.json and a contact sheet.

        Mechanical only (coverage, resolution, black and frozen spans). It does not judge
        identity or creative quality; those stay with visual review.
        """
        report, rows = {}, []
        w, h = self.plan["frame_size"]
        for shot, count in zip(self.plan["shots"], self.shot_frames()):
            sid, take = shot["id"], shot.get("pick", 0)
            clip = self.take_path(sid, take)
            if not os.path.exists(clip):
                report[sid] = {"status": "missing", "clip": clip}
                continue
            probe = json.loads(subprocess.run(
                ["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames", "-show_entries",
                 "stream=width,height,r_frame_rate,nb_read_frames", "-of", "json", clip],
                check=True, capture_output=True, text=True).stdout)["streams"][0]
            used = f"trim=end_frame={count}"
            scan = subprocess.run(["ffmpeg", "-v", "info", "-i", clip, "-vf",
                                   f"{used},blackdetect=d=0.25:pix_th=0.06,freezedetect=n=0.002:d=1.0", "-an", "-f", "null", "-"],
                                  capture_output=True, text=True).stderr
            black = scan.count("black_start")
            frozen = scan.count("freeze_start")
            frames = int(probe["nb_read_frames"])
            problems = [p for p, bad in (("short", frames < count), ("resolution", (probe["width"], probe["height"]) != (w, h)),
                                         ("black", black > 0), ("frozen", frozen > 0)) if bad]
            report[sid] = {"take": take, "clip": clip, "frames": frames, "needed": count, "fps": probe["r_frame_rate"],
                           "size": [probe["width"], probe["height"]], "black_spans": black, "frozen_spans": frozen,
                           "status": "pass" if not problems else "flagged", "problems": problems}
            row = self.path("check", f"{sid}.png")
            os.makedirs(os.path.dirname(row), exist_ok=True)
            picks = "+".join(f"eq(n\\,{int(count * f)})" for f in (0.05, 0.5, 0.95))
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", clip, "-vf",
                            f"select='{picks}',scale=426:-2,tile=3x1", "-frames:v", "1", row], check=True)
            rows.append(row)
        with open(self.path("check", "report.json"), "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2)
        if rows:
            args = [a for r in rows for a in ("-i", r)]
            subprocess.run(["ffmpeg", "-y", "-v", "error", *args, "-filter_complex",
                            "".join(f"[{i}:v]" for i in range(len(rows))) + f"vstack=inputs={len(rows)}",
                            self.path("check", "contact-sheet.jpg")], check=True)
        flagged = {k: v.get("problems", v["status"]) for k, v in report.items() if v["status"] != "pass"}
        print(f"[check] {len(report) - len(flagged)}/{len(report)} pass; flagged: {flagged or 'none'}", flush=True)

    def shot_frames(self):
        return timing.shot_frames([s["bars"] for s in self.plan["shots"]], self.plan["song"]["bpm"])

    def passage_start(self):
        song = self.plan["song"]
        if "start" in song:
            return float(song["start"])
        env, rate = timing.load_envelope(song["audio"])
        phase = timing.downbeat_phase(env, rate, song["bpm"])
        bars = sum(s["bars"] for s in self.plan["shots"])
        start = timing.loudest_window(env, rate, song["bpm"], bars, phase)
        self.manifest["passage"] = {"phase_s": round(phase, 4), "start_s": round(start, 4), "bars": bars}
        self.save_manifest()
        return start

    def cut(self):
        out_w, out_h = self.plan.get("delivery_size", [1280, 720])
        frames = self.shot_frames()
        start = self.passage_start()
        total = sum(frames) / timing.FPS
        inputs, filters = [], []
        for i, (shot, count) in enumerate(zip(self.plan["shots"], frames)):
            clip = self.take_path(shot["id"], shot.get("pick", 0))
            inputs += ["-i", clip]
            filters.append(
                f"[{i}:v]fps={timing.FPS},scale={out_w}:{out_h}:force_original_aspect_ratio=increase,"
                f"crop={out_w}:{out_h},setsar=1,trim=end_frame={count},setpts=PTS-STARTPTS[v{i}]")
        n = len(frames)
        filters.append("".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[v]")
        inputs += ["-ss", f"{start:.4f}", "-t", f"{total:.4f}", "-i", self.plan["song"]["audio"]]
        dest = self.path("cut", f"{self.name}.mp4")
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        subprocess.run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", ";".join(filters),
                        "-map", "[v]", "-map", f"{n}:a", "-c:v", "libx264", "-crf", "17", "-preset", "slow",
                        "-pix_fmt", "yuv420p", "-r", str(timing.FPS), "-c:a", "aac", "-b:a", "320k",
                        "-shortest", "-movflags", "+faststart", dest], check=True)
        self.manifest["cut"] = {"output": dest, "start_s": round(start, 4), "duration_s": round(total, 4),
                                "frames": sum(frames), "status": "assembled_unverified"}
        self.save_manifest()
        print(f"[cut] {dest} ({total:.2f}s from {start:.2f}s)", flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("stage", choices=(*STAGES, "all"))
    parser.add_argument("plan")
    parser.add_argument("--force", nargs="*", default=[], help="manifest keys to regenerate, e.g. keyframe:s03")
    args = parser.parse_args(argv)
    run = Run(args.plan, args.force)
    if args.stage not in ("cut", "check"):
        print("preflight:", comfy.preflight(), flush=True)
    stages = STAGES if args.stage == "all" else (args.stage,)
    if args.stage == "all" and run.plan.get("clip_mode") == "ref2v":
        stages = tuple(s for s in stages if s != "keyframes")  # Ref2V renders straight from the sheets.
    for stage in stages:
        print(f"== {stage}", flush=True)
        getattr(run, stage)()
    return 0


if __name__ == "__main__":
    sys.exit(main())





