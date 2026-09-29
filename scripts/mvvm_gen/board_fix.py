"""Put the characters back into the user's storyboard panels, exactly, at production resolution.

Each panel (boards.py output) goes through one Qwen Image 2.1 edit at the plan frame size: <image1> is the panel,
whose composition, camera, pose, action, light, colour grade and background are kept; the following images are the
ground-truth faces (Lune: her identity image; Rafa: the user's close-up), unlabeled so no text is painted in. The
edit re-renders at 1344x768, so it upscales at the same time. Each fixed panel is face-checked against the right
identity image (face_check.py in ComfyUI's venv).

Usage (repo root): python -m scripts.mvvm_gen.board_fix scripts/mvvm_gen/plans/i-ran-pilot.json board2
"""

import argparse
import json
import os
import subprocess
import sys

from . import graphs, qwen_edit
from .run import Run, seed_for

COMFY_PY = r"D:\ComfyUI_V89\ComfyUI\venv\Scripts\python.exe"
# The masters: each character's named sheet close-up (user, 2026-09-28: "that's the master one"). Scores use the
# same close-up without the caption band.
IDENTITY = {"lune": ".runtime/gen/i-ran-pilot/sheets/lune/closeup.png",
            "rafa": ".runtime/gen/i-ran-pilot/sheets/rafa/closeup.png"}

# panel -> characters on screen (who needs putting back); empty = no faces, upscale only.
CAST = {
    "board2": {"p11": ["lune", "rafa"], "p12": ["lune"], "p13": ["rafa"], "p21": [], "p22": ["lune", "rafa"],
               "p23": ["lune"], "p31": ["lune"], "p32": ["lune"], "p33": ["lune", "rafa"]},
}


# Edit mode: the locked Qwen 2.1 edit call (qwen_edit.py, docs/qwen-image-edit.md). Instructions are SHORT, in the
# user's own format ("Replace the woman in <image2> with young woman from <image1>, same face"): the Benji prompt
# enhancer rewrites them into the precise directive, and its system prompt says identity must be pointed at a
# reference image, never described in words (descriptions degrade the likeness). {L}/{R} expand to Lune's/Rafa's
# reference tags; the scene is always <image1>. A panel can be several steps; each step edits the previous output.
# Low-res storyboard panels: upscale first, because output quality follows input quality (research doc).
UPSCALE = ("Keep colors exactly the same, upscale the image.", [], False)
PUT = ("Put the {who} from {tag} into the scene of <image1>, in the same position and pose as the {who} there{extra}. "
       "Match the exact lighting and environment of <image1>{env}.")


def put(cid, extra="", env=""):
    """The compositing formula (docs/qwen-image-edit.md, formula C): one character per pass."""
    who = "woman" if cid == "lune" else "man"
    if cid == "lune":
        # The enhancer reads "freckled skin" off her master and transfers it; the user wants none (say it positively).
        extra = ", with smooth clear skin" + extra
    return (PUT.format(who=who, tag="{L}" if cid == "lune" else "{R}", extra=extra, env=env), [cid], True)


EDITS = {
    "board2": {
        "p21": [UPSCALE, ("Fix both hands so each has a natural thumb and four fingers, the index fingertips almost "
                          "touching.", [], False)],
        "p22": [UPSCALE, put("rafa", ", leaping from the snapping rope bridge", ", with motion blur on the flying debris"),
                put("lune", ", reaching up for his hand", "")],
        "p23": [("Remove all the people from the image, leaving only the smoke and mist.", [], False), UPSCALE,
                ("Put the woman from {L} into the scene of <image1>, falling back first through the mist, her body flat "
                 "and parallel to the camera, lower in the frame and sinking into the clouds, face up, with smooth clear skin and motion blur "
                 "from the fall. Match the exact lighting and environment of <image1>.", ["lune"], False)],
        "p31": [UPSCALE, put("lune", ", with her eyes closed", ", with bubbles drifting in front of her face")],
        "p33": [UPSCALE, put("rafa", ", not smiling", ""), put("lune", "", "")],
        "p11": [UPSCALE, put("rafa", ", running toward her across the rope bridge", ""),
                put("lune", ", seen from behind in the foreground", "")],
        "p12": [UPSCALE, put("lune", ", reaching her hand toward the camera", "")],
        "p32": [UPSCALE, put("lune", ", sinking through the water as a dark silhouette with her arms raised",
                             ", with bubbles rising around her")],
    },
}

# Character references: the close-up carries the face, the full-body sheet panel the outfit.
EDIT_REFS = {"lune": [".runtime/gen/i-ran-pilot/sheets/lune/closeup-named.png"],
             "rafa": [".runtime/gen/i-ran-pilot/sheets/rafa/closeup-named.png"]}


def step_refs(run, cast):
    """Reference paths after the scene, and each character's tag text (<image2> and <image3>, ...)."""
    paths, tags, n = [], {}, 1
    for cid in cast:
        own = [p if p.endswith(".png") else run.panel(cid, p) for p in EDIT_REFS[cid]]
        tags[cid] = " and ".join(f"<image{n + i + 1}>" for i in range(len(own)))
        n += len(own)
        paths += own
    return paths, tags


def edit_main(run, args):
    """Each panel's steps through qwen_edit.edit (the locked call); the last step's image is the take."""
    report = {}
    finals_path = run.path("boards", "fixed", "finals.json")
    user_finals = {k: v for k, v in (json.load(open(finals_path, encoding="utf-8")) if os.path.exists(finals_path)
                                      else {}).items() if v.get("source", "").startswith("user-made")}
    for board in args.boards:
        src_dir, out_dir = run.path("boards", board), run.path("boards", "fixed", board)
        os.makedirs(out_dir, exist_ok=True)
        for panel, steps in EDITS[board].items():
            if args.panels and panel not in args.panels:
                continue
            if f"{board}/{panel}" in user_finals:
                print(f"[boardedit] {board}/{panel}: the user made this one ({user_finals[f'{board}/{panel}']['source']}); "
                      "skipped", flush=True)
                continue
            original = qwen_edit.conform(os.path.join(src_dir, f"{panel}.png"), os.path.join(out_dir, f"{panel}-scene.png"))
            for k in range(args.seeds):
                seed = seed_for(run.name, "boardedit", board, panel, args.tag, str(k))
                scene, entry = original, {"steps": []}
                for i, (template, cast, measure) in enumerate(steps):
                    refs, tags = step_refs(run, cast)
                    instruction = template.format(lune=run.full_name("lune"), rafa=run.full_name("rafa"),
                                                  L=tags.get("lune", ""), R=tags.get("rafa", ""))
                    last = i == len(steps) - 1
                    # Plate steps (clean-up, upscale) before the first character step are shared by every take.
                    shared = not last and all(not st[1] for st in steps[:i + 1])
                    dest = os.path.join(out_dir, f"{panel}-{args.tag}-step{i + 1}.png" if shared else
                                        f"{panel}-{args.tag}-s{k}.png" if last else
                                        f"{panel}-{args.tag}-s{k}-step{i + 1}.png")
                    step_seed = seed_for(run.name, "boardedit", board, panel, args.tag, "plate", str(i)) if shared else seed + i
                    if not os.path.exists(dest):
                        print(f"[boardedit] {board}/{panel} s{k} step {i + 1}: {instruction}", flush=True)
                        meta = qwen_edit.edit(scene, refs, instruction, dest, seed=step_seed, pe=not args.no_pe)
                        print(f"[boardedit]   enhanced: {meta.get('rewritten')}", flush=True)
                    entry["steps"].append({"instruction": instruction, "out": dest})
                    if measure:
                        entry["geometry"] = geometry(original, dest)
                    scene = dest
                entry["identity"] = {c: face(IDENTITY[c], scene) for c in steps[-1][1]}
                report[f"{board}/{panel}/{args.tag}/s{k}"] = entry
                print(f"[boardedit] {board}/{panel} s{k} identity {entry['identity']} proportions "
                      f"{entry.get('geometry', 'n/a (new placement)')}", flush=True)
    path = run.path("boards", "fixed", "edit-report.json")
    old = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}
    old.update(report)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(old, fh, indent=1)
    return 0


def edit_prompt(run, cast):
    keep = ("<image1> is a film frame: keep its exact composition, framing, camera angle, lens, pose, gesture, action, "
            "expression, lighting, colour grade, atmosphere, background and props. Re-render it as a sharp, clean, "
            "high-resolution cinematic film still with natural skin texture, correct anatomy and no blur or artifacts.")
    if not cast:
        return keep + " Change nothing else."
    parts = []
    for i, cid in enumerate(cast, start=2):
        char = run.plan["characters"][cid]
        who = "the woman" if cid == "lune" else "the man"
        parts.append(f"{who} in <image1> is {run.full_name(cid)}: give {who} exactly the face, bone structure, eyes, "
                     f"skin tone and hair of the person in <image{i}> ({char['identity']}); outfit: {char['look']}")
    return keep + " " + " ".join(parts) + " Keep each person's pose and expression from <image1>; no text, no labels."


def mask_prompt(run, cast):
    """Masked mode: the scene is already in the unmasked pixels, so the only references are the true faces."""
    parts = []
    for i, cid in enumerate(cast, start=1):
        char = run.plan["characters"][cid]
        who = "the woman" if cid == "lune" else "the man"
        parts.append(f"<image{i}> is {run.full_name(cid)} ({char['identity']}). Paint {who}'s face in this film frame as "
                     f"exactly {run.full_name(cid)}'s face from <image{i}>: same bone structure, eyes, nose, mouth, brows, "
                     f"skin tone and hair.")
    return (" ".join(parts) + " Keep the head angle, expression, lighting, wet skin, colour grade and focus of the frame; "
            "keep the exact expression and emotion of the face already in the frame (open mouth, strain, fear or longing "
            "as shown), and blend seamlessly with the surrounding image. Cinematic film still, natural skin texture, no text.")


def geometry(scene, result):
    """Face proportions vs the user's frame (both at the same size): for each scene face, the matching result face's
    size ratio (result/scene box height) and centre shift as a fraction of frame width. Flags > 8% off."""
    code = ("import sys, cv2\nfrom insightface.app import FaceAnalysis\n"
            "app = FaceAnalysis(name='buffalo_l', providers=['CUDAExecutionProvider','CPUExecutionProvider'])\n"
            "app.prepare(ctx_id=0, det_size=(640, 640))\n"
            "def boxes(p):\n    im = cv2.resize(cv2.imread(p), (1344, 768))\n"
            "    return [[float(v) for v in f.bbox] for f in app.get(im)]\n"
            "print('BOXES', repr(boxes(sys.argv[1])), '|', repr(boxes(sys.argv[2])))\n")
    out = subprocess.run([COMFY_PY, "-c", code, scene, result], capture_output=True, text=True).stdout
    line = next((l for l in out.splitlines() if l.startswith("BOXES")), None)
    if not line:
        return {"ok": False, "error": "no detection"}
    a, b = (eval(x) for x in line[6:].split("|"))
    faces = []
    for x0, y0, x1, y1 in a:
        cx, cy, hh = (x0 + x1) / 2, (y0 + y1) / 2, y1 - y0
        if not b:
            faces.append({"missing": True})
            continue
        m = min(b, key=lambda r: ((r[0] + r[2]) / 2 - cx) ** 2 + ((r[1] + r[3]) / 2 - cy) ** 2)
        faces.append({"size": round((m[3] - m[1]) / hh, 3),
                      "shift": round((((m[0] + m[2]) / 2 - cx) ** 2 + ((m[1] + m[3]) / 2 - cy) ** 2) ** 0.5 / 1344, 3)})
    ok = bool(faces) and all(not f.get("missing") and abs(f["size"] - 1) <= 0.08 and f["shift"] <= 0.04 for f in faces)
    return {"ok": ok, "faces": faces}


def face(ref, image):
    code = ("import sys, cv2, numpy as np\nfrom insightface.app import FaceAnalysis\n"
            "app = FaceAnalysis(name='buffalo_l', providers=['CUDAExecutionProvider','CPUExecutionProvider'])\n"
            "app.prepare(ctx_id=0, det_size=(640, 640))\n"
            "def e(p):\n    f = app.get(cv2.imread(p))\n    return [x.normed_embedding for x in f]\n"
            "r = e(sys.argv[1])[0]\nprint('SCORE', max([float(np.dot(r, x)) for x in e(sys.argv[2])] or [-1]))\n")
    out = subprocess.run([COMFY_PY, "-c", code, ref, image], capture_output=True, text=True).stdout
    line = next((l for l in out.splitlines() if l.startswith("SCORE")), "SCORE -1")
    return round(float(line.split()[1]), 3)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("boards", nargs="+")
    ap.add_argument("--denoise", type=float, nargs="+", default=[0.6],
                    help="how much of the panel is re-rendered (lower keeps more of the user's frame)")
    ap.add_argument("--panels", nargs="*", default=None, help="only these panels, e.g. p11 p12")
    ap.add_argument("--mode", choices=("edit", "mask", "img2img"), default="edit",
                    help="edit: the user's Qwen 2.1 edit workflow (recommended); mask: faces only; img2img: whole frame")
    ap.add_argument("--seeds", type=int, default=2, help="edit mode: takes per panel")
    ap.add_argument("--no-pe", action="store_true", help="edit mode: skip the prompt-rewrite (enhancer) node")
    ap.add_argument("--tag", default="edit3", help="edit mode: output name tag (a new tag re-renders)")
    args = ap.parse_args(argv)
    run = Run(args.plan)
    if args.mode == "edit":
        return edit_main(run, args)
    w, h = run.plan["frame_size"]
    ids = {cid: run.upload(path) for cid, path in IDENTITY.items()}
    report = {}
    for board in args.boards:
        src_dir = run.path("boards", board)
        out_dir = run.path("boards", "fixed", board)
        os.makedirs(out_dir, exist_ok=True)
        for panel, cast in CAST[board].items():
            if args.panels and panel not in args.panels:
                continue
            src = run.upload(os.path.join(src_dir, f"{panel}.png"))
            mask = None
            if args.mode == "mask":
                up = os.path.join(out_dir, f"{panel}-up.png")
                mask_path = os.path.join(out_dir, f"{panel}-mask.png")
                out = subprocess.run([COMFY_PY, "scripts/mvvm_gen/face_masks.py", os.path.join(src_dir, f"{panel}.png"),
                                      up, mask_path, str(w), str(h)], capture_output=True, text=True).stdout
                n = int(next((l.split()[1] for l in out.splitlines() if l.startswith("FACES")), "0"))
                print(f"[boardfix] {board}/{panel}: {n} face(s) masked", flush=True)
                src = run.upload(up)
                mask = run.upload(mask_path) if n and cast else None
                if mask is None:
                    # No face to fix (hands, tiny figures): keep the clean upscale, never re-render the whole frame.
                    import shutil
                    shutil.copy2(up, os.path.join(out_dir, f"{panel}-final.png"))
                    report[f"{board}/{panel}"] = {"cast": cast, "faces": n, "kept": "upscale"}
                    print(f"[boardfix] {board}/{panel}: no face to fix, kept the upscale", flush=True)
                    continue
            refs = ([ids[c] for c in cast] if mask else [src] + [ids[c] for c in cast])
            seed = seed_for(run.name, "boardfix", board, panel)
            before = {c: face(IDENTITY[c], os.path.join(src_dir, f"{panel}.png")) for c in cast}
            for den in args.denoise:
                # Start from the user's panel (image-to-image) so framing, pose and light are kept.
                graph = graphs.qwen21_image(mask_prompt(run, cast) if mask else edit_prompt(run, cast), refs, w, h, seed,
                                            f"mvvm/{run.name}/boardfix-{board}-{panel}-d{int(den * 100)}",
                                            unet=run.plan.get("keyframe_unet"), init_image=src, denoise=den,
                                            mask_image=mask)
                dest = os.path.join(out_dir, f"{panel}-{args.mode}{'ref' if mask else ''}-d{int(den * 100)}.png")
                run.generate(f"boardfix:{board}:{panel}:{args.mode}{'ref' if mask else ''}:d{int(den * 100)}", graph, dest, seed)
                scores = {c: face(IDENTITY[c], dest) for c in cast}
                report[f"{board}/{panel}/d{int(den * 100)}"] = {"cast": cast, "before": before, "after": scores}
                if len(args.denoise) == 1:
                    import shutil
                    shutil.copy2(dest, os.path.join(out_dir, f"{panel}-final.png"))
                print(f"[boardfix] {board}/{panel} d{den} cast {cast} face before {before} after {scores}", flush=True)
    with open(run.path("boards", "fixed", "report.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
