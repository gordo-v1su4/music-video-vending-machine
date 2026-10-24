"""Identity check: how much a render's face looks like the character's identity reference (ArcFace cosine).

Runs in ComfyUI's venv (it has insightface + the buffalo_l models):
  D:\\ComfyUI_V89\\ComfyUI\\venv\\Scripts\\python.exe scripts/mvvm_gen/face_check.py REF.png VIDEO.mp4 [VIDEO.mp4 ...]

Samples a frame every 0.25 s, takes the largest detected face, and prints the median similarity per video and
per shot (split at scene cuts). Same person is typically >= 0.45; below ~0.30 reads as someone else.
Output: one JSON line per video.
"""

import json
import subprocess
import sys

import cv2
import numpy as np
from insightface.app import FaceAnalysis

STEP_S = 0.25


def embed(app, image):
    faces = app.get(image)
    if not faces:
        return None
    face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
    return face.normed_embedding


def cuts(path):
    out = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-vf", "select='gt(scene,0.12)',showinfo", "-an",
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    import re
    return [float(t) for t in re.findall(r"pts_time:([0-9.]+)", out)]


def score(app, ref, path):
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    samples = []
    for frame_no in range(0, total, max(1, int(round(fps * STEP_S)))):
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
        ok, frame = cap.read()
        if not ok:
            break
        e = embed(app, frame)
        samples.append((frame_no / fps, None if e is None else float(np.dot(ref, e))))
    cap.release()
    bounds = [0.0, *cuts(path), total / fps + 1]
    shots = []
    for a, b in zip(bounds, bounds[1:]):
        sims = [s for t, s in samples if a <= t < b and s is not None]
        shots.append({"from_s": round(a, 2), "faces": len(sims), "median": round(float(np.median(sims)), 3) if sims else None})
    sims = [s for _, s in samples if s is not None]
    return {"video": path, "frames_with_face": len(sims), "median": round(float(np.median(sims)), 3) if sims else None,
            "worst": round(min(sims), 3) if sims else None, "shots": shots}


def main(argv):
    app = FaceAnalysis(name="buffalo_l", providers=["CUDAExecutionProvider", "CPUExecutionProvider"])
    app.prepare(ctx_id=0, det_size=(640, 640))
    ref_img = cv2.imread(argv[0])
    ref = embed(app, ref_img)
    if ref is None:
        raise SystemExit(f"no face found in reference {argv[0]}")
    for path in argv[1:]:
        print(json.dumps(score(app, ref, path)), flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
