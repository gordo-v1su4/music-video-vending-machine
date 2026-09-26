# /// script
# requires-python = ">=3.12"
# dependencies = ["boto3==1.43.103"]
# ///
"""Cold backup/restore acceptance for the isolated local PostgreSQL fixture.

Stop the acceptance coordinator on 5201 first. This deliberately targets only
the mvm-dev-postgres container and mvm_storage_acceptance database. It creates a
new restore database and fresh object keys, retaining the source and backup.
This is a verification harness, not a deployed backup scheduler.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import uuid

import boto3
from botocore.config import Config

CONTAINER = "mvm-dev-postgres"
SOURCE = "mvm_storage_acceptance"
BUCKET = "music-vending-machine"


def command(arguments, data=None):
    result = subprocess.run(["docker", "exec", "-i", CONTAINER, *arguments], input=data, capture_output=True)
    if result.returncode:
        raise RuntimeError("PostgreSQL tool failed; retained partial backup requires inspection")
    return result.stdout


def query(database, sql):
    return command(["psql", "-X", "-v", "ON_ERROR_STOP=1", "-U", "mvm", "-d", database, "-Atc", sql]).decode().strip()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args()
    with socket.socket() as connection:
        if connection.connect_ex(("127.0.0.1", 5201)) == 0:
            raise ValueError("Stop the isolated acceptance coordinator before taking a cold backup")
    if query(SOURCE, "SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() AND pid<>pg_backend_pid()") != "0":
        raise ValueError("Acceptance database still has active clients")
    args.directory.mkdir(parents=True, exist_ok=False)
    objects_dir = args.directory / "objects"
    objects_dir.mkdir()
    client = boto3.client("s3", endpoint_url="https://s3.v1su4.dev", region_name="us-east-1",
        aws_access_key_id=os.environ["MVM_S3_ACCESS_KEY"], aws_secret_access_key=os.environ["MVM_S3_SECRET_KEY"],
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"},
                      retries={"max_attempts": 0}, connect_timeout=10, read_timeout=30,
                      request_checksum_calculation="when_required", response_checksum_validation="when_required"))
    dump = command(["pg_dump", "-U", "mvm", "-d", SOURCE, "--format=custom", "--no-owner", "--no-acl"])
    (args.directory / "database.dump").write_bytes(dump)
    rows = json.loads(query(SOURCE, "SELECT COALESCE(json_agg(a),'[]'::json) FROM (SELECT id,object_key,metadata FROM assets ORDER BY id) a"))
    if query(SOURCE, "SELECT count(*) FROM upload_intents") != "0":
        raise ValueError("Resolve fixture upload intents before this completed-asset backup acceptance")
    if not rows:
        raise ValueError("Acceptance requires at least one real uploaded asset")
    manifest = {"schemaVersion": 1, "state": "backup_in_progress", "sourceDatabase": SOURCE,
                "createdAt": datetime.now(timezone.utc).isoformat(), "databaseSha256": digest(dump), "assets": []}
    for row in rows:
        with client.get_object(Bucket=BUCKET, Key=row["object_key"])["Body"] as body:
            media = body.read()
        metadata = row["metadata"]
        if digest(media) != metadata["sha256"] or len(media) != metadata["sizeBytes"]:
            raise ValueError("Source media integrity mismatch")
        (objects_dir / metadata["sha256"]).write_bytes(media)
        manifest["assets"].append({"id": row["id"], "originalKey": row["object_key"],
                                   "sha256": metadata["sha256"], "bytes": len(media)})
    manifest["state"] = "backup_complete"
    (args.directory / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    # Verify the actual backup bytes before creating any restore target.
    if digest((args.directory / "database.dump").read_bytes()) != manifest["databaseSha256"]:
        raise ValueError("Backup database checksum mismatch")
    for asset in manifest["assets"]:
        data = (objects_dir / asset["sha256"]).read_bytes()
        if digest(data) != asset["sha256"] or len(data) != asset["bytes"]:
            raise ValueError("Backup media checksum mismatch")
    restore_id = uuid.uuid4().hex
    database = "mvm_storage_restore_" + restore_id
    manifest.update(state="restore_started", restoredDatabase=database, restoreId=restore_id)
    (args.directory / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    command(["createdb", "-U", "mvm", database])
    command(["pg_restore", "-U", "mvm", "-d", database, "--exit-on-error", "--no-owner", "--no-acl"],
            (args.directory / "database.dump").read_bytes())
    for asset in manifest["assets"]:
        key = f'projects/{restore_id}/restored/{asset["sha256"]}'
        media = (objects_dir / asset["sha256"]).read_bytes()
        client.put_object(Bucket=BUCKET, Key=key, Body=media)
        with client.get_object(Bucket=BUCKET, Key=key)["Body"] as body:
            if digest(body.read()) != asset["sha256"]:
                raise ValueError("Restored object checksum mismatch")
        # Key/hash are generated here; UUID is parsed before interpolation.
        asset_id = str(uuid.UUID(asset["id"]))
        query(database, f"UPDATE assets SET object_key='{key}' WHERE id='{asset_id}'")
        asset["restoredKey"] = key
    for table in ("projects", "project_events", "upload_intents"):
        # Compare full logical records with stable ordering, not only row counts.
        sql = f"SELECT COALESCE(json_agg(t ORDER BY row_to_json(t)::text),'[]'::json) FROM {table} t"
        if query(SOURCE, sql) != query(database, sql):
            raise ValueError("Restored database contents differ")
    sql = "SELECT COALESCE(json_agg(a),'[]'::json) FROM (SELECT id,project_id,metadata FROM assets ORDER BY id) a"
    if query(SOURCE, sql) != query(database, sql):
        raise ValueError("Restored asset identities differ")
    manifest.update(state="restored_and_verified", restoredAt=datetime.now(timezone.utc).isoformat(),
                    limits="Cold isolated fixture; no production scheduling, off-host backup or pending-upload restore acceptance")
    (args.directory / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: manifest[key] for key in ("state", "restoredDatabase", "databaseSha256")}))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(json.dumps({"state": "failed", "errorKind": type(error).__name__,
                          "reason": str(error) if isinstance(error, ValueError) else "Inspect retained partial state; never overwrite an existing restore target"}))
        raise SystemExit(1)
