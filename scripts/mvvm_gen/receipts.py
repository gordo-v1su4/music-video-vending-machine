"""Read-only render receipt collector for visible Swarm Generate runs (V1S-228).

Polls the managed ComfyUI queue/history (GET only; never submits) and writes, per prompt id:
  <out>/<prompt_id>/submitted.json   exact graph as queued (first time it is seen)
  <out>/<prompt_id>/history.json     history entry once complete (status, timings, outputs)
  <out>/<prompt_id>/gpu.jsonl        nvidia-smi memory/utilisation samples while it runs
Re-running after an interruption resumes from what is on disk: a prompt id already complete is skipped,
so reconnecting never duplicates or resubmits a render.

  uv run --python 3.12 python -m mvvm_gen.receipts <out_dir> [--minutes 90] [--comfy http://127.0.0.1:7821]

If the collector stopped before a job finished (no history.json), `reconcile` closes the gap offline: jobs run
one at a time, so each receipt's GPU sampling window ends just before exactly one output file is written. A
pairing is only accepted when that is unambiguous and the output's embedded Swarm parameters agree with the
submitted graph (audio seek); otherwise the run is recorded as uncertain, never guessed.

  uv run --python 3.12 python -m mvvm_gen.receipts --reconcile <renders_dir> <plan_root>
"""

import argparse
import json
import os
import re
import subprocess
import time
import urllib.request


def get(url):
    with urllib.request.urlopen(url, timeout=20) as r:
        return json.load(r)


def gpu():
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used,utilization.gpu", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=10).stdout.split(",")
        return {"t": round(time.time(), 1), "mem_mib": int(out[0]), "util": int(out[1])}
    except (OSError, ValueError, IndexError, subprocess.SubprocessError):
        return None


def save(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + ".part", "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=1)
    os.replace(path + ".part", path)


def collect(out, comfy, minutes, idle_exit=180):
    deadline, idle_since = time.time() + minutes * 60, None
    while time.time() < deadline:
        q = get(f"{comfy}/queue")
        active = q["queue_running"] + q["queue_pending"]
        for item in active:
            pid = item[1]
            path = os.path.join(out, pid, "submitted.json")
            if not os.path.exists(path):
                save(path, {"prompt_id": pid, "seen_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "number": item[0],
                            "prompt": item[2], "extra": item[3] if len(item) > 3 else None})
                print("seen", pid, flush=True)
        for item in q["queue_running"]:
            sample = gpu()
            if sample:
                with open(os.path.join(out, item[1], "gpu.jsonl"), "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(sample) + "\n")
        for pid in os.listdir(out) if os.path.isdir(out) else []:
            hist_path = os.path.join(out, pid, "history.json")
            if os.path.exists(os.path.join(out, pid, "submitted.json")) and not os.path.exists(hist_path):
                h = get(f"{comfy}/history/{pid}")
                if pid in h and h[pid].get("status", {}).get("completed") is not None:
                    save(hist_path, h[pid])
                    print("done", pid, h[pid]["status"].get("status_str"), flush=True)
        idle_since = None if active else (idle_since or time.time())
        if idle_since and time.time() - idle_since > idle_exit:
            print("queue idle; exiting", flush=True)
            return
        time.sleep(10)


def swarm_params(path):
    """The sui_image_params Swarm embeds in an output's container comment."""
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format_tags=comment", "-of", "json", path],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(json.loads(out)["format"]["tags"]["comment"])["sui_image_params"]


def mechanical(path):
    """Decode check plus detected black and frozen spans (seconds). Says nothing about content quality."""
    res = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-vf", "blackdetect=d=0.3:pix_th=0.08,freezedetect=n=0.003:d=0.8",
                          "-an", "-f", "null", "-"], capture_output=True, text=True)
    log = res.stderr
    black = [[float(a), float(b)] for a, b in re.findall(r"black_start:([0-9.]+) black_end:([0-9.]+)", log)]
    starts = [float(x) for x in re.findall(r"freeze_start: ([0-9.]+)", log)]
    ends = [float(x) for x in re.findall(r"freeze_end: ([0-9.]+)", log)]
    return {"decoded": res.returncode == 0, "black_spans": black, "freeze_spans": [list(p) for p in zip(starts, ends)]}


def reconcile(renders, plan_root, slack_s=60):
    from .production import Production, _read, _write, probe
    prod = Production(plan_root)
    packet = prod.packet()
    slots = packet["sequence"]["clips"]
    receipts = os.path.join(renders, "receipts")
    outputs = {f: os.path.getmtime(os.path.join(renders, f)) for f in os.listdir(renders) if f.endswith(".mp4")}
    attribution = _read(os.path.join(prod.dir, "private", "attribution.json"), {})
    runs_path = os.path.join(prod.dir, "runs.json")
    runs = {r["prompt_id"]: r for r in _read(runs_path, [])}
    for pid in sorted(os.listdir(receipts)):
        rdir = os.path.join(receipts, pid)
        submitted = _read(os.path.join(rdir, "submitted.json"), None)
        if submitted is None:
            continue
        samples = []
        if os.path.exists(os.path.join(rdir, "gpu.jsonl")):
            with open(os.path.join(rdir, "gpu.jsonl"), encoding="utf-8") as fh:
                samples = [json.loads(line) for line in fh if line.strip()]
        run = {"prompt_id": pid, "queued_at": submitted["seen_at"], "status": "uncertain", "label": pid[:8], "slot": "?",
               "preset": "", "gpu_peak_mib": max((s["mem_mib"] for s in samples), default=None)}
        hist = _read(os.path.join(rdir, "history.json"), None)
        if hist and hist.get("status", {}).get("status_str") == "error":
            # Interrupted or failed in the backend: no output exists, so nothing to pair. Recorded, never retried here.
            msgs = [m[0] for m in hist["status"].get("messages", [])]
            run.update(status="failed", reconciled="history: " + ("interrupted" if "execution_interrupted" in msgs else "error"))
            runs[pid] = run
            continue
        if samples:
            end = samples[-1]["t"]
            near = [f for f, m in outputs.items() if 0 <= m - end <= slack_s]
            run["seconds"] = round(end - samples[0]["t"] + 10, 1)  # samples are 10 s apart
            if len(near) == 1:
                f = near[0]
                params = swarm_params(os.path.join(renders, f))
                seek = float(params.get("comfyrawworkflowinputdecimalvhsloadaudionodeseeksecondseb", -1))
                graph = json.dumps(submitted["prompt"])
                if f"{seek}" in graph or f"{seek:.3f}" in graph:
                    label = f.rsplit("_", 1)[0]
                    slot = "C0+C1" if label.startswith("trial-") else next((c["slot"] for c in slots if abs(c["song_s"][0] - seek) < 0.05), "?")
                    cond = None
                    if label.startswith("trial-"):
                        cond = {(False, False): "no guide", (False, True): "guide B f120", (True, True): "guides A f62 + B f120"}.get(
                            (bool(params.get("useguidea")), bool(params.get("useguideb"))), "other")
                    clip = prod.add_clip(os.path.join(renders, f), "generated", label=label,
                                         lineage={"prompt_id": pid, "seed": params.get("comfyrawworkflowinputseedseedrgthreenodeseedch"),
                                                  "song_seek_s": seek, "workflow": params.get("comfyuicustomworkflow"),
                                                  "refmod": params.get("rafacharacterrefmod"), "condition": cond,
                                                  "packet_revision": attribution.get(label, {}).get("packet_revision")})
                    run.update(status="complete", label=label, slot=slot, output=clip["path"], clip_id=clip["id"], condition=cond,
                               preset=label, checks=dict(mechanical(clip["path"]), frames=clip["media"]["frames"], audio=clip["media"]["audio"]),
                               reconciled="gpu-window/output-mtime pairing, audio seek verified" if not hist else "history")
        runs[pid] = run
    _write(runs_path, sorted(runs.values(), key=lambda r: r["queued_at"]))
    return list(runs.values())


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out")
    ap.add_argument("plan_root", nargs="?")
    ap.add_argument("--reconcile", action="store_true")
    ap.add_argument("--minutes", type=float, default=90)
    ap.add_argument("--comfy", default="http://127.0.0.1:7821")
    a = ap.parse_args()
    if a.reconcile:
        for r in reconcile(a.out, a.plan_root):
            print(r["prompt_id"][:8], r["status"], r["label"], r["slot"], r.get("condition"), r.get("checks"))
    else:
        collect(a.out, a.comfy, a.minutes)
