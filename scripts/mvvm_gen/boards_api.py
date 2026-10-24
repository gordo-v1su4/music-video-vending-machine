"""Storyboards and one-at-a-time image approval for the studio (served by review_server under /pilot-api).

A board is a grid the user made (boards/src/<board>.*) split into panels (boards/<board>/pRC.png), plus any
panels the pipeline or the user added (boards/fixed/finals.json: user-made frames, picked renders, parked shots).
Each panel's current image is, in order of preference: the grade-unified still (boards/unified/<board>-<panel>.png),
its final (finals.json), or the raw split panel.

Decisions live in review/image-decisions.json: {key: [{decision, note, at, image}]}, newest last. A decision
records the sha1 of the image it was made on; when the image changes (a redo, a new grade), the panel is back to
"to review" and the previous note stays visible. Per-panel "use as" (reference / first frame / first + last) lives
in review/board-settings.json. The clip batch (board_clips.py) renders only panels approved on their current image.
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import time

KEY = re.compile(r"^(board[0-9a-z]+)/(p[0-9]{2}[a-z]?|[ab][0-9]{2})$")
BOARD = re.compile(r"^board[0-9a-z]+$")
USE_AS = ("ref", "first", "firstlast")
DECISIONS = ("approve", "changes", "reset")
GRIDS = {"1x1": (1, 1), "2x2": (2, 2), "3x3": (3, 3), "2x3": (2, 3), "3x2": (3, 2)}
IMAGE_TYPES = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}


def _load(path, default):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


def _save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + ".part", "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1)
    os.replace(path + ".part", path)


def _sha1(path):
    h = hashlib.sha1()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _order(board):
    """board1 < board2 < board2b < ... < board9 < board10 (numeric, then suffix)."""
    m = re.match(r"board(\d+)(.*)", board)
    return (int(m.group(1)), m.group(2)) if m else (10 ** 6, board)


class Boards:
    def __init__(self, root):
        self.root = root  # .runtime/gen/<plan>
        self.dir = os.path.join(root, "boards")
        self.decisions_path = os.path.join(root, "review", "image-decisions.json")
        self.settings_path = os.path.join(root, "review", "board-settings.json")

    # ---- paths -------------------------------------------------------------------------------------------------
    def finals(self):
        return _load(os.path.join(self.dir, "fixed", "finals.json"), {})

    def source_grid(self, board):
        for ext in (".webp", ".png", ".jpg", "-a.png"):
            path = os.path.join(self.dir, "src", board + ext)
            if os.path.exists(path):
                return path
        return None

    def split_panel(self, board, panel):
        path = os.path.join(self.dir, board, panel + ".png")
        return path if os.path.exists(path) else None

    def image(self, key):
        """The panel's current image (what gets approved), or None."""
        board, panel = key.split("/")
        unified = os.path.join(self.dir, "unified", f"{board}-{panel}.png")
        if os.path.exists(unified):
            return unified
        final = self.finals().get(key, {}).get("final")
        if final and os.path.exists(final):
            return final
        return self.split_panel(board, panel)

    def source(self, key):
        board, panel = key.split("/")
        return self.split_panel(board, panel) or self.finals().get(key, {}).get("final")

    # ---- listing -----------------------------------------------------------------------------------------------
    def keys(self):
        keys = set(k for k in self.finals() if KEY.match(k))
        if os.path.isdir(self.dir):
            for board in os.listdir(self.dir):
                folder = os.path.join(self.dir, board)
                if BOARD.match(board) and os.path.isdir(folder):
                    keys.update(f"{board}/{f[:-4]}" for f in os.listdir(folder)
                                if re.fullmatch(r"p[0-9]{2}\.png", f))
        return sorted(keys, key=lambda k: (_order(k.split("/")[0]), k.split("/")[1]))

    def status(self, key, image, decisions):
        history = decisions.get(key, [])
        last = history[-1] if history else None
        current = _sha1(image) if image else None
        if last and last["decision"] != "reset" and last.get("image") == current:
            return ("approved" if last["decision"] == "approve" else "changes"), last
        if last and last["decision"] != "reset":
            return "review", {**last, "stale": True}  # the image changed since this note
        return "review", None

    def placements(self):
        """key -> song ms, from the clip plan (board_clips.CLIPS) and the studio's edit plan."""
        try:
            from .board_clips import CLIPS
        except Exception:  # noqa: BLE001 - the listing must work without the render stack
            return {}
        chunks = {c["index"]: c for c in _load(os.path.join(self.root, "edit-plan.json"), {}).get("chunks", [])}
        return {key: chunks[ci]["startMs"] for key, ci, *_ in CLIPS if ci in chunks}

    def payload(self):
        finals, decisions = self.finals(), _load(self.decisions_path, {})
        settings, placed = _load(self.settings_path, {}), self.placements()
        boards = {}
        for key in self.keys():
            board, panel = key.split("/")
            image = self.image(key)
            if not image:
                continue
            state, last = self.status(key, image, decisions)
            fin = finals.get(key, {})
            origin = ("yours" if fin.get("source", "").startswith("user-made") else
                      "generated" if fin.get("source", "").startswith("generated") else
                      "graded" if "unified" in image else "panel")
            v = int(os.path.getmtime(image))
            boards.setdefault(board, []).append({
                "key": key, "board": board, "panel": panel, "status": "parked" if fin.get("parked") else state,
                "parked": fin.get("parked"), "note": (last or {}).get("note", ""), "noteStale": bool((last or {}).get("stale")),
                "decidedAt": (last or {}).get("at"), "origin": origin,
                "useAs": settings.get(key, {}).get("useAs", "first" if key in placed else "ref"),
                "songMs": placed.get(key), "url": f"/pilot-api/board-image/{key}?v={v}",
                "sourceUrl": f"/pilot-api/board-image/{key}/source" if self.source(key) else None,
            })
        out = []
        for board in sorted(boards, key=_order):
            out.append({"id": board, "sourceUrl": f"/pilot-api/board-source/{board}" if self.source_grid(board) else None,
                        "panels": boards[board]})
        panels = [p for b in out for p in b["panels"]]
        return {"boards": out, "counts": {s: sum(p["status"] == s for p in panels)
                                          for s in ("review", "changes", "approved", "parked")}}

    def approved_keys(self):
        """Keys approved on their current image (the clip batch renders only these)."""
        decisions = _load(self.decisions_path, {})
        return {k for k in self.keys() if (img := self.image(k)) and self.status(k, img, decisions)[0] == "approved"}

    # ---- actions -----------------------------------------------------------------------------------------------
    def decide(self, key, decision, note):
        if not KEY.match(key):
            raise LookupError(f"unknown panel {key}")
        if decision not in DECISIONS:
            raise ValueError("decision must be approve, changes or reset")
        image = self.image(key)
        if not image:
            raise LookupError(f"{key} has no image yet")
        note = str(note or "")[:4000].strip()
        if decision == "changes" and not note:
            raise ValueError("Say what should change.")
        decisions = _load(self.decisions_path, {})
        decisions.setdefault(key, []).append({"decision": decision, "note": note, "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                                              "image": _sha1(image)})
        _save(self.decisions_path, decisions)
        return self.panel(key)

    def use_as(self, key, value):
        if not KEY.match(key):
            raise LookupError(f"unknown panel {key}")
        if value not in USE_AS:
            raise ValueError("use as must be ref, first or firstlast")
        settings = _load(self.settings_path, {})
        settings.setdefault(key, {})["useAs"] = value
        _save(self.settings_path, settings)
        return self.panel(key)

    def panel(self, key):
        for b in self.payload()["boards"]:
            for p in b["panels"]:
                if p["key"] == key:
                    return p
        raise LookupError(f"unknown panel {key}")

    def upload(self, name, grid, content_type, data):
        """Save an uploaded image or grid as a new board and split it into equal panels (pRC.png)."""
        board = "board" + re.sub(r"[^0-9a-z]+", "", name.lower().removeprefix("board"))
        if not BOARD.match(board) or board == "board":
            raise ValueError("Name the board with letters or numbers, e.g. 10 or 10b.")
        if grid not in GRIDS:
            raise ValueError(f"grid must be one of {', '.join(GRIDS)}")
        ext = IMAGE_TYPES.get(content_type)
        if not ext:
            raise ValueError("Upload a PNG, JPEG or WebP image.")
        if self.source_grid(board) or os.path.isdir(os.path.join(self.dir, board)):
            raise ValueError(f"{board} already exists; pick another name.")
        src = os.path.join(self.dir, "src", board + ext)
        os.makedirs(os.path.dirname(src), exist_ok=True)
        with open(src, "wb") as fh:
            fh.write(data)
        rows, cols = GRIDS[grid]
        size = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                               "-of", "csv=p=0", src], capture_output=True, text=True)
        try:
            w, h = (int(x) for x in size.stdout.strip().split(","))
        except ValueError:
            os.remove(src)
            raise ValueError("That file could not be read as an image.")
        out = os.path.join(self.dir, board)
        os.makedirs(out, exist_ok=True)
        pw, ph = w // cols, h // rows
        for r in range(rows):
            for c in range(cols):
                dest = os.path.join(out, f"p{r + 1}{c + 1}.png")
                subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-vf",
                                f"crop={pw}:{ph}:{c * pw}:{r * ph}", dest], check=True)
        if grid == "1x1":
            shutil.copy2(os.path.join(out, "p11.png"), os.path.join(out, "p11.png"))
        return {"board": board, "panels": rows * cols, **self.payload()}
