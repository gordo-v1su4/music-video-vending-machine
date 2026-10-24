"""Local API for the side-by-side take review page (apps/web route /pilot-review).

Usage (from the repository root):
  uv run --python 3.12 python -m scripts.mvvm_gen.review_server scripts/mvvm_gen/plans/i-ran-pilot.json

Serves on 127.0.0.1:5197 under /pilot-api; the web dev server proxies that prefix. Decisions are
written to .runtime/gen/<plan>/review/decisions.json and read back by `run check` and `run cut`.
"""

import argparse
import json
import os
import re
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

from . import review, timing
from .boards_api import Boards
from .production_api import MAX_BODY as MAX_PRODUCTION_BODY, ProductionAPI
from .run import Run

PORT = 5197
MAX_BODY = 64 * 1024
MAX_PLAN_BODY = 8 * 1024 * 1024
MAX_UPLOAD = 40 * 1024 * 1024
IMAGE_MIME = {".png": "image/png", ".webp": "image/webp", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}


class ReviewApp:
    def __init__(self, plan_path):
        self.plan_path = plan_path
        self.lock = threading.Lock()
        self.production = ProductionAPI(self.run)

    def run(self):
        return Run(self.plan_path)  # Re-read per request so new renders and plan edits show up.

    def clip_ids(self, run, sid, takes):
        return {str(t): run.manifest.get(run.take_key(sid, t), {}).get("prompt_id") for t in takes}

    def shot_payload(self, run, store, shot):
        sid = shot["id"]
        seeds = run.plan.get("seeds_per_prompt", 1)
        setups = [{"label": "Main", "framing": shot.get("framing", ""), "camera": shot.get("camera", "")}]
        setups += [{"label": f"Alt {chr(65 + i)}", "framing": alt.get("framing", shot.get("framing", "")),
                    "camera": alt.get("camera", shot.get("camera", ""))} for i, alt in enumerate(shot.get("alts", []))]
        takes = run.takes(shot)
        current = self.clip_ids(run, sid, takes)
        decisions = store.decisions(sid)
        stale = any(str(t) in d.get("clips", {}) and d["clips"][str(t)] != current.get(str(t))
                    for d in decisions for t in (d["a"], d["b"]) if t is not None)
        try:
            state = review.bracket(takes, decisions, seeds)
        except ValueError:
            state, stale = None, True
        chars = run.plan.get("characters", {})
        return {
            "id": sid, "summary": shot.get("summary", ""), "bars": shot.get("bars"),
            "location": shot.get("location"), "characters": [chars.get(c, {}).get("name", c) for c in shot.get("characters", [])],
            "setups": setups,
            "takes": [{"take": t, "setup": min(t // seeds, len(setups) - 1), "seed": t % seeds,
                       "url": f"/pilot-api/media/{os.path.basename(run.take_path(sid, t))}",
                       "gpu_s": run.manifest.get(run.take_key(sid, t), {}).get("gpu_s")} for t in takes],
            "decisions": decisions, "state": state, "stale": stale, "planPick": shot.get("pick"),
        }

    def payload(self):
        run = self.run()
        store = review.Store(run.root)
        return {"plan": run.name, "seedsPerPrompt": run.plan.get("seeds_per_prompt", 1),
                "shots": [self.shot_payload(run, store, s) for s in run.plan["shots"]]}

    def cut_payload(self, run=None):
        """The assembled pilot cut: where it sits in the song, each shot's span, and whether picks changed since."""
        run = run or self.run()
        cut = run.manifest.get("cut")
        path = run.path("cut", f"{run.name}.mp4")
        if not cut or not os.path.exists(path):
            return {"exists": False, "plan": run.name}
        start_ms = cut["start_s"] * 1000
        shots, at = [], start_ms
        summaries = {s["id"]: s.get("summary", "") for s in run.plan["shots"]}
        if cut.get("segments"):
            # Assembled from picked takes plus spliced chunk renders: one entry per segment on the song.
            for seg in cut["segments"]:
                label = seg["label"]
                sid, _, take = label.partition(" t")
                pick = next((run.pick(s)[0] for s in run.plan["shots"] if s["id"] == sid), None)
                shots.append({"id": sid, "summary": summaries.get(sid, f"New chunk render {sid}"), "startMs": seg["startMs"],
                              "endMs": seg["endMs"], "take": int(take) if take else None,
                              "pickNow": pick if take else None, "source": "reviewed" if take else "spliced"})
        for shot, count in ([] if cut.get("segments") else zip(run.plan["shots"], run.shot_frames())):
            end = at + count * 1000 / timing.FPS
            take, source = run.pick(shot)
            shots.append({"id": shot["id"], "summary": shot.get("summary", ""), "startMs": round(at), "endMs": round(end),
                          "take": cut.get("picks", {}).get(shot["id"], take), "pickNow": take, "source": source})
            at = end
        return {"exists": True, "plan": run.name, "url": f"/pilot-api/cut.mp4?v={int(os.path.getmtime(path))}",
                "songStartMs": round(start_ms), "durationMs": round(cut["duration_s"] * 1000),
                "builtAt": cut.get("built_at"), "shots": shots,
                "stale": any(s["take"] != s["pickNow"] for s in shots)}

    def save_edit_plan(self, body):
        """The studio's music-driven edit plan (chunks, stutters, impacts, builds) for prompt writing."""
        if not isinstance(body.get("chunks"), list) or not body["chunks"]:
            raise ValueError("edit plan has no chunks")
        run = self.run()
        path = run.path("edit-plan.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with self.lock:
            with open(path + ".part", "w", encoding="utf-8") as fh:
                json.dump(body, fh, indent=1)
            os.replace(path + ".part", path)
        return {"saved": path, "chunks": len(body["chunks"])}

    def boards(self):
        return Boards(self.run().root)

    def build_cut(self):
        with self.lock:
            run = self.run()
            run.cut()
            return self.cut_payload(Run(self.plan_path))

    def shot(self, run, sid):
        for s in run.plan["shots"]:
            if s["id"] == sid:
                return s
        raise LookupError(f"unknown shot {sid}")

    def act(self, sid, action, body):
        with self.lock:
            run = self.run()
            store = review.Store(run.root)
            shot = self.shot(run, sid)
            takes = run.takes(shot)
            if action == "decide":
                a, b = body.get("a"), body.get("b")
                comment = str(body.get("comment", ""))[:4000]
                store.decide(sid, takes, run.plan.get("seeds_per_prompt", 1), a, b, body.get("choice"), comment,
                             {k: v for k, v in self.clip_ids(run, sid, takes).items() if k in (str(a), str(b))})
            elif action == "undo":
                store.set_decisions(sid, store.decisions(sid)[:-1])
            elif action == "redo":
                setup = body.get("setup")
                if not isinstance(setup, int):
                    raise ValueError("redo needs a setup number")
                store.redo(sid, run.plan.get("seeds_per_prompt", 1), setup)
            elif action == "reset":
                store.set_decisions(sid, [])
            else:
                raise LookupError(f"unknown action {action}")
            return self.shot_payload(run, store, shot)


class Handler(BaseHTTPRequestHandler):
    app = None

    def log_message(self, fmt, *args):
        if not self.path.startswith("/pilot-api/media/"):
            sys.stderr.write("[review] " + fmt % args + "\n")

    def send_json(self, status, obj):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def production(self, result):
        """Send a ProductionAPI result: (status, json) | ("file", image path) | ("media", video path)."""
        kind, value = result
        if kind == "file":
            return self.send_image(value)
        if kind == "media":
            return self.send_media(value)
        return self.send_json(kind, value)

    def do_GET(self):
        path = urlparse(self.path).path
        if path.startswith("/pilot-api/production"):
            try:
                result = self.app.production.get(path)
            except LookupError as exc:
                return self.send_json(404, {"error": str(exc)})
            return self.production(result) if result else self.send_json(404, {"error": "not found"})
        if path == "/pilot-api/review":
            return self.send_json(200, self.app.payload())
        if path == "/pilot-api/cut":
            return self.send_json(200, self.app.cut_payload())
        if path == "/pilot-api/cut.mp4":
            run = self.app.run()
            return self.send_media(run.path("cut", f"{run.name}.mp4"))
        match = re.fullmatch(r"/pilot-api/media/([A-Za-z0-9_-]+\.mp4)", path)
        if match:
            return self.send_media(os.path.join(self.app.run().root, "clips", unquote(match.group(1))))
        if path == "/pilot-api/boards":
            return self.send_json(200, self.app.boards().payload())
        match = re.fullmatch(r"/pilot-api/board-image/(board[0-9a-z]+)/([a-z0-9]+)(/source)?", path)
        if match:
            boards, key = self.app.boards(), f"{match.group(1)}/{match.group(2)}"
            return self.send_image(boards.source(key) if match.group(3) else boards.image(key))
        match = re.fullmatch(r"/pilot-api/board-source/(board[0-9a-z]+)", path)
        if match:
            return self.send_image(self.app.boards().source_grid(match.group(1)))
        self.send_json(404, {"error": "not found"})

    def send_image(self, path):
        if not path or not os.path.isfile(path):
            return self.send_json(404, {"error": "image not found"})
        with open(path, "rb") as fh:
            data = fh.read()
        self.send_response(200)
        self.send_header("Content-Type", IMAGE_MIME.get(os.path.splitext(path)[1].lower(), "application/octet-stream"))
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        if self.path.startswith("/pilot-api/production/"):
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_PRODUCTION_BODY:
                return self.send_json(413, {"error": "request too large"})
            try:
                body = json.loads(self.rfile.read(length) or b"{}")
            except ValueError:
                return self.send_json(400, {"error": "invalid JSON"})
            with self.app.lock:
                result = self.app.production.post(self.path, body)
            return self.production(result) if result else self.send_json(404, {"error": "not found"})
        if self.path == "/pilot-api/edit-plan":
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_PLAN_BODY:
                return self.send_json(413, {"error": "edit plan too large"})
            try:
                return self.send_json(200, self.app.save_edit_plan(json.loads(self.rfile.read(length) or b"{}")))
            except (ValueError, TypeError) as exc:
                return self.send_json(400, {"error": str(exc)})
        if self.path == "/pilot-api/cut/build":
            try:
                return self.send_json(200, self.app.build_cut())
            except Exception as exc:  # ffmpeg or missing clips: report, keep serving
                return self.send_json(500, {"error": f"Cut failed: {exc}"})
        if self.path.startswith("/pilot-api/boards/upload"):
            return self.upload()
        match = re.fullmatch(r"/pilot-api/(images|boards)/(board[0-9a-z]+)/([a-z0-9]+)/(decide|use-as)", self.path)
        if match:
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY:
                return self.send_json(413, {"error": "request too large"})
            try:
                body = json.loads(self.rfile.read(length) or b"{}")
                boards, key = self.app.boards(), f"{match.group(2)}/{match.group(3)}"
                with self.app.lock:
                    if match.group(4) == "decide":
                        return self.send_json(200, boards.decide(key, body.get("decision"), body.get("note")))
                    return self.send_json(200, boards.use_as(key, body.get("useAs")))
            except LookupError as exc:
                return self.send_json(404, {"error": str(exc)})
            except (ValueError, TypeError) as exc:
                return self.send_json(409, {"error": str(exc)})
        match = re.fullmatch(r"/pilot-api/review/([A-Za-z0-9_-]+)/(decide|undo|redo|reset)", self.path)
        if not match:
            return self.send_json(404, {"error": "not found"})
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            return self.send_json(413, {"error": "request too large"})
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
            return self.send_json(200, self.app.act(match.group(1), match.group(2), body))
        except LookupError as exc:
            return self.send_json(404, {"error": str(exc)})
        except (ValueError, TypeError) as exc:
            return self.send_json(409, {"error": str(exc)})

    def upload(self):
        """POST /pilot-api/boards/upload?name=10&grid=3x3 with the image as the raw body."""
        from urllib.parse import parse_qs
        query = parse_qs(urlparse(self.path).query)
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return self.send_json(400, {"error": "No image received."})
        if length > MAX_UPLOAD:
            return self.send_json(413, {"error": "Images up to 40 MB."})
        data = self.rfile.read(length)
        try:
            with self.app.lock:
                out = self.app.boards().upload(query.get("name", [""])[0], query.get("grid", ["3x3"])[0],
                                               (self.headers.get("Content-Type") or "").split(";")[0].strip(), data)
            return self.send_json(200, out)
        except (ValueError, OSError) as exc:
            return self.send_json(409, {"error": str(exc)})

    def send_media(self, path):
        if not os.path.isfile(path):
            return self.send_json(404, {"error": "clip not rendered"})
        size = os.path.getsize(path)
        start, end = 0, size - 1
        ranged = re.fullmatch(r"bytes=(\d*)-(\d*)", self.headers.get("Range", ""))
        if ranged and (ranged.group(1) or ranged.group(2)):
            if ranged.group(1):
                start = int(ranged.group(1))
                end = min(int(ranged.group(2)), size - 1) if ranged.group(2) else size - 1
            else:
                start = max(0, size - int(ranged.group(2)))
            if start > end:
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{size}")
                self.end_headers()
                return
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        else:
            self.send_response(200)
        self.send_header("Content-Type", "video/mp4")
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(end - start + 1))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        with open(path, "rb") as fh:
            fh.seek(start)
            left = end - start + 1
            try:
                while left > 0:
                    chunk = fh.read(min(1 << 20, left))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    left -= len(chunk)
            except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError):
                pass  # The browser cancels ranges while seeking.


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("plan")
    parser.add_argument("--port", type=int, default=PORT)
    args = parser.parse_args(argv)
    Handler.app = ReviewApp(args.plan)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"[review] {Handler.app.run().name} on http://127.0.0.1:{args.port}/pilot-api/review "
          f"(open the web app at /pilot-review)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
