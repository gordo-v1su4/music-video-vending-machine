"""Compile and lint MiniMax H3 Ref2VA prompts against a production packet's actual input map (V1S-226).

The linter is structural. It checks what can be checked mechanically: the six Ref2VA sections, label
existence and stable meaning, input roles, the H3 frame grid, cut/guide timing bounds, stale packet
revisions and negated action lists in generation text. Creative fidelity, physics and continuity stay
review tasks; a clean lint is not a semantic guarantee.

Input map (from the packet + workflow, never guessed):
  {"subjects": {"1": "Rafa"}, "pictures": {"1": "gorge scene"}, "audios": {"1": "song"}, "videos": {},
   "refmods": ["Rafa_identity_full"], "guides": [{"name": "B", "frame": 120}]}
RefMods enter through native Apply as DiT conditioning: they carry no <Picture N> token, so subjects
bound only to a RefMod are described in words. Native guide images likewise get no Picture label.
"""

import json
import re

SECTIONS = ("subject_definitions", "summary", "retention_analysis", "detailed_description",
            "overall_soundscape", "non_diegetic_music")
FPS = 24
LABEL = re.compile(r"<(Subject|Picture|Audio|Video) (\d+)>")
SHOT = re.compile(r"\[Shot (\d+)\](?:\s*At\s+(\d+):(\d+)\.(\d{3}))?")
# Negated unwanted-action lists belong in review criteria, not generation text.
NEGATION = re.compile(r"\b(no|not|never|without|don't|doesn't|does not|do not|avoid|instead of)\b[^.]{0,80}"
                      r"\b(stop|stops|stopping|sit|sits|sitting|crouch|crouches|reset|resets|pause|pauses|"
                      r"freeze|freezes|cut|cuts|land|lands|stand|stands|morph|twist|twists|reverse)\b", re.I)
ONE_SHOT = re.compile(r"\b(one continuous shot|single continuous shot|no cuts?|without cuts?|one-take)\b", re.I)


def h3_frames(seconds):
    """Frames H3 actually generates for a requested duration: 5 + 17n at 24 fps (matches workflow node 19)."""
    n = max(5, round(seconds * FPS))
    return n + (5 - n % 17) % 17


def parse(text):
    """Split a Ref2VA prompt into its sections. Unknown leading text is kept under ''."""
    out, key, buf = {}, "", []
    pattern = re.compile(r"^\s*(" + "|".join(SECTIONS) + r")\s*:\s*(.*)$")
    for line in text.replace("\r\n", "\n").split("\n"):
        m = pattern.match(line)
        if m:
            out[key] = "\n".join(buf).strip()
            key, buf = m.group(1), [m.group(2)]
        else:
            buf.append(line)
    out[key] = "\n".join(buf).strip()
    if not out.get(""):
        out.pop("", None)
    return out


def compile_prompt(fields):
    """Join the six fields in the grammar's order (missing ones are left out and reported by lint)."""
    return "\n\n".join(f"{k}: {fields[k].strip()}" for k in SECTIONS if fields.get(k, "").strip())


def finding(code, severity, message, where=None):
    return {"code": code, "severity": severity, "message": message, **({"where": where} if where else {})}


def lint(text, input_map, duration_s, packet_revision=None, expected_revision=None, cuts=None):
    """Return {ok, frames, duration_actual_s, findings[]}. `cuts` = intended cut count (None = unchecked)."""
    findings = []
    sections = parse(text)
    for name in SECTIONS:
        if not sections.get(name):
            findings.append(finding("missing-section", "error", f"Missing or empty '{name}:' section."))
    if expected_revision is not None and packet_revision != expected_revision:
        findings.append(finding("stale-packet", "error",
                                f"Prompt was written for packet revision {packet_revision}; current is {expected_revision}."))

    available = {"Subject": set(input_map.get("subjects", {})), "Picture": set(input_map.get("pictures", {})),
                 "Audio": set(input_map.get("audios", {})), "Video": set(input_map.get("videos", {}))}
    used = {(k, n) for k, n in LABEL.findall(text)}
    defs = sections.get("subject_definitions", "")
    for kind, n in sorted(used):
        if n not in available[kind]:
            hint = " Native guide images and RefMods have no Picture token." if kind == "Picture" else ""
            findings.append(finding("unknown-label", "error", f"<{kind} {n}> has no matching input.{hint}"))
        elif kind != "Subject" and f"<{kind} {n}>" not in defs:
            findings.append(finding("undefined-label", "warning", f"<{kind} {n}> is used but not defined in subject_definitions."))
    for n, name in input_map.get("subjects", {}).items():
        if f"<Subject {n}>" not in defs:
            findings.append(finding("subject-undefined", "error", f"<Subject {n}> ({name}) is not defined in subject_definitions."))
        elif name.lower() not in defs.lower():
            findings.append(finding("subject-name", "warning", f"<Subject {n}> should be introduced by name ('{name}')."))
    for kind, key in (("Picture", "pictures"), ("Audio", "audios")):
        for n in input_map.get(key, {}):
            if (kind, n) not in used:
                findings.append(finding("unused-input", "warning", f"<{kind} {n}> is connected but never referenced."))

    frames = h3_frames(duration_s)
    actual = frames / FPS
    if abs(actual - duration_s) > 0.75 / FPS * 17:
        findings.append(finding("frame-grid", "info", f"Requested {duration_s:.3f}s renders {frames} frames ({actual:.3f}s)."))
    for g in input_map.get("guides", []):
        f = g["frame"] if g["frame"] >= 0 else frames + g["frame"]
        if not 0 <= f < frames:
            findings.append(finding("guide-range", "error", f"Guide {g['name']} frame {g['frame']} is outside 0..{frames - 1}."))

    times, last = [], -1.0
    for idx, mm, ss, ms in SHOT.findall(text):
        if mm:
            t = int(mm) * 60 + int(ss) + int(ms) / 1000
            if t >= actual:
                findings.append(finding("cut-range", "error", f"[Shot {idx}] at {t:.3f}s is past the clip end ({actual:.3f}s)."))
            if t <= last:
                findings.append(finding("cut-order", "error", f"[Shot {idx}] at {t:.3f}s is not after the previous cut."))
            last = t
            times.append(t)
    detailed = sections.get("detailed_description", "") + " " + sections.get("summary", "")
    if ONE_SHOT.search(detailed) and times:
        findings.append(finding("cut-contradiction", "error", "Text promises one continuous shot but contains timed [Shot N] cuts."))
    if cuts is not None and len(times) != cuts:
        findings.append(finding("cut-count", "warning", f"Packet intends {cuts} cut(s); prompt has {len(times)} timed shot marker(s)."))

    gen = " ".join(sections.get(k, "") for k in ("summary", "detailed_description"))
    for m in NEGATION.finditer(gen):
        findings.append(finding("negated-action", "warning",
                                "Negated action list in generation text; describe the intended visible motion instead "
                                "and keep failure lists in the review rubric.", m.group(0)))
    return {"ok": not any(f["severity"] == "error" for f in findings), "frames": frames,
            "duration_actual_s": round(actual, 3), "findings": findings}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("prompt_file")
    ap.add_argument("input_map_json")
    ap.add_argument("--duration", type=float, required=True)
    a = ap.parse_args()
    with open(a.prompt_file, encoding="utf-8") as fh, open(a.input_map_json, encoding="utf-8") as mh:
        print(json.dumps(lint(fh.read(), json.load(mh), a.duration), indent=1))
