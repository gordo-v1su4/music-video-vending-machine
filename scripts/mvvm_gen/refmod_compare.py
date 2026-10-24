"""Build Lune identity RefMods from view sets and compare them on identical C2 graphs, all through SwarmUI.

Each variant is a MiniMaxH3RefModExtract (Full Reference, identity, 5120-token cap) over its own list of views; the
view list is the only difference. Each RefMod then renders the saved C2 graphs with only the RefMod dropdown changed
(same prompt, seed, guides and refs), and every clip is scored with face_check (ArcFace median vs the master
close-up). Scores are evidence only; the user's eye decides.

  uv run --python 3.12 python -m mvvm_gen.refmod_compare [--variants master4 swaps] [--res 640] [--skip-extract]
"""

import argparse
import copy
import glob
import json
import os
import shutil
import subprocess
import time

from . import swarm_raw

ROOT = "D:/output/local/MVVM"
LUNE = f"{ROOT}/i-ran-pilot/sheets/lune"
PACKET = f"{ROOT}/demo-v1s155/packet"
OUT = f"{ROOT}/demo-v1s155/refmod-compare"
COMFY_INPUT = "D:/ComfyUI_V89/ComfyUI/input"
REFMODS = "D:/ComfyUI_V89/ComfyUI/models/refmods"
COMFY_PY = r"D:\ComfyUI_V89\ComfyUI\venv\Scripts\python.exe"
MASTER = f"{LUNE}/closeup-named.png"
MASTER4 = [f"{LUNE}/closeup.png", f"{LUNE}/portrait.png", f"{LUNE}/front.png", f"{LUNE}/side.png"]
LOOK = "Silver wrapped headband with yellow wildflowers, wavy chestnut hair, silver halter."
VARIANTS = {
    "master4": (MASTER4, "the four master sheet views only (closeup, portrait, front, side)"),
    "swaps": (MASTER4 + sorted(glob.glob(f"{LUNE}/set2/swap*.png")),
              "the four master sheet views plus the six Qwen 2.1 face-swap angle views (set2)"),
    "grey": (sorted(glob.glob(f"{LUNE}/grey/view*.png")), "the grey 4-view sheet, cropped to four images"),
}
# Saved C2 graphs whose node 110 picks the RefMod; existing renders with Lune_identity_multi are the baseline.
GRAPHS = {"v2": "c2-anchor/rep2-v2-multi-sheet.api.json", "v3": "c2-anchor/rep2-v3-multi-last.api.json"}
BASELINE = {"v2": f"{ROOT}/demo-v1s155/renders/rep2-v2-multi-sheet_1.mp4",
            "v3": f"{ROOT}/demo-v1s155/renders/rep2-v3-multi-last_1.mp4"}


def refmod_name(variant):
    return f"Lune_identity_{variant}"


def extract(variant, res):
    views, about = VARIANTS[variant]
    if not views:
        raise SystemExit(f"{variant}: no views on disk")
    g = {"vae": {"class_type": "VAELoader", "inputs": {"vae_name": "minimax_h3_video_vae_int8_convrot.safetensors"}}}
    ext = {"name": refmod_name(variant), "mode": "Full Reference", "concept_type": "identity",
           "background_retention": 0.0, "ref_resolution": res, "pool_h": 16, "pool_w": 16, "latent_frames": 16,
           "identity": 500, "merge": False, "motion_only": False, "multiplier": 1, "max_tokens": 5120, "save": True,
           "budget_policy": "error", "extraction_preset": "manual", "subfolder": "", "vae": ["vae", 0],
           "description": f"Lune, identity from {about}. {LOOK}"}
    for i, path in enumerate(views):
        name = f"mvvm-lune-{variant}-{i}{os.path.splitext(path)[1]}"
        shutil.copy(path, f"{COMFY_INPUT}/{name}")
        g[f"img{i}"] = {"class_type": "LoadImage", "inputs": {"image": name}}
        ext[f"refs_image.ref_image_{i}"] = [f"img{i}", 0]
    g["extract"] = {"class_type": "MiniMaxH3RefModExtract", "inputs": ext}
    with open(f"{OUT}/{variant}.extract.api.json", "w", encoding="utf-8") as fh:
        json.dump(g, fh, indent=1)
    started = time.monotonic()
    res_ = swarm_raw.run(g, prompt=f"Lune RefMod {variant} extraction")
    path = f"{REFMODS}/{refmod_name(variant)}.safetensors"
    if not os.path.exists(path):
        raise SystemExit(f"{variant}: extraction did not write {path}: {json.dumps(res_)[:600]}")
    return {"views": views, "res": res, "refmod": path, "elapsed_s": round(time.monotonic() - started, 1)}


def swarm_file(result, ext=".mp4"):
    """Local path of the first output Swarm reports (View/local/... under D:/output/local)."""
    rel = result["images"][0].split("View/local/", 1)[1]
    path = f"D:/output/local/{rel}"
    for _ in range(30):
        if os.path.exists(path):
            return path
        hits = glob.glob(os.path.join(os.path.dirname(path), os.path.basename(path).split("-", 1)[0] + f"-*{ext}"))
        if hits:
            return hits[0]
        time.sleep(1)
    raise FileNotFoundError(path)


def render(variant, key):
    with open(f"{PACKET}/{GRAPHS[key]}", encoding="utf-8") as fh:
        g = json.load(fh)
    g = copy.deepcopy(g)
    g["110"]["inputs"]["value"] = refmod_name(variant)
    dest = f"{OUT}/{key}-{variant}.mp4"
    if os.path.exists(dest):
        return dest
    started = time.monotonic()
    result = swarm_raw.run(g, prompt=f"C2 {key} with {refmod_name(variant)}")
    if "images" not in result:
        raise SystemExit(f"{key}-{variant}: {json.dumps(result)[:600]}")
    shutil.copy(swarm_file(result), dest)
    with open(dest[:-4] + ".json", "w", encoding="utf-8") as fh:
        json.dump({"graph": GRAPHS[key], "refmod": refmod_name(variant), "swarm": result,
                   "elapsed_s": round(time.monotonic() - started, 1)}, fh, indent=1)
    return dest


def faces(video):
    out = subprocess.run([COMFY_PY, os.path.join(os.path.dirname(__file__), "face_check.py"), MASTER, video], capture_output=True, text=True)
    line = next((l for l in out.stdout.splitlines() if l.startswith("{")), None)
    return json.loads(line) if line else {"error": out.stderr[-400:]}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--variants", nargs="+", default=["master4", "swaps"], choices=sorted(VARIANTS))
    ap.add_argument("--res", type=int, default=640)
    ap.add_argument("--skip-extract", action="store_true")
    args = ap.parse_args(argv)
    os.makedirs(OUT, exist_ok=True)
    report_path = f"{OUT}/report.json"
    report = json.load(open(report_path, encoding="utf-8")) if os.path.exists(report_path) else {}
    for key, clip in BASELINE.items():
        report.setdefault(f"{key}-multi", {"clip": clip, "refmod": "Lune_identity_multi", "faces": faces(clip)})
    for variant in args.variants:
        if not args.skip_extract:
            report[f"refmod-{variant}"] = extract(variant, args.res)
            print(f"[{variant}] extracted {report[f'refmod-{variant}']}", flush=True)
        for key in GRAPHS:
            clip = render(variant, key)
            report[f"{key}-{variant}"] = {"clip": clip, "refmod": refmod_name(variant), "faces": faces(clip)}
            print(f"[{key}-{variant}] {report[f'{key}-{variant}']['faces'].get('median')}", flush=True)
            with open(report_path, "w", encoding="utf-8") as fh:
                json.dump(report, fh, indent=1)
    with open(report_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1)
    for k, v in report.items():
        if "faces" in v:
            print(k, v["faces"].get("median"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
