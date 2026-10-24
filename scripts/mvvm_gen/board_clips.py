"""Animate the finished storyboard panels: one song-conditioned MiniMax H3 clip per panel (PlagueKind V11 fl2v_refs).

The panel is the first frame. The named masters (sheets/<cid>/closeup-named.png) are the identity references and
the only place a character's name is used. The song slice at the clip's spot is both the locked output audio and
<Audio 1>. Every impact marker from the studio's edit plan that falls inside the clip is written into the prompt as
a timestamped beat-snap. Clips are filler for song spans the pilot cut does not cover yet; they are placed with
Run.fill.

  python -m scripts.mvvm_gen.board_clips scripts/mvvm_gen/plans/i-ran-pilot.json [--only board2/p31 ...]
"""

import argparse
import json
import os
import sys

from . import comfy, graphs, pk_v11, qwen_edit
from .identity_audio_test import face_score  # runs face_check.py in ComfyUI's venv (OpenCV)
from .identity_audio_test import SLA
from .run import Run, seed_for

# (first-frame panel, edit-plan chunk, cast, one line per cut slot in that chunk). The clip opens on the panel and
# hard-cuts on the chunk's own slot times ("cut to this, cut to that"), so every piece lands on the song's cut map.
# Story order, all outside the 3:32-4:37 pilot cut. The bridge-fall sequence (board2b) is parked (user, 2026-09-29).
CLIPS = [
    ("board9/p11", 1, ["lune"], ["Extreme close-up of her eye, the torchlit crowd dancing in its reflection; slow push in.",
                                 "She dances with her arm raised, head back, laughing, hair whipping.",
                                 "The crowd dances in the haze, green lasers slicing through the smoke."]),
    ("board9/p12", 2, ["lune"], ["She dances, arm raised, laughing, lyrical and free.",
                                 "Close on her spinning, hair flying across her face in slow motion.",
                                 "Torches and dancing silhouettes, the camera whips past them."]),
    ("board9/p13", 3, ["lune", "rafa"], ["She looks around the crowd, lost and searching.",
                                         "Across the crowd Rafa turns and almost sees her.",
                                         "He looks straight through her and is pulled away by someone else."]),
    ("board9/p21", 4, ["lune"], ["She runs away from the camera into the torchlit crowd.", "Green lasers flicker through the haze.",
                                 "Her face, breathing hard, torchlight flashing.", "Her feet pounding the wet ground.",
                                 "The crowd parts and closes behind her.", "She looks back over her shoulder."]),
    ("board9/p22", 5, ["lune"], ["She reaches toward the lens through the crowd, pleading.",
                                 "Hands grab her arms and pull her back.", "The crowd closes over her."]),
    ("board9/p23", 6, ["lune"], ["She is swallowed by the crowd, bodies closing around her.",
                                 "Dolly zoom on her face: the background stretches away while she stays the same size.",
                                 "Overhead: she spins alone in the middle of the dancers.", "Her hand reaching up out of the crowd.",
                                 "Close on her eyes closing."]),
    ("board9/p31", 7, ["lune"], ["Dreamy close-up of her face through glittering bokeh, eyes closed, swaying.",
                                 "Torches blur into streaks as she turns.", "She dances slowly, lyrical, arms drifting.",
                                 "Bokeh lights pulse to the beat.", "Her face tilts up, lit gold."]),
    ("board9/p32", 8, ["lune", "rafa"], ["They lean forehead to forehead in the torchlight, almost kissing.",
                                         "Close on their hands finding each other.", "They sway together, eyes closed."]),
    ("board9/p33", 9, ["lune"], ["She stands waist-deep in the moonlit lagoon, face turned up to the moon.",
                                 "The torches on the shore reflect in the rippling water.", "Close on her wet face, eyes open to the sky.",
                                 "Wide: she is alone in the lagoon under the huge moon."]),
    ("board2/p11", 10, ["lune", "rafa"], ["She runs toward him across the rope bridge, reaching out, the moon behind her.",
                                          "Close on his face as she comes toward him.", "The ropes creak and sway over the gorge."]),
    ("board2/p13", 13, ["rafa"], ["He lunges toward the lens reaching for her.", "A rope snaps behind him.",
                                  "His hand stretching toward the lens.", "The planks splinter under him.", "His face, screaming her name."]),
    ("board2/p21", 14, [], ["Two hands reach toward each other, fingertips almost touching, trembling.",
                            "Close on the tiny gap between the fingertips.", "The fingers slip apart.", "An empty hand in the rain."]),
    ("board2/p22", 15, ["lune", "rafa"], ["The rope bridge explodes apart; she reaches up, he reaches down.",
                                          "Debris flies past the lens in slow motion.", "Her hand reaching up.", "His hand reaching down.",
                                          "Planks tumble into the gorge.", "The moon through the flying debris."]),
    ("board2/p23", 16, ["lune"], ["Seen from above, she falls backward through the mist, arms spread, face up, strong motion blur.",
                                  "The mist swallows her."]),
    ("board2/p31", 17, ["lune"], ["Underwater, eyes closed, she sinks slowly, bubbles streaming up past her face.",
                                  "Her hair floating around her headwrap.", "Light rays from the surface far above."]),
    ("board2/p32", 18, ["lune"], ["Her silhouette sinks through the dark water toward the light above, arms raised.",
                                  "Bubbles rising from her lips.", "The surface glowing far above."]),
    ("board2/p33", 19, ["lune", "rafa"], ["Waist-deep in the moonlit lagoon they almost kiss; he is serious.",
                                          "Close on their lips almost touching.", "Wide: the two of them under the moon."]),
]

# Reference sequences (pk_v11_ref2v): the user's panels are BLOCKING references only ("put Rafa where this man is,
# Lune where she is"), never first frames; identity comes from the named masters. (name, chunk, cast, blocking panel
# keys, one line per cut slot.)
REF_SEQUENCES = [
    ("dream-bridge-fall", 21, ["lune", "rafa"], ["board2b/a11", "board2b/a21", "board2b/a22"],
     ["Staged like the first blocking reference: she falls backward off the breaking rope bridge, reaching up, terrified.",
      "Staged like the second blocking reference: he lunges down from the bridge, reaching for her, screaming.",
      "Staged like the third blocking reference: wide, he clings to the broken bridge as she falls away into the gorge under the moon.",
      "She tumbles through the mist in slow motion, reaching up.",
      "She wakes with a gasp, lying on the jungle floor at night, torches glowing in the distance: it was a dream."]),
]

# LoRA A/B variants (first LoRA tests): the same clip rendered again with the LoRA, saved with a suffix.
VARIANTS = {
    "board9/p12": [("bhm", [(r"h3etter_motion_h3_lora_v1_500.safetensors", 0.6)], "")],
    "board9/p21": [("bhm", [(r"h3etter_motion_h3_lora_v1_500.safetensors", 0.6)], "")],
    "board2/p22": [("bt", [(r"h3\BulletTime-MMH3.safetensors", 1.0)], "bullet-time. ")],
}


def impacts_in(plan, start, seconds):
    out = []
    for chunk in plan["chunks"]:
        for hit in chunk.get("impacts", []):
            t = hit["ms"] / 1000 - start
            if 0.2 < t < seconds - 0.2:
                out.append(t)
    return sorted(set(round(t, 3) for t in out))


def stamp(t):
    return f"00:{int(t):02d}.{int(round((t % 1) * 1000)):03d}"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("--only", nargs="*", default=None)
    args = ap.parse_args(argv)
    run = Run(args.plan)
    with open(run.path("edit-plan.json"), encoding="utf-8") as fh:
        edit = json.load(fh)
    with open(run.path("boards", "fixed", "finals.json"), encoding="utf-8") as fh:
        finals = json.load(fh)
    print("preflight:", comfy.preflight(), flush=True)
    song_file = run.plan["song"]["audio"]
    song = comfy.upload_image(song_file)
    chars = run.plan["characters"]
    masters = {cid: run.upload(chars[cid]["master_ref"]) for cid in ("lune", "rafa")}
    w, h = run.plan["frame_size"]
    sla = {**run.plan.get("clip_overrides", {}).get(SLA, {}), "reference_protection": "Heavy Enforcement",
           "protect_audio": True, "dense_last_steps": 1, "dense_steps": "0-2"}
    out_dir = run.path("clips", "boards")
    os.makedirs(out_dir, exist_ok=True)
    chunks = {c["index"]: c for c in edit["chunks"]}
    jobs = []
    for key, ci, cast, shots in CLIPS:
        if args.only and key not in args.only:
            continue
        chunk = chunks[ci]
        if len(shots) != len(chunk["shots"]):
            raise SystemExit(f"{key}: {len(shots)} shot lines for {len(chunk['shots'])} slots in chunk {ci}")
        start, seconds = chunk["startMs"] / 1000, (chunk["endMs"] - chunk["startMs"]) / 1000
        cuts = [(x["startMs"] - chunk["startMs"]) / 1000 for x in chunk["shots"][1:]]
        # The approved, grade-unified still (boards/unified, see grade_match.py unify) is the first frame.
        first = qwen_edit.conform(run.path("boards", "unified", key.replace("/", "-") + ".png"),
                                  os.path.join(out_dir, key.replace("/", "-") + "-first.png"), (w, h))
        refs = [run.upload(first), None]
        subjects = []
        for cid in cast:
            refs.append(masters[cid])
            subjects.append((f"{chars[cid]['identity']} Outfit: {chars[cid]['look']}", [len(refs) - 1],
                             run.full_name(cid), list(range(1, len(shots) + 1))))
        lines = [f"[Shot 1] The video opens exactly on the first frame. {shots[0]}"]
        lines += [f"[Shot {i + 2}] At {stamp(t)}, the camera cuts to: {text}" for i, (t, text) in enumerate(zip(cuts, shots[1:]))]
        accents = [t for t in impacts_in(edit, start, seconds) if all(abs(t - c) > 0.25 for c in cuts)]
        lines += [f"At {stamp(t)}, on the accent in <Audio 1>, a sharp snap of movement." for t in accents]
        lines.append("Hard cuts only, exactly at those times; no cuts or camera shake on minor beats. Cinematic, photoreal, "
                     "the same colour grade as the first frame.")
        for suffix, loras, trigger in [("", (), "")] + VARIANTS.get(key, []):
            dest = os.path.join(out_dir, key.replace("/", "-") + (f"-{suffix}" if suffix else "") + ".mp4")
            if os.path.exists(dest):
                continue
            prompt = graphs.h3_music_prompt(subjects, f"{trigger}Board sequence {key} (chunk {ci}).", run.plan["style"],
                                            "\n\n".join(lines))
            seed = seed_for(run.name, "boardclip", key)
            graph = pk_v11.build("pk_v11_fl2v_refs", prompt, seed, f"mvvm/{run.name}/boardclip-{os.path.basename(dest)[:-4]}",
                                 w, h, seconds, images=refs, unet=run.plan.get("clip_unet"), overrides={SLA: sla},
                                 song_audio=(song, start), reference_audio=(song_file, start, seconds), loras=loras)
            with open(dest.replace(".mp4", ".prompt.txt"), "w", encoding="utf-8") as fh:
                fh.write(prompt)
            pid = comfy.submit(graph)
            print(f"[{key}{'-' + suffix if suffix else ''}] queued {pid}: chunk {ci} at {start:.1f}s, {seconds:.1f}s, "
                  f"{len(cuts)} cuts, {len(accents)} accents", flush=True)
            jobs.append((key + (f"-{suffix}" if suffix else ""), cast, pid, dest, start, ci, cuts))
    for name, ci, cast, blocking, shots in REF_SEQUENCES:
        if args.only and name not in args.only:
            continue
        dest = os.path.join(out_dir, name + ".mp4")
        if os.path.exists(dest):
            continue
        chunk = chunks[ci]
        if len(shots) != len(chunk["shots"]):
            raise SystemExit(f"{name}: {len(shots)} shot lines for {len(chunk['shots'])} slots in chunk {ci}")
        start, seconds = chunk["startMs"] / 1000, (chunk["endMs"] - chunk["startMs"]) / 1000
        cuts = [(x["startMs"] - chunk["startMs"]) / 1000 for x in chunk["shots"][1:]]
        refs, subjects = [], []
        for cid in cast:
            refs.append(masters[cid])
            subjects.append((f"{chars[cid]['identity']} Outfit: {chars[cid]['look']}", [len(refs)],
                             run.full_name(cid), list(range(1, len(shots) + 1))))
        first_block = len(refs) + 1
        refs += [run.upload(finals[k]["final"]) for k in blocking]
        pics = ", ".join(f"<Picture {first_block + i}>" for i in range(len(blocking)))
        lines = [f"{pics} are blocking references only: take from them where each person stands, their poses and the "
                 f"camera angle, never their faces, hair or bodies. The people are always the named characters above.",
                 f"[Shot 1] {shots[0]}"]
        lines += [f"[Shot {i + 2}] At {stamp(t)}, the camera cuts to: {text}" for i, (t, text) in enumerate(zip(cuts, shots[1:]))]
        lines.append("Hard cuts only, exactly at those times. Cinematic, photoreal, moonlit teal-green night grade.")
        prompt = graphs.h3_music_prompt(subjects, f"Flashback dream sequence {name} (chunk {ci}).", run.plan["style"],
                                        "\n\n".join(lines))
        graph = pk_v11.build("pk_v11_ref2v", prompt, seed_for(run.name, "refseq", name), f"mvvm/{run.name}/refseq-{name}",
                             w, h, seconds, images=refs, unet=run.plan.get("clip_unet"), overrides={SLA: sla},
                             song_audio=(song, start), reference_audio=(song_file, start, seconds))
        with open(dest.replace(".mp4", ".prompt.txt"), "w", encoding="utf-8") as fh:
            fh.write(prompt)
        pid = comfy.submit(graph)
        print(f"[{name}] queued {pid}: chunk {ci} at {start:.1f}s, {seconds:.1f}s, {len(cuts)} cuts", flush=True)
        jobs.append((name, cast, pid, dest, start, ci, cuts))
    report_path = os.path.join(out_dir, "report.json")
    report = json.load(open(report_path, encoding="utf-8")) if os.path.exists(report_path) else {}
    for key, cast, pid, dest, start, ci, cuts in jobs:
        record = comfy.wait(pid, timeout=run.plan.get("job_timeout_s", 1800))
        comfy.download(comfy.output_files(record)[0], dest)
        faces = {cid: face_score(chars[cid]["master_ref"], dest).get("median") for cid in cast}
        report[key] = {"clip": dest, "chunk": ci, "song_s": start, "planned_cuts": cuts, "faces": faces}
        json.dump(report, open(report_path, "w", encoding="utf-8"), indent=1)
        print(f"[{key}] done -> {dest} | faces {faces}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
