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
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import uuid

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


def private_directory(path):
    path.mkdir(parents=True, exist_ok=False, mode=0o700)
    if os.name == "nt":
        # Restrict the empty directory before any private bytes are written.
        identity = subprocess.run(["whoami", "/user", "/fo", "csv", "/nh"], capture_output=True, text=True, check=True)
        sid = next(csv.reader(identity.stdout.strip().splitlines()))[1]
        if not sid.startswith("S-1-"):
            raise ValueError("Cannot determine the current Windows user SID")
        subprocess.run(["icacls", str(path.resolve()), "/inheritance:r", "/grant:r", f"*{sid}:(OI)(CI)F"],
                       capture_output=True, check=True)
    else:
        path.chmod(0o700)


def restored_key(restore_id, asset):
    # Identical bytes can belong to different assets; object_key is unique.
    return f'projects/{uuid.UUID(restore_id).hex}/restored/{uuid.UUID(asset["id"])}/{asset["sha256"]}'


def backup_object(client, row, objects_dir, *, pending=False):
    metadata = row["metadata"]
    record = {"id": row["id"], "originalKey": row["object_key"],
              "sha256": metadata["sha256"], "expectedBytes": metadata["sizeBytes"]}
    try:
        response = client.get_object(Bucket=BUCKET, Key=row["object_key"])
    except Exception as error:
        code = getattr(error, "response", {}).get("Error", {}).get("Code")
        if pending and code in ("NoSuchKey", "NotFound", "404"):
            return dict(record, objectState="missing")
        raise
    with response["Body"] as body:
        media = body.read()
    stored_hash = digest(media)
    valid = stored_hash == metadata["sha256"] and len(media) == metadata["sizeBytes"]
    if not pending and not valid:
        raise ValueError("Source media integrity mismatch")
    # Even an incomplete/corrupt pending object is retained as evidence. Its
    # expected identity remains unchanged, so reconciliation cannot accept it.
    (objects_dir / stored_hash).write_bytes(media)
    return dict(record, objectState="verified" if valid else "unverified",
                storedSha256=stored_hash, bytes=len(media))


def restore_objects(client, manifest, objects_dir, database, restore_id):
    for table, records in (("assets", manifest["assets"]), ("upload_intents", manifest["pendingUploads"])):
        for asset in records:
            key = restored_key(restore_id, asset)
            if asset["objectState"] != "missing":
                media = (objects_dir / asset["storedSha256"]).read_bytes()
                client.put_object(Bucket=BUCKET, Key=key, Body=media)
                with client.get_object(Bucket=BUCKET, Key=key)["Body"] as body:
                    if digest(body.read()) != asset["storedSha256"]:
                        raise ValueError("Restored object checksum mismatch")
            # Key/hash are generated here; UUID is parsed before interpolation.
            asset_id = str(uuid.UUID(asset["id"]))
            query(database, f"UPDATE {table} SET object_key='{key}' WHERE id='{asset_id}'")
            asset["restoredKey"] = key


def main():
    import boto3
    from botocore.config import Config

    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args()
    with socket.socket() as connection:
        if connection.connect_ex(("127.0.0.1", 5201)) == 0:
            raise ValueError("Stop the isolated acceptance coordinator before taking a cold backup")
    if query(SOURCE, "SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() AND pid<>pg_backend_pid()") != "0":
        raise ValueError("Acceptance database still has active clients")
    private_directory(args.directory)
    objects_dir = args.directory / "objects"
    objects_dir.mkdir()
    client = boto3.client("s3", endpoint_url="https://s3.v1su4.dev", region_name="us-east-1",
        aws_access_key_id=os.environ["MVVM_S3_ACCESS_KEY"], aws_secret_access_key=os.environ["MVVM_S3_SECRET_KEY"],
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"},
                      retries={"max_attempts": 0}, connect_timeout=10, read_timeout=30,
                      request_checksum_calculation="when_required", response_checksum_validation="when_required"))
    dump = command(["pg_dump", "-U", "mvm", "-d", SOURCE, "--format=custom", "--no-owner", "--no-acl"])
    (args.directory / "database.dump").write_bytes(dump)
    rows = json.loads(query(SOURCE, "SELECT COALESCE(json_agg(a),'[]'::json) FROM (SELECT id,object_key,metadata FROM assets ORDER BY id) a"))
    pending = json.loads(query(SOURCE, "SELECT COALESCE(json_agg(a),'[]'::json) FROM (SELECT id,object_key,metadata FROM upload_intents ORDER BY id) a"))
    if not rows:
        raise ValueError("Acceptance requires at least one real uploaded asset")
    manifest = {"schemaVersion": 2, "state": "backup_in_progress", "sourceDatabase": SOURCE,
                "createdAt": datetime.now(timezone.utc).isoformat(), "databaseSha256": digest(dump), "assets": [], "pendingUploads": []}
    for row in rows:
        manifest["assets"].append(backup_object(client, row, objects_dir))
    for row in pending:
        manifest["pendingUploads"].append(backup_object(client, row, objects_dir, pending=True))
    manifest["state"] = "backup_complete"
    (args.directory / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    # Verify the actual backup bytes before creating any restore target.
    if digest((args.directory / "database.dump").read_bytes()) != manifest["databaseSha256"]:
        raise ValueError("Backup database checksum mismatch")
    for asset in manifest["assets"] + manifest["pendingUploads"]:
        if asset["objectState"] == "missing":
            continue
        data = (objects_dir / asset["storedSha256"]).read_bytes()
        if digest(data) != asset["storedSha256"] or len(data) != asset["bytes"]:
            raise ValueError("Backup media checksum mismatch")
    restore_id = uuid.uuid4().hex
    database = "mvm_storage_restore_" + restore_id
    manifest.update(state="restore_started", restoredDatabase=database, restoreId=restore_id)
    (args.directory / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    command(["createdb", "-U", "mvm", database])
    command(["pg_restore", "-U", "mvm", "-d", database, "--exit-on-error", "--no-owner", "--no-acl"],
            (args.directory / "database.dump").read_bytes())
    restore_objects(client, manifest, objects_dir, database, restore_id)
    for table in ("projects", "project_events"):
        # Compare full logical records with stable ordering, not only row counts.
        sql = f"SELECT COALESCE(json_agg(t ORDER BY row_to_json(t)::text),'[]'::json) FROM {table} t"
        if query(SOURCE, sql) != query(database, sql):
            raise ValueError("Restored database contents differ")
    sql = "SELECT COALESCE(json_agg(a),'[]'::json) FROM (SELECT id,project_id,metadata FROM assets ORDER BY id) a"
    if query(SOURCE, sql) != query(database, sql):
        raise ValueError("Restored asset identities differ")
    sql = "SELECT COALESCE(json_agg(to_jsonb(t)-'object_key' ORDER BY id),'[]'::json) FROM upload_intents t"
    if query(SOURCE, sql) != query(database, sql):
        raise ValueError("Restored pending upload identities differ")
    manifest.update(state="restored_and_verified", restoredAt=datetime.now(timezone.utc).isoformat(),
                    limits="Cold isolated fixture; pending records and available bytes restored; coordinator reconciliation requires separate live verification. No production scheduling or off-host backup acceptance.")
    (args.directory / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: manifest[key] for key in ("state", "restoredDatabase", "databaseSha256")}))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(json.dumps({"state": "failed", "errorKind": type(error).__name__,
                          "reason": str(error) if isinstance(error, ValueError) else "Inspect retained partial state; never overwrite an existing restore target"}))
        raise SystemExit(1)
