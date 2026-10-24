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
        "p11": (["p11-v4-s0.png"], "p11  picked"),
        "p12": (["p12-v4-s1.png"], "p12  picked"),
        "p13": (["p13-final.png"], "p13  YOURS"),
        "p21": (["p21-adam-s1.png"], "p21  picked (hands)"),
        "p22": (["p22-final.png"], "p22  YOURS"),
        "p23": (["p23-P-s1.png"], "p23  picked (motion blur)"),
        "p31": (["p31-v4-s0.png"], "p31  picked"),
        "p32": (["p32-v4-s1.png"], "p32  picked"),
        "p33": (["p33-v4-s1.png"], "p33  picked"),
        "p11r": (["p11r-hair-s1.png"], "p11r  YOURS + hair fix (reverse of p11)"),
        "p22alt": (["p22-alt.png"], "p22 alt  YOURS"),
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
        out = os.path.join(d, f"_tile-{panel}.png")
        tile(src, label, out)
        tiles.append(out)
    sheet = os.path.join(ROOT, "fixed", f"{board}-sheet.png")
    inputs = sum((["-i", t] for t in tiles), [])
    # The user's 3x3 grid, then any added panels on extra rows.
    layout = "|".join(f"{(i % 3) * 644}_{(i // 3) * 404}" for i in range(len(tiles)))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex",
                    f"xstack=inputs={len(tiles)}:layout={layout}:fill=0x111111", sheet], check=True)
    for t in tiles:
        os.remove(t)
    print(sheet)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "board2")
