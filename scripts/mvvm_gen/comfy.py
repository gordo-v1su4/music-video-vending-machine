"""Minimal client for the SwarmUI-managed ComfyUI backend (default 127.0.0.1:7821).

Standard library only. Submits API-format graphs, waits on /history and downloads
outputs. The backend is owned by SwarmUI; this client never starts or stops it.
"""

import hashlib
import json
import mimetypes
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

BASE = os.environ.get("MVVM_COMFY_URL", "http://127.0.0.1:7821").rstrip("/")
SWARM = os.environ.get("MVVM_SWARM_URL", "http://127.0.0.1:7861").rstrip("/")
CLIENT_ID = f"mvvm-gen-{uuid.uuid4().hex[:8]}"


class ComfyError(RuntimeError):
    pass


def _request(url, data=None, headers=None, timeout=60):
    req = urllib.request.Request(url, data=data, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return res.read()
    except urllib.error.HTTPError as err:
        raise ComfyError(f"{url}: HTTP {err.code}: {err.read()[:2000].decode(errors='replace')}") from err


def get_json(route):
    return json.loads(_request(BASE + route))


def preflight():
    """Confirm SwarmUI and its managed backend on 7821 are live before submitting.

    Only 7821 is used. If SwarmUI has relaunched its backend elsewhere (it takes the next
    free port, e.g. 7822, after a crash), stop and restart SwarmUI with its own launcher
    (D:\\SwarmUI\\Windows_Start_SwarmUI.bat or the "SwarmUI Persistent" task); never follow it.
    """
    try:
        _request(SWARM + "/", timeout=10)
    except Exception as err:  # noqa: BLE001 - report any reachability failure
        raise ComfyError(f"SwarmUI is not reachable at {SWARM}; start it with its own launcher") from err
    try:
        stats = get_json("/system_stats")
    except Exception as err:  # noqa: BLE001 - report any reachability failure
        raise ComfyError(f"Swarm-managed ComfyUI is not on {BASE}; restart SwarmUI so its backend returns to 7821") from err
    return {"backend": BASE, "comfyui": stats["system"]["comfyui_version"],
            "devices": [d["name"] for d in stats.get("devices", [])]}


def upload_image(path):
    """Upload a local image once, named by content hash so repeats are idempotent."""
    with open(path, "rb") as fh:
        body = fh.read()
    ext = os.path.splitext(path)[1].lower() or ".png"
    name = f"mvvm-{hashlib.sha256(body).hexdigest()[:16]}{ext}"
    boundary = uuid.uuid4().hex
    ctype = mimetypes.guess_type(name)[0] or "application/octet-stream"
    parts = []
    for field, value in (("subfolder", "mvvm"), ("overwrite", "true"), ("type", "input")):
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"\r\n\r\n{value}\r\n'.encode())
    parts.append(
        f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="{name}"\r\n'
        f"Content-Type: {ctype}\r\n\r\n".encode() + body + b"\r\n"
    )
    parts.append(f"--{boundary}--\r\n".encode())
    res = json.loads(_request(BASE + "/upload/image", b"".join(parts), {"Content-Type": f"multipart/form-data; boundary={boundary}"}, timeout=300))
    return f"{res['subfolder']}/{res['name']}" if res.get("subfolder") else res["name"]


def submit(graph):
    payload = json.dumps({"prompt": graph, "client_id": CLIENT_ID}).encode()
    res = json.loads(_request(BASE + "/prompt", payload, {"Content-Type": "application/json"}))
    if res.get("node_errors"):
        raise ComfyError(f"node errors: {json.dumps(res['node_errors'])[:2000]}")
    return res["prompt_id"]


def wait(prompt_id, timeout=3600, poll=3.0):
    """Block until the prompt finishes; return its history record or raise."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        hist = get_json(f"/history/{prompt_id}")
        record = hist.get(prompt_id)
        if record:
            status = record.get("status", {})
            if status.get("status_str") == "error" or (status.get("completed") is False and status.get("messages")):
                msgs = [m for m in status.get("messages", []) if m[0] == "execution_error"]
                if msgs or status.get("status_str") == "error":
                    raise ComfyError(f"prompt {prompt_id} failed: {json.dumps(msgs)[:2000]}")
            if status.get("completed", True):
                return record
        time.sleep(poll)
    raise ComfyError(f"prompt {prompt_id} did not finish within {timeout}s")


def output_files(record):
    """Every saved (type=output) file in a history record, in node order."""
    files = []
    for node_out in record.get("outputs", {}).values():
        for items in node_out.values():
            if isinstance(items, list):
                files.extend(i for i in items if isinstance(i, dict) and "filename" in i and i.get("type") == "output")
    return files


def download(file_info, dest):
    query = urllib.parse.urlencode({k: file_info.get(k, "") for k in ("filename", "subfolder", "type")})
    data = _request(f"{BASE}/view?{query}", timeout=600)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = dest + ".part"
    with open(tmp, "wb") as fh:
        fh.write(data)
    os.replace(tmp, dest)
    return dest
