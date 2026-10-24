"""Upscale a panel to the canvas and build a soft mask over its faces (runs in ComfyUI's venv).

  D:\\ComfyUI_V89\\ComfyUI\\venv\\Scripts\\python.exe scripts/mvvm_gen/face_masks.py IN.png UP.png MASK.png W H

UP.png is IN.png resized (lanczos, cover-crop) to W x H; MASK.png is white over every detected face (box grown to take
in hair and headwear, feathered), black elsewhere. Prints FACES <n>. With no face, the mask is all black.
"""

import sys

import cv2
import numpy as np
from insightface.app import FaceAnalysis
from PIL import Image, ImageFilter, ImageOps


def main(src, up_path, mask_path, w, h):
    img = ImageOps.fit(Image.open(src).convert("RGB"), (w, h), Image.LANCZOS)
    img.save(up_path)
    app = FaceAnalysis(name="buffalo_l", providers=["CUDAExecutionProvider", "CPUExecutionProvider"])
    app.prepare(ctx_id=0, det_size=(640, 640))
    faces = app.get(cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR))
    mask = Image.new("L", (w, h), 0)
    px = np.zeros((h, w), np.uint8)
    for f in faces:
        x0, y0, x1, y1 = f.bbox
        cx, cy, bw, bh = (x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0
        # tight: the face itself (1.2x wide, 1.3x tall); hair, headwear, scarf and background stay the user's
        gx0, gx1 = int(max(0, cx - bw * 0.6)), int(min(w, cx + bw * 0.6))
        gy0, gy1 = int(max(0, cy - bh * 0.62)), int(min(h, cy + bh * 0.68))
        px[gy0:gy1, gx0:gx1] = 255
    mask = Image.fromarray(px).filter(ImageFilter.GaussianBlur(radius=max(4, w // 150)))
    mask.save(mask_path)
    print(f"FACES {len(faces)}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5]))
