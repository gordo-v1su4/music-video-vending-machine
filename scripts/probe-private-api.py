# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Exercise a separately launched private coordinator on loopback port 5201.

Inject MVM_OPERATOR_TOKEN. Run start once, restart the coordinator, then verify
with the same receipt. Uses only synthetic media and an acceptance project.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
import os
from pathlib import Path
import urllib.error
import urllib.request
import wave
from datetime import datetime, timezone

ENDPOINT = "http://127.0.0.1:5201"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def request(method, path, payload=None, *, authenticated=True, headers=None):
    headers = dict(headers or {})
    if authenticated:
        headers["Authorization"] = "Bearer " + os.environ["MVM_OPERATOR_TOKEN"]
    if isinstance(payload, dict):
        headers["Content-Type"] = "application/json"
        payload = json.dumps(payload).encode()
    req = urllib.request.Request(ENDPOINT + path, data=payload, method=method, headers=headers)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    try:
        with opener.open(req, timeout=45) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


def expect(status, response):
    actual, data = response
    if actual != status:
        raise ValueError(f"Expected HTTP {status}, received {actual}")
    return data


def save(path, record, exclusive=False):
    target = path if exclusive else path.with_suffix(path.suffix + ".tmp")
    with target.open("x" if exclusive else "w", encoding="utf-8") as output:
        json.dump(record, output, indent=2)
        output.write("\n")
        output.flush()
        os.fsync(output.fileno())
    if not exclusive:
        target.replace(path)


def fixture():
    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(8000)
        wav.writeframes(b"\x00\x00" * 8000)
    return output.getvalue()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["start", "verify"])
    parser.add_argument("--receipt", required=True, type=Path)
    args = parser.parse_args()
    expect(401, request("GET", "/api/v1/projects", authenticated=False))
    expect(403, request("POST", "/api/v1/projects", {"name": "Must not exist"}, headers={"Origin": "http://untrusted.invalid"}))
    health = json.loads(expect(200, request("GET", "/api/v1/health")))
    if health.get("storage") != "rustfs" or health.get("development") is not False:
        raise ValueError("Acceptance coordinator must use authenticated non-development RustFS mode")
    if args.action == "start":
        record = {"state": "started", "endpoint": ENDPOINT, "startedAt": datetime.now(timezone.utc).isoformat()}
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        save(args.receipt, record, exclusive=True)
        project = json.loads(expect(201, request("POST", "/api/v1/projects", {"name": "Private storage acceptance fixture"})))
        record["projectId"] = project["id"]
        save(args.receipt, record)
        path = f'/api/v1/projects/{project["id"]}'
        audio = fixture()
        body = b'--mvm-acceptance\r\nContent-Disposition: form-data; name="file"; filename="silence-fixture.wav"\r\nContent-Type: audio/wav\r\n\r\n' + audio + b'\r\n--mvm-acceptance--\r\n'
        asset = json.loads(expect(201, request("POST", path + "/assets", body, headers={"Content-Type": "multipart/form-data; boundary=mvm-acceptance"})))
        record.update(assetId=asset["id"], assetUrl=asset["url"], sha256=hashlib.sha256(audio).hexdigest())
        save(args.receipt, record)
        if record["sha256"] != asset["sha256"]:
            raise ValueError("Upload checksum mismatch")
        def action(value):
            return request("POST", path + "/actions", {"expectedRevision": 0, "action": {"type": "setTreatment", "text": value}})
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(action, ["Synthetic treatment A", "Synthetic treatment B"]))
        if sorted(result[0] for result in results) != [200, 409]:
            raise ValueError("Concurrent writes did not preserve revision conflict")
        record["project"] = json.loads(expect(200, request("GET", path)))
        record.update(state="ready_for_restart", simultaneousWrites=[200, 409], unauthorizedHttpStatus=401, untrustedOriginHttpStatus=403)
    else:
        record = json.loads(args.receipt.read_text(encoding="utf-8"))
        if record.get("endpoint") != ENDPOINT or record.get("state") != "ready_for_restart":
            raise ValueError("Expected the retained receipt from the initial acceptance run")
        project = json.loads(expect(200, request("GET", f'/api/v1/projects/{record["projectId"]}')))
        if project != record["project"]:
            raise ValueError("Project changed across restart")
        record.update(state="verified_after_operator_restart", verifiedAt=datetime.now(timezone.utc).isoformat())
    data = expect(200, request("GET", record["assetUrl"]))
    if hashlib.sha256(data).hexdigest() != record["sha256"]:
        raise ValueError("Authenticated download checksum mismatch")
    record["downloadChecksumVerified"] = True
    save(args.receipt, record)
    print(json.dumps({key: record[key] for key in ("state", "projectId", "assetId", "sha256")}))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(json.dumps({"state": "failed", "errorKind": type(error).__name__,
                          "reason": str(error) if isinstance(error, ValueError) else "See retained receipt; no automatic resubmission"}))
        raise SystemExit(1)
