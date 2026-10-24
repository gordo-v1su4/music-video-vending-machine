"""Keyframe stills from MiniMax H3 with RefMods: no Qwen, no commercial models, submitted through SwarmUI.

One latent frame (Fizgig H3 Still Latent) sampled by H3 and decoded with Fizgig H3 Still Decode. RefMods
(characters and environments) are attached with H3 RefMod Text Encode, which numbers them in loader order as
<Picture 1>, <Picture 2>, ... so the prompt can say which picture is who or where.

  uv run --python 3.12 python -m mvvm_gen.h3_still --mods Lune_identity_multi --prompt-file P.txt --out OUT.png \\
      [--config eros_er|base] [--mp 2.5] [--seed N]

Writes OUT.png plus OUT.json (graph, prompt, mods, reference map, config, Swarm result, seconds).
"""

import argparse
import glob
import json
import math
import os
import shutil
import time

from . import swarm_raw

CONFIGS = {
    # Eros turbo GGUF (the demo video model) on er_sde, the sampler Fizgig recommends for stills. Its video pass-1
    # sigmas (5 steps, res_multistep) break a still into a collage (2026-10-11 test), so they are not offered.
    "eros_er": {"loader": ("UnetLoaderGGUF", {"unet_name": "10Eros-Max-Turbo-Beta5-Q6_K.gguf"}),
                "sampler": "er_sde", "steps": 12},
    # Plain ref2va base, no LoRA, full steps: slowest, the quality reference.
    "base": {"loader": ("UNETLoader", {"unet_name": "minimax_h3_ref2va_pruned_int8_convrot.safetensors",
                                       "weight_dtype": "default"}),
             "sampler": "er_sde", "steps": 40},
}
MOD_SLOTS = 8


def size_for(mp, aspect=(16, 9)):
    w = math.sqrt(mp * 1e6 * aspect[0] / aspect[1])
    w, h = int(w // 64 * 64), int(w * aspect[1] / aspect[0] // 64 * 64)  # 64 keeps the latent grid even
    return w, h


def build(prompt, mods, seed, prefix, config="eros_er", mp=2.5, aspect=(16, 9), strengths=None):
    cfg = CONFIGS[config]
    w, h = size_for(mp, aspect)
    loader = {"show_info": True, "max_total_tokens": 0}
    for i in range(1, MOD_SLOTS + 1):
        name = mods[i - 1] if i <= len(mods) else "(none)"
        loader.update({f"mod_{i}": name, f"strength_{i}": (strengths or {}).get(name, 1.0), f"copies_{i}": 1,
                       f"components_{i}": "All", f"visual_strength_{i}": 1.0, f"audio_strength_{i}": 1.0})
    g = {
        "model": {"class_type": cfg["loader"][0], "inputs": dict(cfg["loader"][1])},
        "shift": {"class_type": "MiniMaxH3SigmaShift", "inputs": {"model": ["model", 0], "shift_video": 12.0,
                                                                  "shift_audio": 3.0}},
        "clip": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen3vl_32b_minimax_h3_int8_convrot.safetensors",
                                                        "type": "minimax", "device": "default"}},
        "vae": {"class_type": "VAELoader", "inputs": {"vae_name": "minimax_h3_video_vae_int8_convrot.safetensors"}},
        "mods": {"class_type": "MiniMaxH3RefModsLoader", "inputs": loader},
        "encode": {"class_type": "MiniMaxH3RefModTextEncode", "inputs": {"clip": ["clip", 0], "mods": ["mods", 0],
                                                                         "prompt": prompt, "reference_fps": 24.0,
                                                                         "max_total_tokens": 0, "vae": ["vae", 0]}},
        "latent": {"class_type": "FizgigH3StillLatent", "inputs": {"width": w, "height": h, "batch_size": 1}},
        "noise": {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}},
        "sampler": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": cfg["sampler"]}},
        "guider": {"class_type": "BasicGuider", "inputs": {"model": ["shift", 0], "conditioning": ["encode", 0]}},
        "sample": {"class_type": "SamplerCustomAdvanced", "inputs": {"noise": ["noise", 0], "guider": ["guider", 0],
                                                                     "sampler": ["sampler", 0], "sigmas": ["sigmas", 0],
                                                                     "latent_image": ["latent", 0]}},
        "decode": {"class_type": "FizgigH3StillDecode", "inputs": {"samples": ["sample", 0], "vae": ["vae", 0]}},
        "save": {"class_type": "SaveImage", "inputs": {"images": ["decode", 0], "filename_prefix": prefix}},
        "refmap": {"class_type": "PreviewAny", "inputs": {"source": ["encode", 1]}},
    }
    if "sigmas" in cfg:
        g["sigmas"] = {"class_type": "ManualSigmas", "inputs": {"sigmas": cfg["sigmas"]}}
    else:
        g["sigmas"] = {"class_type": "BasicScheduler", "inputs": {"model": ["shift", 0], "scheduler": "simple",
                                                                  "steps": cfg["steps"], "denoise": 1.0}}
    return g, (w, h)


SLOT_IDS = ("first", "second", "third")  # Swarm keeps only lowercase letters in parameter ids
REALISM_LORA = "mini\\h3-realism-people-t2v-i2v-r2v.safetensors"


def _swarm_input(kind, title, raw_id, value, order, description, **extra):
    inputs = {"title": title, "value": value, "description": description, "order_priority": order,
              "is_advanced": False, "raw_id": raw_id, **extra}
    return {"class_type": f"SwarmInput{kind}", "inputs": inputs}


def swarm_template(config="eros_er", slots=3):
    """The still graph with SwarmUI input nodes, for saving as a Swarm workflow (Comfy Workflow tab) and presets.

    Prompt, seed, width, height and steps reuse Swarm's core parameters (raw_id), so Generate-tab metadata records
    them; RefMod slots are dropdowns that list the loader's RefMods; the realism LoRA strength defaults to 0."""
    g, _ = build("", [], 0, "MVVM/stills/h3-still", config)
    num = dict(step=1, min=0, max=100, view_max=100, view_type="small")
    g["in_prompt"] = _swarm_input("Text", "Prompt", "prompt", "", 0,
                                  "H3 prompt. RefMods are <Picture 1>, <Picture 2>, ... in slot order.", view_type="prompt")
    g["in_seed"] = _swarm_input("Integer", "Seed", "seed", 21, 0, "Sampler seed.", step=1, min=-1, max=2**31 - 1,
                                view_max=2**31 - 1, view_type="seed")
    g["in_width"] = _swarm_input("Integer", "Width", "width", 2048, 0, "Multiple of 64.", step=64, min=512, max=4096,
                                 view_max=4096, view_type="pot_slider")
    g["in_height"] = _swarm_input("Integer", "Height", "height", 1152, 0, "Multiple of 64.", step=64, min=512,
                                  max=4096, view_max=4096, view_type="pot_slider")
    g["in_steps"] = _swarm_input("Integer", "Steps", "steps", CONFIGS[config].get("steps", 12), 0,
                                 "er_sde steps (12 is the tested Eros setting).", **num)
    g["in_realism"] = _swarm_input("Float", "Realism LoRA Strength", "realismlorastrength", 0.0, 2,
                                   "h3-realism-people LoRA on the model; 0 = off.", step=0.05, min=0, max=1.5,
                                   view_max=1.5, view_type="slider")
    g["lora"] = {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["model", 0], "lora_name": REALISM_LORA,
                                                                 "strength_model": ["in_realism", 0]}}
    g["shift"]["inputs"]["model"] = ["lora", 0]
    g["encode"]["inputs"]["prompt"] = ["in_prompt", 0]
    g["noise"]["inputs"]["noise_seed"] = ["in_seed", 0]
    g["latent"]["inputs"].update(width=["in_width", 0], height=["in_height", 0])
    g["sigmas"]["inputs"]["steps"] = ["in_steps", 0]
    for i in range(1, slots + 1):
        g[f"in_mod{i}"] = _swarm_input("Dropdown", f"RefMod {i}", f"refmod{SLOT_IDS[i - 1]}", "(none)", 1,
                                       f"Becomes <Picture {i}> (characters first, then the location).", values="")
        g[f"in_mod{i}_s"] = _swarm_input("Float", f"RefMod {i} Strength", f"refmod{SLOT_IDS[i - 1]}strength", 1.0, 1,
                                         "1 = full reference.", step=0.05, min=0, max=1, view_max=1, view_type="slider")
        g["mods"]["inputs"][f"mod_{i}"] = [f"in_mod{i}", 0]
        g["mods"]["inputs"][f"strength_{i}"] = [f"in_mod{i}_s", 0]
    g["save"]["inputs"]["filename_prefix"] = "MVVM/stills/h3-still"
    return g


def swarm_image(result):
    """Local path of the first PNG Swarm reports (View/local/... under D:/output/local)."""
    rel = result["images"][0].split("View/local/", 1)[1]
    path = f"D:/output/local/{rel}"
    for _ in range(30):
        if os.path.exists(path):
            return path
        hits = glob.glob(os.path.join(os.path.dirname(path), os.path.basename(path).split("-", 1)[0] + "-*.png"))
        if hits:
            return hits[0]
        time.sleep(1)
    raise FileNotFoundError(path)


def render(prompt, mods, out, seed=42, config="eros_er", mp=2.5, aspect=(16, 9), strengths=None):
    graph, size = build(prompt, mods, seed, "mvvm/stills/" + os.path.splitext(os.path.basename(out))[0],
                        config, mp, aspect, strengths)
    started = time.monotonic()
    result = swarm_raw.run(graph, prompt=prompt[:200])
    if "images" not in result:
        raise RuntimeError(f"{out}: {json.dumps(result)[:800]}")
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    shutil.copy(swarm_image(result), out)
    meta = {"prompt": prompt, "mods": mods, "strengths": strengths, "seed": seed, "config": config, "size": size,
            "swarm": result, "elapsed_s": round(time.monotonic() - started, 1), "graph": graph}
    with open(os.path.splitext(out)[0] + ".json", "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=1)
    return meta


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mods", nargs="*", default=[], help="RefMod names in <Picture n> order")
    ap.add_argument("--prompt")
    ap.add_argument("--prompt-file")
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--config", choices=sorted(CONFIGS), default="eros_er")
    ap.add_argument("--mp", type=float, default=2.5)
    args = ap.parse_args(argv)
    prompt = args.prompt or open(args.prompt_file, encoding="utf-8").read()
    meta = render(prompt, args.mods, args.out, args.seed, args.config, args.mp)
    print(json.dumps({k: meta[k] for k in ("out", "size", "elapsed_s") if k in meta} | {"out": args.out}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
