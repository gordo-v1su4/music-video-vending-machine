"""Anonymous Review, usable-range salvage and bounded repair over the production registry (V1S-230/231/232).

Layout under .runtime/gen/<plan>/production/:
  reviews/media/<blind>.mp4       metadata-stripped copies; the only media a reviewer receives
  reviews/<reviewer>/<blind>.json write-once reports (a reviewer cannot overwrite or read peers)
  reviews/findings.json           imported findings, mapped back to candidate labels by the orchestrator
  private/blind.json              blind id -> candidate label (never shown to reviewers)
  edit.json, edits/<id>.mp4       candidate Musical edits, joins, Keep/Reject, active cut and history
  repairs.json                    repair proposals bound to a finding, packet revision and allowance

Scores are individual ordinal judgments, never averaged into a leaderboard. A confirmed identity/Look gate
blocks Keep/export regardless of scores; reviewer allegations stay "alleged" until confirmed or cleared.
"""

import json
import os
import random
import re
import shutil
import subprocess
import time

from .production import Conflict, _lock, _read, _write, probe, sha256_file

SCOPES = ("shot", "clip", "sequence")
KINDS = ("technical", "brief", "artistic")
SEVERITIES = ("info", "minor", "major", "hard")
REPAIR_KINDS = ("trim", "reorder", "replace", "re-prompt", "rerender", "gap-fill")
GPU_KINDS = ("re-prompt", "rerender", "gap-fill")
MASTER = "D:/output/local/MVVM/song/master.mp3"


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%S")


class Review:
    def __init__(self, prod):
        self.prod = prod
        self.dir = os.path.join(prod.dir, "reviews")
        self.blind_path = os.path.join(prod.dir, "private", "blind.json")
        self.findings_path = os.path.join(self.dir, "findings.json")

    # ---- anonymous media ------------------------------------------------------------------------------
    def blind(self, labels, seed=None):
        """Give each candidate label a blind id and a metadata-stripped media copy (prompt text lives in
        Swarm's container comment, so the original file would leak the interpretation)."""
        reg = self.prod.registry()["clips"]
        by_label = {c["label"]: c for c in reg.values()}
        with _lock:
            blind = _read(self.blind_path, {})
            known = {v: k for k, v in blind.items()}
            rng = random.Random(seed)
            for label in labels:
                if label in known:
                    continue
                clip = by_label.get(label)
                if clip is None:
                    raise LookupError(f"unknown candidate {label}")
                bid = "K" + "".join(rng.choice("ABCDEFGHJKMNPQRSTUVWXYZ23456789") for _ in range(4))
                while bid in blind:
                    bid = "K" + "".join(rng.choice("ABCDEFGHJKMNPQRSTUVWXYZ23456789") for _ in range(4))
                dst = os.path.join(self.dir, "media", bid + ".mp4")
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", clip["path"], "-map", "0", "-map_metadata", "-1",
                                "-c", "copy", dst], check=True)
                blind[bid] = label
                known[label] = bid
            _write(self.blind_path, blind)
        return {known[label]: os.path.join(self.dir, "media", known[label] + ".mp4").replace("\\", "/") for label in labels}

    # ---- reports ----------------------------------------------------------------------------------------
    def save_report(self, reviewer, identity, blind_id, findings):
        """Write-once report from one reviewer for one blind candidate. identity: provider, model, access."""
        if not all(k in identity for k in ("provider", "model", "access")):
            raise Conflict("reviewer identity needs provider, model and access")
        blind = _read(self.blind_path, {})
        if blind_id not in blind:
            raise LookupError(f"unknown blind candidate {blind_id}")
        path = os.path.join(self.dir, reviewer, blind_id + ".json")
        if os.path.exists(path):
            raise Conflict(f"{reviewer} already saved a report for {blind_id}; reports are write-once")
        clean = []
        for i, f in enumerate(findings):
            if f.get("scope") not in SCOPES or f.get("kind") not in KINDS or f.get("severity") not in SEVERITIES:
                raise Conflict(f"finding {i + 1}: scope/kind/severity must be one of {SCOPES}/{KINDS}/{SEVERITIES}")
            scores = {k: v for k, v in (f.get("scores") or {}).items() if v is None or (isinstance(v, int) and 1 <= v <= 5)}
            clean.append({"scope": f["scope"], "kind": f["kind"], "severity": f["severity"], "text": str(f["text"])[:2000],
                          "range_s": f.get("range_s"), "gate": f.get("gate") if f.get("gate") in ("identity", "look") else None,
                          "uncertainty": str(f.get("uncertainty", ""))[:600], "evidence": f.get("evidence") or [],
                          "scores": scores, "action": str(f.get("action", ""))[:600]})
        _write(path, {"reviewer": reviewer, "identity": identity, "blind": blind_id, "saved_at": now(), "findings": clean})
        return path

    def import_reports(self):
        """Orchestrator step after every reviewer has saved: map blind ids back to labels."""
        blind = _read(self.blind_path, {})
        old = {f["id"]: f for f in _read(self.findings_path, [])}
        out = []
        for reviewer in sorted(os.listdir(self.dir)) if os.path.isdir(self.dir) else []:
            rdir = os.path.join(self.dir, reviewer)
            if reviewer == "media" or reviewer.startswith("packet") or not os.path.isdir(rdir):
                continue
            for name in sorted(os.listdir(rdir)):
                rep = _read(os.path.join(rdir, name), None) if name.endswith(".json") else None
                if not rep or "findings" not in rep:
                    continue
                for i, f in enumerate(rep["findings"]):
                    fid = f"{reviewer}/{rep['blind']}/{i + 1}"
                    entry = dict(f, id=fid, candidate=blind[rep["blind"]], blind=rep["blind"],
                                 reviewer={"id": reviewer, "model": f"{rep['identity']['provider']} {rep['identity']['model']}",
                                           "access": rep["identity"]["access"]})
                    if f.get("gate"):
                        entry["gate_status"] = old.get(fid, {}).get("gate_status", "alleged")
                    out.append(entry)
        _write(self.findings_path, out)
        return out

    def set_gate(self, finding_id, status, by, evidence=None):
        if status not in ("alleged", "confirmed", "cleared"):
            raise Conflict("gate status must be alleged, confirmed or cleared")
        with _lock:
            findings = _read(self.findings_path, [])
            f = next((f for f in findings if f["id"] == finding_id), None)
            if f is None or not f.get("gate"):
                raise LookupError(f"no gated finding {finding_id}")
            f["gate_status"], f["gate_by"], f["gate_at"] = status, by, now()
            if evidence:
                f["evidence"] = list(f.get("evidence") or []) + list(evidence)
            _write(self.findings_path, findings)
        return f

    def hard_blocked(self, label):
        return any(f["candidate"] == label and f.get("gate") and f.get("gate_status") == "confirmed"
                   for f in _read(self.findings_path, []))


class Edit:
    """Candidate Musical edits built only from registered immutable Clips. Never changes the active cut
    unless the user Keeps a candidate; Restore returns to the previous active cut."""

    def __init__(self, prod, master=MASTER):
        self.prod = prod
        self.master = master
        self.path = os.path.join(prod.dir, "edit.json")
        self.out_dir = os.path.join(prod.dir, "edits")
        self.review = Review(prod)

    def state(self):
        return _read(self.path, {"active": None, "history": [], "candidates": []})

    def build(self, cand_id, label, segments, joins, note="", repair_of=None, song_start=None):
        """segments: [{clip_id, in_s, out_s, song_s, label}] in edit order. Trims each source range, lays the
        song master under the whole cut from song_start, and checks the rendered length against the summed
        ranges to within one output frame."""
        reg = self.prod.registry()["clips"]
        packet = self.prod.packet()
        song_start = packet["sequence"]["song_start_s"] if song_start is None else song_start
        fps = 24.0
        parts, expected, cursor = [], 0.0, song_start
        for g in segments:
            clip = reg.get(g["clip_id"])
            if clip is None:
                raise LookupError(f"unknown clip {g['clip_id']}")
            if self.review.hard_blocked(clip["label"]):
                raise Conflict(f"{clip['label']} has a confirmed identity/Look block")
            a, b = float(g["in_s"]), float(g["out_s"])
            if not 0 <= a < b <= clip["media"]["duration_s"] + 1e-3:
                raise Conflict(f"{clip['label']} range {a}-{b} outside 0-{clip['media']['duration_s']}")
            if abs(g["song_s"] - cursor) > 1.0 / fps:
                raise Conflict(f"segment {clip['label']} starts at song {g['song_s']} but the cut is at {cursor:.3f}")
            # Frame-snap so trims and the expected length agree exactly.
            fa, fb = round(a * fps), round(b * fps)
            parts.append((clip, fa, fb, g))
            expected += (fb - fa) / fps
            cursor += (fb - fa) / fps
        if not os.path.isdir(self.out_dir):
            os.makedirs(self.out_dir)
        out = os.path.join(self.out_dir, f"{cand_id}.mp4")
        args, chains = ["ffmpeg", "-v", "error", "-y"], []
        for clip, fa, fb, _ in parts:
            args += ["-i", clip["path"]]
        args += ["-ss", f"{song_start:.3f}", "-t", f"{expected + 1:.4f}", "-i", self.master]
        for i, (clip, fa, fb, _) in enumerate(parts):
            chains.append(f"[{i}:v]trim=start_frame={fa}:end_frame={fb},setpts=PTS-STARTPTS,fps={fps:g},"
                          f"scale=1088:608:force_original_aspect_ratio=decrease,pad=1088:608:(ow-iw)/2:(oh-ih)/2,setsar=1[v{i}]")
        chains.append("".join(f"[v{i}]" for i in range(len(parts))) + f"concat=n={len(parts)}:v=1:a=0[v]")
        args += ["-filter_complex", ";".join(chains), "-map", "[v]", "-map", f"{len(parts)}:a", "-c:v", "libx264",
                 "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-t", f"{expected:.4f}", out]
        subprocess.run(args, check=True)
        media = probe(out)
        timing_ok = abs(media["frames"] / media["fps"] - expected) <= 1.0 / fps
        cand = {"id": cand_id, "label": label, "status": "candidate", "note": note, "repair_of": repair_of,
                "segments": [{"clip_id": c["id"], "label": g.get("label") or c["label"], "in_s": fa / fps, "out_s": fb / fps,
                              "song_s": round(g["song_s"], 3), "lineage": c["lineage"], "source_sha256": c["sha256"]}
                             for c, fa, fb, g in parts],
                "joins": joins, "url": f"/pilot-api/production/edit-media/{cand_id}.mp4",
                "built_at": now(), "sha256": sha256_file(out),
                "timing": {"expected_s": round(expected, 4), "actual_frames": media["frames"], "fps": media["fps"],
                           "within_one_frame": timing_ok}}
        if not timing_ok:
            raise Conflict(f"rendered {media['frames']} frames, expected {expected * fps:.0f}: timing off by more than a frame")
        with _lock:
            st = self.state()
            st["candidates"] = [c for c in st["candidates"] if c["id"] != cand_id] + [cand]
            _write(self.path, st)
        return cand

    def act(self, cand_id, action, by="director"):
        with _lock:
            st = self.state()
            cand = next((c for c in st["candidates"] if c["id"] == cand_id), None)
            if cand is None:
                raise LookupError(f"unknown candidate {cand_id}")
            if action == "keep":
                if cand["status"] == "rejected":
                    raise Conflict("a rejected candidate cannot be kept")
                if any(j["verdict"] == "unsafe" for j in cand["joins"]):
                    raise Conflict("an unsafe join blocks Keep")
                if any(self.review.hard_blocked(s["label"]) for s in cand["segments"]):
                    raise Conflict("a confirmed identity/Look block prevents Keep")
                st["history"].append({"active": st["active"], "replaced_by": cand_id, "by": by, "at": now()})
                st["active"], cand["status"] = cand_id, "kept"
            elif action == "reject":
                if cand_id == st["active"]:
                    raise Conflict("restore another cut before rejecting the active one")
                cand["status"] = "rejected"
            elif action == "restore":
                last = next((h for h in reversed(st["history"]) if h["replaced_by"] == st["active"]), None)
                if last is None:
                    raise Conflict("nothing to restore")
                st["history"].append({"active": st["active"], "replaced_by": last["active"], "by": by, "at": now(), "restore": True})
                st["active"] = last["active"]
            else:
                raise Conflict("action must be keep, reject or restore")
            _write(self.path, st)
        return st


class Repairs:
    """Repair proposals tied to one finding. Existing-media edits use no GPU attempts; render repairs draw on
    the packet's repair allowance, kept separate from the initial+replacement production cap."""

    def __init__(self, prod):
        self.prod = prod
        self.path = os.path.join(prod.dir, "repairs.json")

    def all(self):
        return _read(self.path, [])

    def allowance(self):
        cap = self.prod.packet()["allowance"].get("repair_renders", 0)
        used = sum(r.get("gpu_attempts_used", 0) for r in self.all())
        return {"repair_renders": cap, "used": used, "remaining": cap - used}

    def propose(self, finding_id, kind, scope, rationale, neighbors=None):
        if kind not in REPAIR_KINDS:
            raise Conflict(f"repair kind must be one of {REPAIR_KINDS}")
        findings = {f["id"]: f for f in _read(os.path.join(self.prod.dir, "reviews", "findings.json"), [])}
        if finding_id not in findings:
            raise LookupError(f"unknown finding {finding_id}")
        with _lock:
            reps = self.all()
            rep = {"id": f"R{len(reps) + 1}", "finding": finding_id, "candidate": findings[finding_id]["candidate"],
                   "kind": kind, "scope": scope, "neighbors": neighbors or [], "rationale": rationale[:2000],
                   "gpu_attempts": 1 if kind in GPU_KINDS else 0, "gpu_attempts_used": 0,
                   "packet_revision": self.prod.packet()["revision"], "status": "proposed", "proposed_at": now()}
            reps.append(rep)
            _write(self.path, reps)
        return rep

    def decide(self, rep_id, decision, by):
        if decision not in ("approved", "rejected"):
            raise Conflict("decision must be approved or rejected")
        with _lock:
            reps = self.all()
            rep = next((r for r in reps if r["id"] == rep_id), None)
            if rep is None:
                raise LookupError(f"unknown repair {rep_id}")
            if rep["packet_revision"] != self.prod.packet()["revision"]:
                raise Conflict("packet changed since this repair was proposed; propose it again")
            if decision == "approved" and rep["gpu_attempts"] and self.allowance()["remaining"] < rep["gpu_attempts"]:
                raise Conflict("repair render allowance exhausted")
            rep["status"], rep["decided_by"], rep["decided_at"] = decision, by, now()
            _write(self.path, reps)
        return rep

    def applied(self, rep_id, result, gpu_attempts_used=0):
        """Record the repair's output (an edit candidate id or a new clip label). Never changes the active cut."""
        with _lock:
            reps = self.all()
            rep = next((r for r in reps if r["id"] == rep_id), None)
            if rep is None or rep["status"] != "approved":
                raise Conflict(f"repair {rep_id} is not approved")
            rep.update(status="applied", result=result, gpu_attempts_used=gpu_attempts_used, applied_at=now())
            _write(self.path, reps)
        return rep


def join_evidence(prod, a, b, out_png, fps=24.0):
    """Outgoing frame of segment a beside the incoming frame of segment b, plus a luma/colour jump measure.
    a/b: {clip_id, in_s, out_s}. The numbers flag exposure/grade jumps only; action, screen direction,
    geography and rhythm across the join remain a reviewed judgment."""
    reg = prod.registry()["clips"]
    ca, cb = reg[a["clip_id"]], reg[b["clip_id"]]
    ta = max(0.0, round(a["out_s"] * fps - 1) / fps)
    tb = round(b["in_s"] * fps) / fps
    os.makedirs(os.path.dirname(out_png), exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{ta:.4f}", "-i", ca["path"], "-ss", f"{tb:.4f}", "-i", cb["path"],
                    "-filter_complex", "[0:v]scale=480:270:force_original_aspect_ratio=decrease,pad=480:270:(ow-iw)/2:(oh-ih)/2,trim=end_frame=1[a];[1:v]scale=480:270:force_original_aspect_ratio=decrease,pad=480:270:(ow-iw)/2:(oh-ih)/2,trim=end_frame=1[b];[a][b]hstack",
                    "-frames:v", "1", out_png], check=True)

    def stats(path, t):
        res = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.4f}", "-i", path, "-frames:v", "1", "-vf",
                              "scale=64:-2,signalstats,metadata=print:file=-", "-f", "null", "-"], capture_output=True, text=True)
        vals = dict(re.findall(r"lavfi\.signalstats\.(YAVG|UAVG|VAVG)=([0-9.]+)", res.stdout))
        return {k: float(v) for k, v in vals.items()}

    sa, sb = stats(ca["path"], ta), stats(cb["path"], tb)
    return {"image": out_png.replace("\\", "/"), "out_frame_s": ta, "in_frame_s": tb,
            "luma_jump": round(abs(sa.get("YAVG", 0) - sb.get("YAVG", 0)), 1),
            "chroma_jump": round(abs(sa.get("UAVG", 0) - sb.get("UAVG", 0)) + abs(sa.get("VAVG", 0) - sb.get("VAVG", 0)), 1)}


def copy_tree(src, dst):
    if os.path.isdir(src):
        shutil.copytree(src, dst, dirs_exist_ok=True)
    elif os.path.exists(src):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
