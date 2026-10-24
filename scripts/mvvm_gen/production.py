"""Revision-bound production packet and Sequence -> Clip -> Generated-shot candidate registry (V1S-224/225).

Everything lives under .runtime/gen/<plan>/production/ next to the pilot's manifest and review store:
  packet.json    brief, master, Characters/Looks, references (role/provenance/hash/decision), Sequence plan,
                 workflow identity, render allowance, and the approval fingerprint
  registry.json  immutable Clips (generated or supplied) keyed by content hash, their reviewed
                 Generated-shot ranges, and run lineage

Approval binds a fingerprint of every approval-relevant field. Any change to references, bindings, the
plan, workflow or allowance changes the fingerprint, so the stored approval no longer matches and the
packet reads as unapproved until approved again. Writes use optimistic revisions and atomic replace.
"""

import hashlib
import json
import os
import re
import subprocess
import threading
import time

ROLES = ("identity", "look", "inspiration", "scene", "first_frame", "last_frame", "timed_guide", "motion")
DECISIONS = ("pending", "approved", "rejected")
APPROVAL_KEYS = ("brief", "master", "characters", "references", "sequence", "workflow", "allowance")
_lock = threading.Lock()


class Conflict(ValueError):
    """Raised when a write targets a stale revision or breaks an invariant."""


def sha256_file(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def fingerprint(packet):
    return hashlib.sha256(canonical({k: packet.get(k) for k in APPROVAL_KEYS}).encode()).hexdigest()[:16]


def _read(path, default):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".part"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=1, ensure_ascii=False)
    os.replace(tmp, path)


def probe(path):
    """Decode facts for a media file: frames, fps, size, duration, audio presence (ffprobe)."""
    out = subprocess.run(["ffprobe", "-v", "error", "-count_packets", "-show_entries",
                          "stream=codec_type,width,height,r_frame_rate,nb_read_packets:format=duration",
                          "-of", "json", path], capture_output=True, text=True, check=True).stdout
    info = json.loads(out)
    video = next(s for s in info["streams"] if s["codec_type"] == "video")
    num, den = (int(x) for x in video["r_frame_rate"].split("/"))
    return {"frames": int(video["nb_read_packets"]), "fps": num / den, "width": video["width"],
            "height": video["height"], "duration_s": round(float(info["format"]["duration"]), 3),
            "audio": any(s["codec_type"] == "audio" for s in info["streams"])}


class Production:
    def __init__(self, root):
        self.dir = os.path.join(root, "production")
        self.packet_path = os.path.join(self.dir, "packet.json")
        self.registry_path = os.path.join(self.dir, "registry.json")

    # ---- packet -------------------------------------------------------------------------------------
    def packet(self):
        p = _read(self.packet_path, None)
        if p is None:
            raise LookupError("no production packet yet")
        p["fingerprint"] = fingerprint(p)
        p["approved"] = p.get("approval", {}).get("fingerprint") == p["fingerprint"]
        p["blocking"] = self.blocking(p)
        return p

    def blocking(self, p):
        """Reasons production cannot start: unapproved/contradictory references, missing conditioning."""
        reasons = []
        for r in p.get("references", []):
            if r["role"] in ("identity", "look") and r["decision"] != "approved":
                reasons.append(f"{r['id']}: {r['role']} reference is {r['decision']}")
        for c in p.get("characters", []):
            if not c.get("refmod") and not any(r["role"] == "identity" and r.get("character") == c["id"]
                                               and r["decision"] == "approved" for r in p["references"]):
                reasons.append(f"{c['id']}: no approved identity conditioning")
        if p.get("approval", {}).get("fingerprint") not in (None, fingerprint(p)):
            reasons.append("packet changed since approval; re-approve")
        return reasons

    def save_packet(self, packet, expected_revision):
        with _lock:
            current = _read(self.packet_path, None)
            if current is not None and current["revision"] != expected_revision:
                raise Conflict(f"packet is at revision {current['revision']}, not {expected_revision}")
            body = {k: v for k, v in packet.items() if k not in ("fingerprint", "approved", "blocking")}
            body["revision"] = (current or {"revision": 0})["revision"] + 1
            body["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
            _write(self.packet_path, body)
        return self.packet()

    def decide_reference(self, ref_id, decision, note, expected_revision):
        if decision not in DECISIONS:
            raise Conflict(f"decision must be one of {DECISIONS}")
        p = self.packet()
        ref = next((r for r in p["references"] if r["id"] == ref_id), None)
        if ref is None:
            raise LookupError(f"unknown reference {ref_id}")
        ref["decision"], ref["note"] = decision, note[:2000]
        return self.save_packet(p, expected_revision)

    SLOT_FIELDS = ("title", "entry", "exit", "camera", "action", "location", "cuts", "characters")

    def edit_plan(self, slot_id, fields, brief, expected_revision):
        """Edit one Sequence slot (and optionally the brief). Changes the fingerprint, so approval lapses."""
        p = self.packet()
        if brief is not None:
            p["brief"] = str(brief)[:4000]
        if slot_id:
            slot = next((c for c in p["sequence"]["clips"] if c["slot"] == slot_id), None)
            if slot is None:
                raise LookupError(f"unknown slot {slot_id}")
            for key, value in (fields or {}).items():
                if key not in self.SLOT_FIELDS:
                    raise Conflict(f"slot field {key} is not editable")
                if key == "cuts":
                    value = int(value)
                    if not 0 <= value <= 4:
                        raise Conflict("cuts must be 0-4")
                elif key == "characters":
                    known = {c["id"] for c in p["characters"]}
                    if not value or not set(value) <= known:
                        raise Conflict(f"characters must be a non-empty subset of {sorted(known)}")
                else:
                    value = str(value)[:1200]
                slot[key] = value
        return self.save_packet(p, expected_revision)

    def approve(self, by, expected_revision):
        p = self.packet()
        blockers = [b for b in p["blocking"] if not b.startswith("packet changed")]
        if blockers:
            raise Conflict("cannot approve: " + "; ".join(blockers))
        p["approval"] = {"fingerprint": p["fingerprint"], "by": by, "at": time.strftime("%Y-%m-%dT%H:%M:%S")}
        return self.save_packet(p, expected_revision)

    # ---- registry -----------------------------------------------------------------------------------
    def registry(self):
        return _read(self.registry_path, {"clips": {}})

    def add_clip(self, path, source, lineage=None, label=None):
        """Register an immutable Clip. Identity is the content hash; re-adding the same bytes is a no-op."""
        if source not in ("generated", "supplied"):
            raise Conflict("source must be generated or supplied")
        clip_id = "clip-" + sha256_file(path)[:12]
        with _lock:
            reg = self.registry()
            if clip_id not in reg["clips"]:
                reg["clips"][clip_id] = {"id": clip_id, "path": os.path.abspath(path).replace("\\", "/"),
                                         "sha256": sha256_file(path), "source": source, "label": label or clip_id,
                                         "media": probe(path), "lineage": lineage or {}, "shots": [],
                                         "added_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
                _write(self.registry_path, reg)
        return reg["clips"][clip_id]

    def set_shots(self, clip_id, shots, reviewed_by):
        """Replace a Clip's Generated-shot ranges. Each shot: {in, out, status: proposed|reviewed, note}."""
        with _lock:
            reg = self.registry()
            clip = reg["clips"].get(clip_id)
            if clip is None:
                raise LookupError(f"unknown clip {clip_id}")
            if sha256_file(clip["path"]) != clip["sha256"]:
                raise Conflict(f"{clip_id} media changed on disk; clips are immutable")
            frames, last, out = clip["media"]["frames"], -1, []
            for i, s in enumerate(sorted(shots, key=lambda s: s["in"])):
                a, b = int(s["in"]), int(s["out"])
                if not (0 <= a < b <= frames) or a < last:
                    raise Conflict(f"shot {i + 1} range {a}..{b} invalid for {frames} frames or overlapping")
                status = s.get("status", "proposed")
                if status not in ("proposed", "reviewed"):
                    raise Conflict("shot status must be proposed or reviewed")
                out.append({"id": f"{clip_id}/s{i + 1}", "in": a, "out": b, "status": status,
                            "note": str(s.get("note", ""))[:2000], "by": reviewed_by if status == "reviewed" else None})
                last = b
            clip["shots"] = out
            _write(self.registry_path, reg)
        return clip

    def propose_cuts(self, clip_id, threshold=0.12):
        """Detector suggestions only: scene-cut frames as proposed (unreviewed) shot boundaries."""
        clip = self.registry()["clips"][clip_id]
        res = subprocess.run(["ffmpeg", "-hide_banner", "-i", clip["path"], "-vf",
                              f"select='gt(scene,{threshold})',showinfo", "-an", "-f", "null", "-"],
                             capture_output=True, text=True).stderr
        fps = clip["media"]["fps"]
        cuts = [round(float(t) * fps) for t in re.findall(r"pts_time:([0-9.]+)", res)]
        bounds = [0] + [c for c in cuts if 0 < c < clip["media"]["frames"]] + [clip["media"]["frames"]]
        return [{"in": a, "out": b, "status": "proposed"} for a, b in zip(bounds, bounds[1:]) if b > a]

    # ---- independent prompt teams (V1S-227) -----------------------------------------------------------
    def team_dir(self, team):
        if not re.fullmatch(r"[a-z0-9-]{1,32}", team):
            raise Conflict("team ids are lowercase letters, digits and dashes")
        return os.path.join(self.dir, "teams", team)

    def export_packet(self):
        """Immutable writer packet for the current revision: brief, slots, references; no teams or outputs."""
        p = self.packet()
        shared = os.path.join(self.dir, "teams", "shared", f"packet-r{p['revision']}.json")
        if not os.path.exists(shared):
            body = {k: p[k] for k in ("id", "brief", "characters", "sequence", "workflow")}
            body["revision"], body["fingerprint"] = p["revision"], p["fingerprint"]
            body["references"] = [{k: r.get(k) for k in ("id", "role", "character", "decision", "frame")}
                                  for r in p["references"] if r["decision"] != "rejected"]
            _write(shared, body)
        return shared.replace("\\", "/")

    def register_team(self, team, identity):
        """identity: provider, model, host, transport (manual|adapter), media_access."""
        os.makedirs(self.team_dir(team), exist_ok=True)
        path = os.path.join(self.dir, "private", "teams.json")
        teams = _read(path, {})
        teams[team] = dict(identity, registered_at=time.strftime("%Y-%m-%dT%H:%M:%S"))
        _write(path, teams)
        return teams[team]

    def team_read(self, team, path):
        """A writer may read only its own directory and the shared packet export; anything else is denied."""
        real = os.path.realpath(path)
        allowed = (os.path.realpath(self.team_dir(team)), os.path.realpath(os.path.join(self.dir, "teams", "shared")))
        if not any(real == a or real.startswith(a + os.sep) for a in allowed):
            self._audit({"event": "denied-read", "team": team, "path": path.replace("\\", "/")})
            raise PermissionError(f"team {team} may not read {path}")
        with open(real, encoding="utf-8") as fh:
            return fh.read()

    def import_interpretation(self, team, slot, filename, input_map, duration_s, cuts=None):
        """Orchestrator import of one writer prompt from that team's own directory, linted on import."""
        from . import h3lint
        p = self.packet()
        text = self.team_read(team, os.path.join(self.team_dir(team), filename))
        lint = h3lint.lint(text, input_map, duration_s, packet_revision=p["revision"],
                           expected_revision=p["revision"], cuts=cuts)
        entry = {"team": team, "slot": slot, "file": filename, "sha256": hashlib.sha256(text.encode()).hexdigest(),
                 "packet_revision": p["revision"], "lint": lint, "imported_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
        with _lock:
            path = os.path.join(self.dir, "private", "interpretations.json")
            entries = _read(path, [])
            entries.append(entry)
            _write(path, entries)
        self._audit({"event": "import", "team": team, "slot": slot, "ok": lint["ok"]})
        return entry

    def critique_for(self, team):
        """A writer's view of Review: findings on its own candidates only (attribution stays private)."""
        attribution = _read(os.path.join(self.dir, "private", "attribution.json"), {})
        mine = {label for label, a in attribution.items() if a.get("team") == team}
        return [f for f in _read(os.path.join(self.dir, "reviews", "findings.json"), []) if f.get("candidate") in mine]

    def _audit(self, event):
        os.makedirs(os.path.join(self.dir, "private"), exist_ok=True)
        with open(os.path.join(self.dir, "private", "audit.jsonl"), "a", encoding="utf-8") as fh:
            fh.write(json.dumps(dict(event, at=time.strftime("%Y-%m-%dT%H:%M:%S"))) + "\n")
