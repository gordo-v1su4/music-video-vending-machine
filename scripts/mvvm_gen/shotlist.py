"""Render a plan's shot list as Markdown (story, timing, setups, render settings).

Usage: python -m scripts.mvvm_gen.shotlist <plan.json> <out.md>
"""

import json
import sys

from . import timing


def write(plan_path, out_path):
    with open(plan_path, encoding="utf-8-sig") as fh:
        plan = json.load(fh)
    bpm = plan["song"]["bpm"]
    frames = timing.shot_frames([s["bars"] for s in plan["shots"]], bpm)
    seeds = plan.get("seeds_per_prompt", 1)
    total = sum(frames) / timing.FPS
    lines = [
        f"# {plan['name']} — shot list", "",
        f"{len(plan['shots'])} shots, {sum(s['bars'] for s in plan['shots'])} bars at {bpm} BPM = {total:.1f} s. "
        f"Workflow `{plan.get('clip_workflow', 'h3_ref2v')}`, {seeds} seed(s) per setup, "
        f"{sum((1 + len(s.get('alts', []))) * seeds for s in plan['shots'])} renders.", "",
        "## Story", "",
        "They never find each other again. Flashbacks (moonlit blue-teal) show what they had; every present-day "
        "beat pushes them further apart, both running through the dark jungle in opposite directions. Her fall "
        "match-cuts into another night, where she mistakes a stranger for him.", "",
        "## Look", "", plan["style"], "",
        "## Characters", "",
    ]
    for cid, c in plan["characters"].items():
        lines += [f"- **{c['name']}** — {c['look']}"]
    lines += ["", "## Shots", ""]
    t = 0.0
    for shot, count in zip(plan["shots"], frames):
        start, t = t, t + count / timing.FPS
        who = " + ".join(plan["characters"][c]["name"] for c in shot["characters"]) or "crowd / no leads"
        lines += [f"### {shot['id']} · {start:05.2f}–{t:05.2f} s · {shot['bars']} bars · {who}", "",
                  f"**{shot['summary']}**", "",
                  f"- Main: {shot['framing']} {shot['still']} {shot['motion']} *Camera:* {shot['camera']}"]
        for i, alt in enumerate(shot.get("alts", []), start=1):
            lines += [f"- Alt {i}: {alt.get('framing', shot['framing'])} *Camera:* {alt.get('camera', shot['camera'])}"]
        lines += [f"- Location: {plan['locations'][shot['location']]['prompt']}", ""]
    ov = plan.get("clip_overrides", {})
    lines += ["## Render settings", "",
              "- PlagueKind MiniMax H3 V11 exported unchanged (SLA sparse 0.7, H3 cache, AdaLN fix, res_multistep/simple 13 steps, no turbo LoRA).",
              f"- Deliberate deviations: {json.dumps(ov) if ov else 'none'} (reference protection for identity).",
              f"- Model `{plan.get('clip_unet', 'default')}`, {plan['frame_size'][0]}×{plan['frame_size'][1]} 16:9, 24 fps; cut to {plan['delivery_size'][0]}×{plan['delivery_size'][1]}.",
              "- Characters come only from their sheet panels; backgrounds and extras are text only.", ""]
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return out_path


if __name__ == "__main__":
    print(write(sys.argv[1], sys.argv[2]))
