# /// script
# requires-python = ">=3.12"
# dependencies = ["boto3==1.43.103"]
# ///
"""Live RustFS acceptance probe. Credentials are injected by agent-secrets."""
import argparse
import hashlib
import json
import os
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--create-bucket", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    endpoint = "https://s3.v1su4.dev"
    bucket = "music-vending-machine"
    client = boto3.client(
        "s3", endpoint_url=endpoint, region_name="us-east-1",
        aws_access_key_id=os.environ["PROXMOX_HOME_RUSTFS_ACCESS_KEY"],
        aws_secret_access_key=os.environ["PROXMOX_HOME_RUSTFS_SECRET_KEY"],
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"},
                      connect_timeout=10, read_timeout=30, retries={"max_attempts": 0},
                      request_checksum_calculation="when_required",
                      response_checksum_validation="when_required"),
    )
    created = False
    try:
        client.head_bucket(Bucket=bucket)
    except ClientError as error:
        if error.response["ResponseMetadata"]["HTTPStatusCode"] != 404 or not args.create_bucket:
            raise
        client.create_bucket(Bucket=bucket)
        created = True
    # No bucket policy is added: private access is required. The concrete object
    # is checked anonymously below, independently of authenticated readback.
    payload = os.urandom(1024 * 1024)
    digest = hashlib.sha256(payload).hexdigest()
    key = f"capability-probes/{uuid.uuid4()}/roundtrip.bin"
    started = time.monotonic()
    client.put_object(Bucket=bucket, Key=key, Body=payload, ContentType="application/octet-stream",
                      Metadata={"sha256": digest, "purpose": "mvm-storage-acceptance"})
    receipt = client.get_object(Bucket=bucket, Key=key)
    with receipt["Body"] as body:
        returned = body.read()
    if len(returned) != len(payload) or hashlib.sha256(returned).hexdigest() != digest:
        raise ValueError("Storage length/checksum mismatch")
    ranged = client.get_object(Bucket=bucket, Key=key, Range="bytes=64-127")
    with ranged["Body"] as body:
        if body.read() != payload[64:128]:
            raise ValueError("Storage range mismatch")
    try:
        with urllib.request.urlopen(f"{endpoint}/{bucket}/{key}", timeout=15) as response:
            anonymous = response.status
    except urllib.error.HTTPError as error:
        anonymous = error.code
    if anonymous != 403:
        raise ValueError(f"Expected private object denial, got HTTP {anonymous}")
    result = {
        "gate": "rustfs-roundtrip", "status": "passed",
        "checkedAt": datetime.now(timezone.utc).isoformat(), "endpoint": endpoint,
        "bucket": bucket, "createdBucket": created, "key": key,
        "bytes": len(payload), "sha256": digest, "rangeVerified": True,
        "anonymousHttpStatus": anonymous, "elapsedSeconds": round(time.monotonic() - started, 3),
        "sdk": f"boto3/{boto3.__version__}",
        "scope": "S3 service acceptance; coordinator live-adapter and scoped writer tests remain separate",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    try:
        main()
    except ClientError as error:
        # Never print a request, authorization header or credential value.
        print(json.dumps({"status": "failed", "code": error.response["Error"]["Code"]}))
        raise SystemExit(1)
    except (BotoCoreError, urllib.error.URLError, ValueError, KeyError) as error:
        print(json.dumps({"status": "failed", "kind": type(error).__name__}))
        raise SystemExit(1)
