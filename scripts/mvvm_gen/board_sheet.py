"""Contact sheet of a storyboard's current state: each panel's best image in the user's 3x3 layout, labelled.

  python -m scripts.mvvm_gen.board_sheet board2   ->  .runtime/gen/i-ran-pilot/boards/fixed/<board>-sheet.png
Status per panel comes from STATUS below (edit as panels change) and finals.json (user-made frames).
"""

import json
import os
import subprocess
import sys

ROOT = ".runtime/gen/i-ran-pilot/boards"
FONT = r"C\:/Windows/Fonts/arialbd.ttf"
# panel -> (image in fixed/<board>/, label). The first existing image wins.
STATUS = {
    "board2": {
        "p11": (["p11-v4-s0.png", "p11-final.png"], "p11  queued"),
        "p12": (["p12-v4-s0.png", "p12-final.png"], "p12  queued"),
        "p13": (["p13-final.png"], "p13  FINAL (yours)"),
        "p21": (["p21-v4-s0.png", "p21-final.png"], "p21  hands: queued"),
        "p22": (["p22-final.png"], "p22  FINAL (yours) + alt"),
        "p23": (["p23-v4-s0.png", "p23-final.png"], "p23  mist fall: rendering"),
        "p31": (["p31-v4-s0.png"], "p31  candidate: pick take"),
        "p32": (["p32-v4-s0.png", "p32-final.png"], "p32  queued"),
        "p33": (["p33-v4-s0.png", "p33-final.png"], "p33  kiss: queued"),
    },
}


def tile(src, label, dest, w=640, h=366):
    text = label.replace(":", r"\:")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-vf",
                    f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},"
                    f"pad={w}:{h + 34}:0:0:black,"
                    f"drawtext=fontfile='{FONT}':text='{text}':x=10:y={h + 8}:fontsize=20:fontcolor=white",
                    dest], check=True)


def main(board):
    d = os.path.join(ROOT, "fixed", board)
    tiles = []
    for panel, (names, label) in STATUS[board].items():
        src = next((os.path.join(d, n) for n in names if os.path.exists(os.path.join(d, n))), None)
        if "v4" in os.path.basename(src or "") and "queued" in label or "rendering" in label and "v4" in (src or ""):
            label = label.split("  ")[0] + "  NEW: review"
        out = os.path.join(d, f"_tile-{panel}.png")
        tile(src, label, out)
        tiles.append(out)
    sheet = os.path.join(ROOT, "fixed", f"{board}-sheet.png")
    inputs = sum((["-i", t] for t in tiles), [])
    layout = "|".join(f"{c * 644}_{r * 404}" for r in range(3) for c in range(3))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex",
                    f"xstack=inputs=9:layout={layout}:fill=0x111111", sheet], check=True)
    for t in tiles:
        os.remove(t)
    print(sheet)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "board2")
