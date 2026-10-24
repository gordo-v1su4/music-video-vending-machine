"""Lint the user's H3 timestamped-cut profile; report findings without modifying prompts.

Standard library only. Exit 1 for errors (or warnings with --strict), 2 for invalid CLI/files.
This is a writing-profile checker, not a proof of semantic continuity or model behavior.
"""

import argparse
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import json
from pathlib import Path
import re

INTERVAL = re.compile(r"^\[(\d+):([0-5]\d(?:\.\d+)?)\s*[-–]\s*(\d+):([0-5]\d(?:\.\d+)?)\]\s*(.+)$")
WORD = re.compile(r"\b[\w’'-]+\b")
TYPO = {"collapes": "collapses", "clifff": "cliff", "promtp": "prompt",
        "realiable": "reliable", "continous": "continuous", "simultanously": "simultaneously"}
NEGATIVE = re.compile(r"\b(?:without|no|not|never|stops|avoid|don't|doesn't|do not|empty of)\b", re.I)
CARRYOVER = re.compile(r"\b(?:continuing from before|as before|just (?:picked|opened|raised|sat)|after \w+ing)\b", re.I)
APPEARANCE = re.compile(r"\b(?:wears|wearing|dressed in|outfit|(?:brown|blue|green) eyes|"
                        r"(?:dark|blond|blonde|black|brown|red|curly|straight|long|short) hair|"
                        r"(?:olive|silver|red|blue|black|white) (?:shirt|top|shorts|dress)|"
                        r"muscular body|slim body)\b", re.I)
WRAP_UP = re.compile(r"\b(?:capturing (?:the|an)|embodying|symbolizing|evoking (?:the|a)|a testament to)\b", re.I)
SIZES = re.compile(r"\b(?:wide shot|medium(?:[- ]tight| full)?(?: shot| framing)?|close[- ]up|"
                   r"full[- ]body|full shot|tight framing|upper body|overhead view)\b", re.I)
COMPLETED_ACTIONS = {
    "sitting down": (r"\b(?:sits? down|sat down|sitting down|seated)\b", r"\b(?:sits? down|sat down|sitting down)\b"),
    "opening the door": (r"\b(?:opens?|opened|opening) (?:the|a) door\b", r"\b(?:opens?|opened|opening) (?:the|a) door\b"),
    "picking up the cup": (r"\b(?:picks?|picked|picking) up (?:the|a) cup\b", r"\b(?:picks?|picked|picking) up (?:the|a) cup\b"),
}
REF_FIELDS = ("subject_definitions", "summary", "retention_analysis", "detailed_description",
              "overall_soundscape", "non_diegetic_music")
BASE_FIELDS = ("integrated_multimodal_description", "overall_soundscape", "non_diegetic_music")


def frame_at(seconds, fps):
    return int((Decimal(str(seconds)) * Decimal(str(fps))).to_integral_value(rounding=ROUND_HALF_UP))


def _decimal(value):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError("FPS and duration must be finite positive numbers") from None
    if not result.is_finite() or result <= 0:
        raise ValueError("FPS and duration must be finite positive numbers")
    return result


def lint(text, fps=24, duration=15, schedule=None, context=None):
    fps, duration = _decimal(fps), _decimal(duration)
    context = context or {}
    if not isinstance(context, dict):
        raise ValueError("context must be a JSON object")
    findings, shots = [], []

    def add(code, message, line=None, severity="warning"):
        findings.append(dict(code=code, severity=severity, message=message,
                             **({"line": line} if line is not None else {})))

    for line_no, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        match = INTERVAL.fullmatch(line.strip())
        if not match:
            add("interval-format", "Expected [MM:SS.sss - MM:SS.sss] followed by a shot body.", line_no, "error")
            continue
        mm, ss, end_mm, end_ss, body = match.groups()
        start, end = Decimal(mm) * 60 + Decimal(ss), Decimal(end_mm) * 60 + Decimal(end_ss)
        idx = len(shots) + 1
        previous = shots[-1]["end"] if shots else Decimal(0)
        # Permit millisecond display rounding of exact frame/FPS intervals, not missing frames.
        if abs(start - previous) > Decimal("0.001"):
            add("interval-continuity", "Shot intervals must start at zero and meet without gaps or overlaps.", line_no, "error")
        if start >= end or end > duration + Decimal("0.001"):
            add("interval-range", "Shot needs positive length within the supplied duration.", line_no, "error")
        frame = frame_at(start, fps)
        if shots and frame <= shots[-1]["frame"]:
            add("frame-collision", "Two shots start at the same frame or run backward at this FPS.", line_no, "error")
        shots.append(dict(start=start, end=end, body=body, frame=frame, line=line_no))
        camera = re.match(r"^\[([^\]]+)\]", body)
        if not camera:
            add("camera-command", "Start the shot body with one bracketed camera command.", line_no, "error")
        elif not SIZES.search(body[:160]):
            add("shot-size", "State one shot size near the camera command.", line_no)
        prose = body[camera.end():] if camera else body
        if re.search(r"<d>|</d>", prose, re.I):
            add("dialogue-review", "Preserve dialogue verbatim; profile prose checks exclude <d>...</d> content.", line_no, "info")
        prose = re.sub(r"<d>.*?</d>", "", prose, flags=re.I | re.S)
        for match in re.finditer(r"\b(\w+)(\s+)\1\b", prose, re.I):
            add("repeated-word", f"Repeated word: {match.group(0)!r}.", line_no)
        for match in WORD.finditer(prose):
            if match.group().lower() in TYPO:
                add("spelling", f"Possible typo {match.group()!r}; use {TYPO[match.group().lower()]!r}.", line_no)
        if NEGATIVE.search(prose):
            add("negative-prose", "Profile asks for positive visible action; review negative wording.", line_no)
        if idx > 1 and CARRYOVER.search(prose):
            add("prior-cut-replay", "Start from the current pose rather than retelling a prior action.", line_no)
        if not context.get("appearance_override") and APPEARANCE.search(prose):
            add("appearance-prose", "Let the reference supply appearance unless an override was requested.", line_no)
        for anchor in context.get("subject_anchors", []):
            if not isinstance(anchor, str) or not anchor.strip():
                raise ValueError("subject_anchors must contain nonempty strings")
            mentions = list(re.finditer(r"(?<!\w)" + re.escape(anchor) + r"(?!\w)", prose, re.I))
            if len(mentions) > 1:
                add("repeated-subject", f"{anchor!r} occurs {len(mentions)} times; prefer pronouns after its first use.", line_no)
        if WRAP_UP.search(prose):
            add("wrap-up", "Remove interpretive wrap-up prose; end on the environment/light cue.", line_no)
        if camera:
            command = camera.group(1).lower()
            if "static" in command and re.search(r"\b(?:pans?|orbits?|tracks?|dollies|push(?:es)? in)\b", body, re.I):
                add("camera-conflict", "A static camera command conflicts with a moving-camera instruction.", line_no)
            if ("clockwise" in command and re.search(r"\b(?:counterclockwise|anticlockwise)\b", body, re.I)):
                add("camera-conflict", "Orbit direction changes within one cut; review the intended vector.", line_no)
        if re.search(r"close[- ]up", body, re.I) and re.search(r"\b(?:whole|full|entire)[- ]body\b", body, re.I):
            add("framing-conflict", "Close-up and whole-body framing compete within one cut.", line_no)
        length, count = end - start, len(WORD.findall(prose))
        limit = 35 if length <= 2 else 65 if length < 6 else 85
        if count > limit:
            add("action-budget", f"{count} words in {length}s; profile suggests at most {limit}. Review action count as well.", line_no)
        if idx in context.get("high_energy_shots", []) and re.search(r"\b(?:peaceful|calm|serene)\b", prose, re.I):
            add("energy-conflict", "Calm/peaceful wording conflicts with this shot's explicit high-energy brief.", line_no)
        suffix = context.get("environment_suffixes", {}).get(str(idx), context.get("environment_suffix"))
        if suffix and not body.rstrip().endswith(suffix):
            add("environment-lock", "End this cut with its supplied environment/lighting suffix verbatim.", line_no)

    if not shots:
        add("empty-prompt", "Provide at least one timestamped shot.", severity="error")
    elif abs(shots[-1]["end"] - duration) > Decimal("0.001"):
        add("duration-end", "The last cut must end at the supplied duration.", shots[-1]["line"], "error")
    action_history = {}
    for shot in shots:
        # Review only a repeated explicit actor, so two different people can perform the same action.
        actor = re.search(r"\bthe (?:woman|man|dancer|singer|warrior)\b", shot["body"], re.I)
        actor = actor.group().lower() if actor else None
        for label, (earlier, current) in COMPLETED_ACTIONS.items():
            if actor and re.search(current, shot["body"], re.I) and label in action_history.get(actor, set()):
                add("action-replay", f"{actor!r} already has {label!r} in an earlier cut. Check for an unintended restart; a deliberate repeat can be retained.", shot["line"])
            if actor and re.search(earlier, shot["body"], re.I):
                action_history.setdefault(actor, set()).add(label)
    generation_text = re.sub(r"<d>.*?</d>", "", text, flags=re.I | re.S)
    if len(shots) > 1 and re.search(r"\b(?:no cuts|single continuous shot|one continuous shot)\b", generation_text, re.I):
        add("cut-contradiction", "Multiple shot intervals conflict with an uncut-shot instruction.", severity="error")

    if schedule is not None:
        if not isinstance(schedule, dict) or any(not isinstance(k, str) or not re.fullmatch(r"0|[1-9]\d*", k)
                                                 or not isinstance(v, str) for k, v in schedule.items()):
            add("schedule-format", "Schedule must be a JSON object of frame-number strings to prompt strings.", severity="error")
        elif list(schedule) != [str(s["frame"]) for s in shots]:
            add("schedule-frames", "Schedule keys/order must match round-half-up(start seconds * FPS).", severity="error")
        else:
            for shot in shots:
                if schedule[str(shot["frame"])] != shot["body"]:
                    add("schedule-body", "Scheduled text differs from the corresponding timestamped shot body.", shot["line"], "error")
    return dict(ok=not any(f["severity"] == "error" for f in findings), findings=findings,
                shot_count=len(shots), cut_count=max(0, len(shots) - 1),
                start_frames=[s["frame"] for s in shots], fps=float(fps), duration=float(duration))


def lint_native(text, fps=24, duration=15, context=None):
    """Audit native H3 fields and shot bodies with the same user profile.

    Ref2VA requires six fields; base modes require three. Exact input/reference binding remains
    the production linter's responsibility. Native mode does not compare a scheduler JSON block.
    """
    fps, duration = _decimal(fps), _decimal(duration)
    fields = REF_FIELDS if re.search(r"(?m)^\s*subject_definitions\s*:", text) else BASE_FIELDS
    pattern = re.compile(r"(?m)^\s*(" + "|".join(REF_FIELDS + BASE_FIELDS) + r")\s*:")
    headers = list(pattern.finditer(text))
    names = [match.group(1) for match in headers]
    findings = []

    def error(code, message):
        findings.append(dict(code=code, severity="error", message=message))

    if names != list(fields):
        error("section-structure", "Native H3 sections must appear once in order: " + ", ".join(fields))
    sections = {}
    for i, header in enumerate(headers):
        sections[header.group(1)] = text[header.end():headers[i + 1].start() if i + 1 < len(headers) else len(text)].strip()
    for name in fields:
        if not sections.get(name):
            error("missing-section", f"Missing or empty {name!r} section.")
    body = sections.get("detailed_description", sections.get("integrated_multimodal_description", ""))
    markers = list(re.finditer(r"\[Shot (\d+)\]", body))
    if markers and [int(m.group(1)) for m in markers] != list(range(1, len(markers) + 1)):
        error("shot-order", "Shot definitions must be consecutive, beginning with Shot 1.")
    bodies, starts = [], []
    if markers:
        preamble = body[:markers[0].start()].strip()
        for i, marker in enumerate(markers):
            content = body[marker.end():markers[i + 1].start() if i + 1 < len(markers) else len(body)].strip()
            time = re.match(r"At (\d{2}):([0-5]\d\.\d{3})\s*[,.:]?\s*", content)
            if i == 0:
                starts.append(Decimal(0))
                if time or re.match(r"(?:\d+:)?\d+\.\d+", content):
                    error("first-shot-time", "Shot 1 begins directly with its description, without a timestamp.")
            elif time:
                starts.append(Decimal(time.group(1)) * 60 + Decimal(time.group(2)))
            else:
                error("shot-timestamp", f"Shot {i + 1} needs 'At MM:SS.mmm,' before its body.")
            bodies.append(content[time.end():] if time else content)
    else:
        preamble, starts, bodies = "", [Decimal(0)], [body]
    if findings:
        return dict(ok=False, findings=findings, shot_count=len(bodies), cut_count=max(0, len(bodies) - 1))

    def stamp(value):
        return f"{int(value // 60):02d}:{value % 60:06.3f}"

    normalized = "\n".join(f"[{stamp(start)} - {stamp(end)}] {content.replace(chr(10), ' ')}"
                           for start, end, content in zip(starts, starts[1:] + [duration], bodies))
    result = lint(normalized, fps, duration, context=context)
    # Headings and retention may cite Shot N but only actual shot bodies count as cuts.
    promises = " ".join((sections.get("summary", ""), preamble))
    if len(bodies) > 1 and re.search(r"\b(?:no cuts|single continuous shot|one continuous shot)\b", promises, re.I):
        result["findings"].append(dict(code="cut-contradiction", severity="error",
                                        message="The summary/preamble promises an uncut shot but defines multiple shots."))
        result["ok"] = False
    result["format"] = "native-h3"
    return result


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prompt", type=Path)
    parser.add_argument("--fps", default="24")
    parser.add_argument("--duration", required=True)
    parser.add_argument("--schedule", type=Path)
    parser.add_argument("--context", type=Path)
    parser.add_argument("--strict", action="store_true", help="Also exit 1 for warnings")
    parser.add_argument("--format", choices=("cuts", "h3"), default="cuts")
    args = parser.parse_args()
    try:
        def load(path):
            return json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=_unique_object) if path else None
        text = args.prompt.read_text(encoding="utf-8-sig")
        if args.format == "h3":
            if args.schedule:
                raise ValueError("Use timestamped cuts format to compare a frame schedule")
            result = lint_native(text, args.fps, args.duration, load(args.context))
        else:
            result = lint(text, args.fps, args.duration, load(args.schedule), load(args.context))
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return int(not result["ok"] or (args.strict and any(f["severity"] == "warning" for f in result["findings"])))


if __name__ == "__main__":
    raise SystemExit(main())
