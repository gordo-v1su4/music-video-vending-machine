"""SwarmUI presets for H3 + RefMod keyframe stills, and runs that apply them (Generate tab equivalent).

Every preset targets the saved 'MVVM H3 Still RefMods' workflow. In the Generate tab: pick the preset, press
Generate. `run` sends the same preset by name to GenerateText2Image (`presets: [...]`), so Swarm applies it exactly
as the Generate tab does and records the full parameter set in the image metadata and history.

  uv run --python 3.12 python -m mvvm_gen.still_presets PLAN.json add                 # create/update presets
  uv run --python 3.12 python -m mvvm_gen.still_presets PLAN.json run [--only ID ...]  # generate from presets
  uv run --python 3.12 python -m mvvm_gen.still_presets PLAN.json model-test KEYFRAME_ID [--models eros hybrid ...]
"""

import argparse
import json
import os

from . import swarm_raw

WORKFLOW = "MVVM - I Ran Music Video/MVVM H3 Still RefMods"
FOLDER = "MVVM - I Ran Music Video/Stills"
MODEL = "10Eros-Max-Turbo-Beta5-Q6_K.gguf"
# Swarm keeps only lowercase letters in parameter ids (CleanTypeName), so slots are named, never numbered.
SLOT_IDS = ("first", "second", "third")
# Still models: (safetensors name or None for the Eros GGUF, er_sde steps). Eros is the default.
STILL_MODELS = {
    "eros": (None, 12),
    "hybrid": ("minimax_h3_hybrid_fl2va_ref2va_b25-49-int8.safetensors", 20),
    "singularity": ("Minimax-h3_Singularity_ref2va_v1.3_Pruned_w4a8.safetensors", 20),
    "fasth3": ("fastvideo_fasth3_trim_8step_nvfp4.safetensors", 8),
}
OUT_ROOT = "D:/output/local/"  # Swarm's output root for the local user; overrideoutpathformat is relative to it


def loc_mod(plan, loc):
    """The location's RefMod: the plan's `refmod` for it (e.g. a Look_* mod from the reference video) or its plate."""
    return plan["locations"].get(loc, {}).get("refmod") or f"Loc_{loc}_background"


def keyframe_prompt(plan, kf):
    mods, defs = [], []
    for cid in kf.get("characters", []):
        ch = plan["characters"][cid]
        mods.append(ch["refmod"])
        defs.append(f"<Subject {len(mods)}> is {ch['define']} Same person as <Picture {len(mods)}>: the exact face.")
    loc = kf.get("location")
    if loc and kf.get("use_location", True):
        mods.append(loc_mod(plan, loc))
        defs.append(f"<Picture {len(mods)}> sets the place and the look: match its light, colour grade, darkness, haze "
                    f"and film texture. Its people are only extras, never the named characters.")
    prompt = (f"subject_definitions: {' '.join(defs)}\n"
              f"summary: A single still frame from a music video, the camera locked and still.\n"
              f"detailed_description: {kf['prompt']} {plan['style']}")
    return prompt, mods


def param_map(prompt, mods, seed, outpath, model="eros", size=(2048, 1152), loc_strength=1.0, has_loc=False):
    if len(mods) > 3:
        raise ValueError(f"the workflow has 3 RefMod slots, got {mods}")
    slots = (mods + ["(none)"] * 3)[:3]
    unet, steps = STILL_MODELS[model]
    p = {"images": "1", "model": MODEL, "comfyuicustomworkflow": WORKFLOW, "prompt": prompt, "seed": str(seed),
         "width": str(size[0]), "height": str(size[1]), "steps": str(steps), "realismlorastrength": "0",
         "useerosgguf": "true" if unet is None else "false", "overrideoutpathformat": outpath}
    if unet:
        p["stillmodel"] = unet
    for i, name in enumerate(slots, 1):
        # the location/look RefMod is always the last filled slot; keyframes may weaken it (`loc_strength`)
        strength = loc_strength if has_loc and i == len(mods) else 1.0
        p[f"refmod{SLOT_IDS[i - 1]}"], p[f"refmod{SLOT_IDS[i - 1]}strength"] = name, f"{strength:g}"
    return p


def presets(plan, model="eros"):
    """{name: (description, param_map)} for every keyframe and seed in the plan, on one still model."""
    rel = os.path.relpath(plan["out"], OUT_ROOT).replace("\\", "/")
    tag = "" if model == "eros" else f" {model}"
    out = {}
    for kf in plan["keyframes"]:
        prompt, mods = keyframe_prompt(plan, kf)
        for seed in kf.get("seeds", [21]):
            name = f"{FOLDER}/{kf['id']} s{seed}{tag}"
            outpath = f"{rel}/keyframes/{kf['id']}-{seed}" + (f"-{model}" if tag else "")
            out[name] = (f"{kf['id']}: {', '.join(mods) or 'no RefMods'}; seed {seed}; model {model}.",
                         param_map(prompt, mods, seed, outpath, model, tuple(kf.get("size", (2048, 1152))),
                                   kf.get("loc_strength", 1.0), bool(kf.get("location")) and kf.get("use_location", True)))
    return out


def add(items):
    sid = swarm_raw.post(swarm_raw.SWARM, "GetNewSession", {})["session_id"]
    for name, (desc, pm) in items.items():
        body = {"session_id": sid, "title": name, "description": desc, "param_map": pm, "is_edit": True,
                "editing": name}
        res = swarm_raw.post(swarm_raw.SWARM, "AddNewPreset", body)
        if "error" in res:  # not there yet: create it
            body.update(is_edit=False, editing=None)
            res = swarm_raw.post(swarm_raw.SWARM, "AddNewPreset", body)
        print(f"[preset] {name}: {res.get('error') or 'ok'}", flush=True)


def run(items):
    sid = swarm_raw.post(swarm_raw.SWARM, "GetNewSession", {})["session_id"]
    for name in items:
        res = swarm_raw.post(swarm_raw.SWARM, "GenerateText2Image", {"session_id": sid, "images": 1,
                                                                      "presets": [name]})
        print(f"[run] {name}: {res.get('error') or res.get('images')}", flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("action", choices=("add", "run", "model-test"))
    ap.add_argument("keyframe", nargs="?")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--models", nargs="*", default=sorted(STILL_MODELS))
    args = ap.parse_args(argv)
    with open(args.plan, encoding="utf-8") as fh:
        plan = json.load(fh)
    if args.action == "model-test":
        plan["keyframes"] = [k for k in plan["keyframes"] if k["id"] == args.keyframe]
        items = {}
        for m in args.models:
            items.update(presets(plan, model=m))
        add(items)
        run(items)
        return 0
    if args.only:
        plan["keyframes"] = [k for k in plan["keyframes"] if k["id"] in args.only]
    items = presets(plan)
    (add if args.action == "add" else run)(items)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
