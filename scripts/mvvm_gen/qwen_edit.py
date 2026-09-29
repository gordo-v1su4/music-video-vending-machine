"""The locked Qwen Image 2.1 edit call: the user's proven workflow, one command.

Source of truth: SwarmUI `Data/Workflows/kim-ho-qwen/swarm-safe-qwen-2.1-pe-i2i.json` (user-approved 2026-09-28),
rebuilt node for node by `graphs.qwen21_edit` and exported to `workflows/qwen-image-2.1-edit-pe.api.json`.
Docs: docs/qwen-image-edit.md.

  python -m scripts.mvvm_gen.qwen_edit --scene PANEL.png --ref lune.png --ref rafa.png \\
      --prompt "Replace the woman in <image1> with Lune from <image2> ..." --out OUT.png [--seed N] [--no-pe]

Rules that make it work (do not change without the user):
  * the scene (the frame being edited) is always <image1> and is conformed to SIZE (1344x768) first: the encoder
    sizes the canvas from the first reference, so this fixes the output size and framing whatever the inputs are;
  * straight qwen_image_2.1_bf16, 40 steps, euler/simple, cfg 1, denoise 1.0; no LoRA (no turbo/Lightning), no
    masks, no img2img;
  * the EditPromptRewrite prompt enhancer on (Qwen 3.5 PE model), sampling 1.0 / 0.95 / 0 / 24000;
  * name every character as on their reference and state their outfit; never describe features they lack.

Writes OUT.png plus OUT.json (instruction, the enhancer's rewritten prompt, seed, refs, prompt id).
"""

import argparse
import json
import os
import subprocess
import sys
import time

from . import comfy, graphs

API_EXPORT = "workflows/qwen-image-2.1-edit-pe.api.json"
# The one output size. The encoder sizes the canvas from <image1> (the scene), and at resolution 1024 a 1344x768
# scene maps to exactly 1344x768, so conforming the scene here makes every edit the same size whatever the inputs.
SIZE = (1344, 768)


def conform(src, dest, size=SIZE):
    """Scale `src` to exactly `size` (lanczos, cover: a centre trim of at most a few percent for near-16:9 frames)."""
    w, h = size
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-vf",
                    f"scale={w}:{h}:force_original_aspect_ratio=increase:flags=lanczos,crop={w}:{h}", dest], check=True)
    return dest


def rewritten_prompt(record):
    """The enhancer's rewritten prompt, from the PreviewAny node in the history record."""
    for node_out in record.get("outputs", {}).values():
        for key in ("text", "string", "value"):
            items = node_out.get(key)
            if isinstance(items, list) and items and isinstance(items[0], str):
                return items[0]
    return None


def edit(scene, refs, instruction, out, seed=42, pe=True, resolution=1024, steps=40, canvas=None):
    """Run one edit on 7821 and write `out` (+ `out`.json). `scene` and `refs` are local image paths."""
    # canvas: a new image at that size; then `scene` is just the first reference (not conformed) or None.
    first = ([conform(scene, os.path.splitext(out)[0] + "-scene.png")] if not canvas else [scene] if scene else [])
    names = [comfy.upload_image(p) for p in [*first, *refs]]
    graph = graphs.qwen21_edit(instruction, names, seed, "mvvm/qwen-edit/" + os.path.splitext(os.path.basename(out))[0],
                               steps=steps, resolution=resolution, pe=pe, pe_seed=seed % 100000, canvas=canvas)
    started = time.monotonic()
    prompt_id = comfy.submit(graph)
    record = comfy.wait(prompt_id, timeout=1800)
    files = [f for f in comfy.output_files(record) if f["filename"].lower().endswith((".png", ".jpg", ".webp"))]
    if not files:
        raise comfy.ComfyError(f"qwen_edit: prompt {prompt_id} completed without an image")
    comfy.download(files[0], out)
    meta = {"scene": scene, "refs": refs, "instruction": instruction, "rewritten": rewritten_prompt(record),
            "seed": seed, "pe": pe, "prompt_id": prompt_id, "elapsed_s": round(time.monotonic() - started, 1),
            "workflow": API_EXPORT}
    with open(os.path.splitext(out)[0] + ".json", "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=1)
    return meta


def export_api(path=API_EXPORT):
    """Write the API-format graph with placeholder file names (scene.png, ref1.png, ref2.png)."""
    graph = graphs.qwen21_edit("Replace the woman in <image1> with the woman from <image2>, same face.",
                               ["scene.png", "ref1.png", "ref2.png"], 42, "qwen-edit")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(graph, fh, indent=1)
    return path


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scene", help="the frame to edit; becomes <image1> and sets the canvas")
    ap.add_argument("--ref", action="append", default=[], help="character reference, <image2>, <image3>, ...")
    ap.add_argument("--prompt", help="edit instruction using <image1>.. tags")
    ap.add_argument("--out")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--no-pe", action="store_true", help="skip the prompt enhancer")
    ap.add_argument("--export-api", action="store_true", help=f"write {API_EXPORT} and exit")
    args = ap.parse_args(argv)
    if args.export_api:
        print(export_api())
        return 0
    if not (args.scene and args.prompt and args.out):
        ap.error("--scene, --prompt and --out are required")
    meta = edit(args.scene, args.ref, args.prompt, args.out, seed=args.seed, pe=not args.no_pe)
    print(json.dumps(meta, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
