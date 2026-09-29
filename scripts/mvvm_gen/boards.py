"""Split 3x3 storyboard grids into panels (runs in ComfyUI's venv, which has PIL + numpy).

  D:\\ComfyUI_V89\\ComfyUI\\venv\\Scripts\\python.exe scripts/mvvm_gen/boards.py <src_dir> <out_dir>

Finds the dark gutters between panels near the 1/3 and 2/3 lines (falls back to exact thirds for seamless grids),
trims them, and writes out_dir/board<N>/p<row><col>.png plus a panels.json index.
"""

import json
import os
import sys

import numpy as np
from PIL import Image


def cuts(profile, size, n=3, dark=18):
    """Panel bounds along one axis: the dark run nearest each 1/n line, else the exact line."""
    bounds, start = [], 0
    for k in range(1, n):
        target = size * k // n
        lo, hi = max(0, target - size // 12), min(size, target + size // 12)
        dark_idx = [i for i in range(lo, hi) if profile[i] < dark]
        if dark_idx:
            # the contiguous run closest to the target
            runs, run = [], [dark_idx[0]]
            for i in dark_idx[1:]:
                if i == run[-1] + 1:
                    run.append(i)
                else:
                    runs.append(run)
                    run = [i]
            runs.append(run)
            best = min(runs, key=lambda r: abs((r[0] + r[-1]) / 2 - target))
            bounds.append((start, best[0]))
            start = best[-1] + 1
        else:
            bounds.append((start, target))
            start = target
    bounds.append((start, size))
    return bounds


def split(path, out_dir):
    img = Image.open(path).convert("RGB")
    a = np.asarray(img).astype(np.float32).mean(axis=2)
    cols = cuts(a.mean(axis=0), a.shape[1])
    rows = cuts(a.mean(axis=1), a.shape[0])
    os.makedirs(out_dir, exist_ok=True)
    panels = []
    for r, (y0, y1) in enumerate(rows):
        for c, (x0, x1) in enumerate(cols):
            name = f"p{r + 1}{c + 1}.png"
            img.crop((x0, y0, x1, y1)).save(os.path.join(out_dir, name))
            panels.append({"panel": name, "box": [x0, y0, x1, y1], "size": [x1 - x0, y1 - y0]})
    return panels


def main(src, out):
    index = {}
    for name in sorted(os.listdir(src)):
        if name.lower().endswith((".webp", ".png", ".jpg", ".jpeg")):
            board = os.path.splitext(name)[0]
            index[board] = split(os.path.join(src, name), os.path.join(out, board))
            sizes = sorted({tuple(p["size"]) for p in index[board]})
            print(f"{board}: {len(index[board])} panels, sizes {sizes}", flush=True)
    with open(os.path.join(out, "panels.json"), "w", encoding="utf-8") as fh:
        json.dump(index, fh, indent=1)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
