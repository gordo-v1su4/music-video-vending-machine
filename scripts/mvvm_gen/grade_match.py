"""Match an image's colour grade to a reference (Reinhard transfer in Lab: per-channel mean and spread).

Upscaled panels keep their detail but drift (the Qwen 2.1 upscale came out 10-20% darker). This puts the
original panel's brightness, contrast and colour balance back on the upscale. Runs in ComfyUI's venv (OpenCV):

  D:\\ComfyUI_V89\\ComfyUI\\venv\\Scripts\\python.exe scripts/mvvm_gen/grade_match.py RESULT.png REFERENCE.png OUT.png
"""

import sys

import cv2
import numpy as np


def match(result, reference):
    res = cv2.cvtColor(result, cv2.COLOR_BGR2LAB).astype(np.float32)
    ref = cv2.cvtColor(reference, cv2.COLOR_BGR2LAB).astype(np.float32)
    for ch in range(3):
        r_mean, r_std = res[..., ch].mean(), res[..., ch].std() + 1e-6
        t_mean, t_std = ref[..., ch].mean(), ref[..., ch].std()
        res[..., ch] = (res[..., ch] - r_mean) * (t_std / r_std) + t_mean
    return cv2.cvtColor(np.clip(res, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR)


def lab_stats(images):
    """Mean and spread per Lab channel over a set of images (the target look)."""
    px = np.concatenate([cv2.cvtColor(i, cv2.COLOR_BGR2LAB).reshape(-1, 3).astype(np.float32) for i in images])
    return px.mean(0), px.std(0)


def toward(img, mean, std, strength, green):
    """Move img's Lab statistics `strength` of the way to (mean, std), then shift a* by -green (more green)."""
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32)
    out = lab.copy()
    for ch in range(3):
        m, s = lab[..., ch].mean(), lab[..., ch].std() + 1e-6
        # Colour spread (a*, b*) may only shrink toward the target, never grow: growing it pumped saturation
        # (red hair, hot skin) on cool shots. Lightness contrast matches both ways.
        scale = std[ch] / s if ch == 0 else min(1.0, std[ch] / s)
        full = (lab[..., ch] - m) * scale + mean[ch]
        out[..., ch] = lab[..., ch] * (1 - strength) + full * strength
    out[..., 1] -= green
    return cv2.cvtColor(np.clip(out, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR)


def unify(jobs_path):
    """One look for the film. JOBS.json: {"target": [reference images], "strength": 0.6, "green": 3, "size": [w, h],
    "items": [{"in": path, "out": path, "source": optional original panel to restore first (for upscales)}]}"""
    import json
    jobs = json.load(open(jobs_path, encoding="utf-8"))
    mean, std = lab_stats([cv2.imread(p) for p in jobs["target"]])
    w, h = jobs.get("size", [1344, 768])
    for item in jobs["items"]:
        img = cv2.imread(item["in"])
        if item.get("source"):
            img = match(img, cv2.imread(item["source"]))
        img = cv2.resize(img, (w, h), interpolation=cv2.INTER_LANCZOS4) if img.shape[:2] != (h, w) else img
        cv2.imwrite(item["out"], toward(img, mean, std, jobs.get("strength", 0.6), jobs.get("green", 3.0)))
        print(f"UNIFIED {item['out']}", flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "unify":
        unify(sys.argv[2])
        sys.exit(0)
    result, reference, out = sys.argv[1:4]
    img = match(cv2.imread(result), cv2.imread(reference))
    cv2.imwrite(out, img)
    a, b = cv2.imread(reference).reshape(-1, 3).mean(0), img.reshape(-1, 3).mean(0)
    print(f"GRADE reference {np.round(a, 1)} matched {np.round(b, 1)}", flush=True)
