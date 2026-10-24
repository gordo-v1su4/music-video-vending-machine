"""Location plates, location RefMods and keyframe stills for a passage, all local (H3 + RefMods via SwarmUI).

  uv run --python 3.12 python -m mvvm_gen.h3_keyframes PLAN.json plates      # text-only location plates, N seeds
  uv run --python 3.12 python -m mvvm_gen.h3_keyframes PLAN.json refmods     # chosen plate -> <Loc>_background RefMod
  uv run --python 3.12 python -m mvvm_gen.h3_keyframes PLAN.json keyframes   # character + location RefMods per frame

PLAN.json: {"out": dir, "style": text, "locations": {id: {"prompt": text, "pick": seed|null}},
            "characters": {id: {"refmod": name, "define": text}},
            "keyframes": [{"id", "location", "characters": [...], "prompt": text, "seeds": [...]}]}
Every output gets a .json receipt beside it; the user's eye decides which takes are used.
"""

import argparse
import json
import os
import shutil

from . import h3_still, swarm_raw

COMFY_INPUT = "D:/ComfyUI_V89/ComfyUI/input"
REFMODS = "D:/ComfyUI_V89/ComfyUI/models/refmods"


def loc_mod(loc):
    return f"Loc_{loc}_background"


def plates(plan, args):
    out = os.path.join(plan["out"], "plates")
    for loc, spec in plan["locations"].items():
        for seed in spec.get("seeds", [11, 12]):
            dest = os.path.join(out, f"{loc}-{seed}.png")
            if os.path.exists(dest) and not args.force:
                continue
            prompt = (f"summary: A single still frame of an empty location, no people, the camera locked and still.\n"
                      f"detailed_description: {spec['prompt']} {plan['style']}")
            meta = h3_still.render(prompt, [], dest, seed=seed, config=args.config, mp=args.mp)
            print(f"[plate {loc} {seed}] {meta['elapsed_s']}s -> {dest}", flush=True)


def refmods(plan, args):
    for loc, spec in plan["locations"].items():
        if spec.get("pick") is None:
            print(f"[refmod {loc}] no plate picked; skipped", flush=True)
            continue
        src = os.path.join(plan["out"], "plates", f"{loc}-{spec['pick']}.png")
        name = f"mvvm-plate-{loc}-{spec['pick']}.png"
        shutil.copy(src, f"{COMFY_INPUT}/{name}")
        g = {"vae": {"class_type": "VAELoader", "inputs": {"vae_name": "minimax_h3_video_vae_int8_convrot.safetensors"}},
             "img": {"class_type": "LoadImage", "inputs": {"image": name}},
             "extract": {"class_type": "MiniMaxH3RefModExtract", "inputs": {
                 "name": loc_mod(loc), "mode": "Full Reference", "concept_type": "background",
                 "background_retention": 0.0, "ref_resolution": 1024, "pool_h": 16, "pool_w": 16, "latent_frames": 16,
                 "identity": 0, "merge": False, "motion_only": False, "multiplier": 1, "max_tokens": 5120, "save": True,
                 "budget_policy": "error", "extraction_preset": "manual", "subfolder": "", "vae": ["vae", 0],
                 "description": f"Location plate {loc} (H3 still, seed {spec['pick']}): {spec['prompt'][:300]}",
                 "refs_image.ref_image_0": ["img", 0]}}}
        result = swarm_raw.run(g, prompt=f"RefMod {loc_mod(loc)}")
        ok = os.path.exists(f"{REFMODS}/{loc_mod(loc)}.safetensors")
        print(f"[refmod {loc}] {'saved' if ok else 'FAILED ' + json.dumps(result)[:400]}", flush=True)


def keyframes(plan, args):
    out = os.path.join(plan["out"], "keyframes")
    for kf in plan["keyframes"]:
        if args.only and kf["id"] not in args.only:
            continue
        mods, defs = [], []
        for cid in kf.get("characters", []):
            ch = plan["characters"][cid]
            mods.append(ch["refmod"])
            defs.append(f"<Subject {len(mods)}> is {ch['define']} Same person as <Picture {len(mods)}>: her or his exact face.")
        loc = kf.get("location")
        if loc and plan["locations"].get(loc, {}).get("pick") is not None and kf.get("use_location", True):
            mods.append(loc_mod(loc))
            defs.append(f"<Picture {len(mods)}> is the location: keep its place, light and atmosphere.")
        prompt = (f"subject_definitions: {' '.join(defs)}\n"
                  f"summary: A single still frame from a music video, the camera locked and still.\n"
                  f"detailed_description: {kf['prompt']} {plan['style']}")
        for seed in kf.get("seeds", [21]):
            dest = os.path.join(out, f"{kf['id']}-{seed}.png")
            if os.path.exists(dest) and not args.force:
                continue
            meta = h3_still.render(prompt, mods, dest, seed=seed, config=args.config, mp=args.mp,
                                   aspect=tuple(kf.get("aspect", (16, 9))))
            print(f"[{kf['id']} {seed}] {meta['elapsed_s']}s -> {dest}", flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("stage", choices=("plates", "refmods", "keyframes"))
    ap.add_argument("--config", default="eros_er", choices=sorted(h3_still.CONFIGS))
    ap.add_argument("--mp", type=float, default=2.5)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)
    with open(args.plan, encoding="utf-8") as fh:
        plan = json.load(fh)
    {"plates": plates, "refmods": refmods, "keyframes": keyframes}[args.stage](plan, args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
