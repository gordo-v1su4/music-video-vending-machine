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
from urllib.parse import unquote

from . import review
from .run import Run

PORT = 5197
MAX_BODY = 64 * 1024


class ReviewApp:
    def __init__(self, plan_path):
        self.plan_path = plan_path
        self.lock = threading.Lock()

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

    def do_GET(self):
        if self.path == "/pilot-api/review":
            return self.send_json(200, self.app.payload())
        match = re.fullmatch(r"/pilot-api/media/([A-Za-z0-9_-]+\.mp4)", self.path)
        if match:
            return self.send_media(os.path.join(self.app.run().root, "clips", unquote(match.group(1))))
        self.send_json(404, {"error": "not found"})

    def do_POST(self):
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
