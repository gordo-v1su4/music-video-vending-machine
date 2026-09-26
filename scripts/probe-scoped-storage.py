# /// script
# requires-python = ">=3.12"
# dependencies = ["boto3==1.43.103"]
# ///
"""Verify the dedicated application's RustFS permissions, without root credentials.

Inject MVM_S3_ACCESS_KEY and MVM_S3_SECRET_KEY with agent-secrets. Retains the
successful fixture. Negative mutations target only new disposable probe keys.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    endpoint = "https://s3.v1su4.dev"
    bucket = "music-vending-machine"
    key = f"projects/{uuid.uuid4()}/permission-probe.bin"
    payload = os.urandom(65536)
    record = {"state": "started", "checkedAt": datetime.now(timezone.utc).isoformat(),
              "endpoint": endpoint, "bucket": bucket, "key": key,
              "sha256": hashlib.sha256(payload).hexdigest(), "denials": []}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # A lost response retains the planned object identity; no automatic retry.
    with args.output.open("x", encoding="utf-8") as output:
        json.dump(record, output, indent=2)
        output.flush()
        os.fsync(output.fileno())
    client = boto3.client("s3", endpoint_url=endpoint, region_name="us-east-1",
        aws_access_key_id=os.environ["MVM_S3_ACCESS_KEY"],
        aws_secret_access_key=os.environ["MVM_S3_SECRET_KEY"],
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"},
                      retries={"max_attempts": 0}, connect_timeout=10, read_timeout=30,
                      request_checksum_calculation="when_required", response_checksum_validation="when_required"))
    client.put_object(Bucket=bucket, Key=key, Body=payload)
    with client.get_object(Bucket=bucket, Key=key)["Body"] as body:
        if body.read() != payload:
            raise ValueError("Scoped readback mismatch")
    with client.get_object(Bucket=bucket, Key=key, Range="bytes=13-63")["Body"] as body:
        if body.read() != payload[13:64]:
            raise ValueError("Scoped range mismatch")
    client.list_objects_v2(Bucket=bucket, Prefix=key, MaxKeys=1)
    checks = [
        ("delete-own-fixture", lambda: client.delete_object(Bucket=bucket, Key=key)),
        ("write-outside-projects", lambda: client.put_object(Bucket=bucket, Key=f"denied-probes/{uuid.uuid4()}", Body=b"permission probe")),
        ("read-outside-projects", lambda: client.get_object(Bucket=bucket, Key="capability-probes/bfded12d-ee06-4802-ab1c-91eed0e0573c/roundtrip.bin")),
        ("list-other-bucket", lambda: client.list_objects_v2(Bucket="pindeck", MaxKeys=1)),
    ]
    for name, operation in checks:
        try:
            result = operation()
            if isinstance(result, dict) and "Body" in result:
                result["Body"].close()
        except ClientError as error:
            if error.response["ResponseMetadata"]["HTTPStatusCode"] == 403:
                record["denials"].append(name)
                continue
            raise ValueError(f"Unexpected denial status: {name}") from None
        raise ValueError(f"Scope violation: {name} was allowed")
    # RustFS filters ListBuckets to buckets allowed by GetBucketLocation.
    # A filtered enumeration is safe; discovering any other bucket is not.
    try:
        visible = client.list_buckets()["Buckets"]
        if any(item["Name"] != bucket for item in visible):
            raise ValueError("Scope violation: other bucket names were disclosed")
        record["bucketEnumeration"] = "filtered_to_application_bucket"
    except ClientError as error:
        if error.response["ResponseMetadata"]["HTTPStatusCode"] != 403:
            raise ValueError("Unexpected bucket enumeration status") from None
        record["bucketEnumeration"] = "denied"
    try:
        with urllib.request.urlopen(f"{endpoint}/{bucket}/{key}", timeout=15):
            raise ValueError("Private fixture is anonymously readable")
    except urllib.error.HTTPError as error:
        if error.code != 403:
            raise ValueError("Unexpected anonymous status") from None
    record.update(state="passed", readbackVerified=True, rangeVerified=True, anonymousHttpStatus=403)
    args.output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        # SDK exceptions can contain request details: never print them.
        result = {"state": "failed", "errorKind": type(error).__name__}
        if isinstance(error, ValueError):
            result["reason"] = str(error)
        print(json.dumps(result))
        raise SystemExit(1)
