# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Submit one synthetic musical fixture to the existing Essentia service.

Inject ESSENTIA_API_KEY through agent-secrets. The receipt is exclusive before
POST and retained on uncertain outcomes. Inspect never resubmits the audio.
"""
import argparse
import array
import hashlib
import json
import math
import os
import sys
import urllib.error
import urllib.request
import uuid
import wave
from datetime import datetime, timezone
from pathlib import Path

ENDPOINT = "http://100.118.78.13:18000"  # Existing app-vm, encrypted Tailscale route.


def save(path, record, exclusive=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    target = path if exclusive else path.with_suffix(".tmp")
    with target.open("x" if exclusive else "w", encoding="utf-8") as output:
        json.dump(record, output, indent=2)
        output.write("\n")
        output.flush()
        os.fsync(output.fileno())
    if not exclusive:
        target.replace(path)


def fixture(path):
    rate = 22050
    samples = array.array("h")
    # 48 seconds, 120 BPM with chord changes every 8 seconds and three energy
    # levels. This is synthetic service evidence, not real-song music quality.
    chords = [(130.8128, 164.8138, 195.9977), (110.0, 130.8128, 164.8138),
              (87.3071, 110.0, 130.8128), (97.9989, 123.4708, 146.8324)]
    for index in range(rate * 48):
        t = index / rate
        beat_time = t % 0.5
        kick = 0.52 * math.exp(-beat_time * 45) * math.sin(2 * math.pi * 65 * beat_time)
        chord = chords[int(t // 8) % 4]
        amplitude = (0.06, 0.10, 0.15)[int(t // 16)]
        tone = sum(math.sin(2 * math.pi * frequency * t) for frequency in chord) * amplitude
        samples.append(round(max(-1, min(1, kick + tone)) * 32767))
    if sys.byteorder != "little":
        samples.byteswap()
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(samples.tobytes())
    return path.read_bytes()


def request(route, data=None, headers=None):
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None
    # Do not forward the API key through a redirect or environment proxy.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    req = urllib.request.Request(ENDPOINT + route, data=data,
                                headers={"X-API-Key": os.environ["ESSENTIA_API_KEY"], **(headers or {})})
    with opener.open(req, timeout=45) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["start", "inspect"])
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--audio", type=Path)
    args = parser.parse_args()
    if args.action == "start":
        if not args.audio:
            parser.error("start requires --audio for the generated synthetic fixture")
        if args.receipt.exists() or args.audio.exists():
            parser.error("Refusing to overwrite an existing receipt or fixture")
        audio = fixture(args.audio)
        record = {"endpoint": ENDPOINT, "state": "submission_intent", "providerId": None,
                  "idempotencyKey": f"mvm-feasibility-{uuid.uuid4()}",
                  "startedAt": datetime.now(timezone.utc).isoformat(),
                  "masterSha256": hashlib.sha256(audio).hexdigest(), "fixtureDurationSeconds": 48,
                  "fixtureBpm": 120, "audioBytes": len(audio)}
        save(args.receipt, record, exclusive=True)
        boundary = "mvm" + uuid.uuid4().hex
        data = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="synthetic.wav"\r\n'
                'Content-Type: audio/wav\r\n\r\n').encode() + audio + f"\r\n--{boundary}--\r\n".encode()
        try:
            response = request("/analyze/studio/jobs", data, {
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "Idempotency-Key": record["idempotencyKey"]})
            record.update(providerId=response["id"], state=response["status"], response=response)
        except urllib.error.HTTPError as error:
            record.update(state="reconciliation_required", errorKind="HTTPError", httpStatus=error.code)
        except (OSError, ValueError, KeyError) as error:
            record.update(state="reconciliation_required", errorKind=type(error).__name__)
        save(args.receipt, record)
    else:
        record = json.loads(args.receipt.read_text(encoding="utf-8"))
        if record["endpoint"] != ENDPOINT or not record.get("providerId"):
            parser.error("No verified provider receipt; reconciliation is required, never blind resubmission")
        provider_id = uuid.UUID(record["providerId"]).hex
        response = request(f"/analyze/studio/jobs/{provider_id}")
        record.update(state=response["status"], response=response,
                      inspectedAt=datetime.now(timezone.utc).isoformat())
        save(args.receipt, record)
    print(json.dumps({key: record.get(key) for key in ("state", "providerId", "masterSha256")}))
    if record["state"] in ("queued", "running"):
        # A successful start acknowledges submission; inspection has not passed.
        if args.action == "inspect":
            raise SystemExit(2)
    elif record["state"] != "completed" or not (
        isinstance(record.get("response", {}).get("result"), dict)
        and record["response"]["result"]
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
