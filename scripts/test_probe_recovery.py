"""Review regressions that require no remote services or provider credentials."""
import importlib.util
import io
import os
from pathlib import Path
import stat
import tempfile
import unittest
import uuid
from unittest.mock import Mock, patch


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


recovery = load("recovery", "verify-local-recovery.py")
scope = load("scope", "probe-scoped-storage.py")


class RecoveryRegressionTests(unittest.TestCase):
    def test_restore_writes_available_bytes_and_relocates_the_correct_records(self):
        client = Mock()
        storage = {}
        client.put_object.side_effect = lambda **kw: storage.update({kw["Key"]: kw["Body"]})
        client.get_object.side_effect = lambda **kw: {"Body": io.BytesIO(storage[kw["Key"]])}
        manifest = {"assets": [], "pendingUploads": []}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for group, state, media in (("assets", "verified", b"complete"),
                    ("pendingUploads", "verified", b"complete"),
                    ("pendingUploads", "unverified", b"partial"),
                    ("pendingUploads", "missing", None)):
                record = {"id": str(uuid.uuid4()), "sha256": recovery.digest(b"complete"),
                          "objectState": state}
                if media is not None:
                    record["storedSha256"] = recovery.digest(media)
                    (root / record["storedSha256"]).write_bytes(media)
                manifest[group].append(record)
            with patch.object(recovery, "query") as query:
                recovery.restore_objects(client, manifest, root, "isolated_restore", uuid.uuid4().hex)
            self.assertEqual(client.put_object.call_count, 3)
            self.assertEqual(client.get_object.call_count, 3)
            self.assertEqual(len(storage), 3)
            for index, record in enumerate(manifest["assets"] + manifest["pendingUploads"]):
                table = "assets" if index == 0 else "upload_intents"
                self.assertEqual(query.call_args_list[index].args,
                    ("isolated_restore", f"UPDATE {table} SET object_key='{record['restoredKey']}' WHERE id='{record['id']}'"))
                if record["objectState"] == "missing":
                    self.assertNotIn(record["restoredKey"], storage)
                else:
                    self.assertEqual(recovery.digest(storage[record["restoredKey"]]), record["storedSha256"])

    def test_restore_does_not_repoint_record_after_failed_readback(self):
        client = Mock()
        client.get_object.return_value = {"Body": io.BytesIO(b"corrupt readback")}
        record = {"id": str(uuid.uuid4()), "sha256": recovery.digest(b"complete"),
                  "storedSha256": recovery.digest(b"partial"), "objectState": "unverified"}
        with tempfile.TemporaryDirectory() as directory, patch.object(recovery, "query") as query:
            root = Path(directory)
            (root / record["storedSha256"]).write_bytes(b"partial")
            with self.assertRaises(ValueError):
                recovery.restore_objects(client, {"assets": [], "pendingUploads": [record]}, root,
                                         "isolated_restore", uuid.uuid4().hex)
            query.assert_not_called()
            self.assertNotIn("restoredKey", record)

    def test_pending_upload_preserves_verified_unverified_and_missing_objects(self):
        expected = b"complete source"
        row = {"id": str(uuid.uuid4()), "object_key": "projects/fixture/pending",
               "metadata": {"sha256": recovery.digest(expected), "sizeBytes": len(expected)}}
        with tempfile.TemporaryDirectory() as directory:
            for media, state in ((expected, "verified"), (b"partial", "unverified")):
                client = Mock()
                client.get_object.return_value = {"Body": io.BytesIO(media)}
                record = recovery.backup_object(client, row, Path(directory), pending=True)
                self.assertEqual(record["objectState"], state)
                self.assertEqual(record["sha256"], recovery.digest(expected))
                self.assertEqual((Path(directory) / record["storedSha256"]).read_bytes(), media)
            error = RuntimeError("object missing")
            error.response = {"Error": {"Code": "NoSuchKey"}}
            client.get_object.side_effect = error
            record = recovery.backup_object(client, row, Path(directory), pending=True)
            self.assertEqual(record["objectState"], "missing")
            self.assertNotIn("storedSha256", record)
            with self.assertRaises(RuntimeError):
                recovery.backup_object(client, row, Path(directory))
            for code in ("AccessDenied", "InternalError", "SlowDown"):
                error.response["Error"]["Code"] = code
                with self.subTest(code=code), self.assertRaises(RuntimeError):
                    recovery.backup_object(client, row, Path(directory), pending=True)

    def test_completed_upload_rejects_corrupt_bytes(self):
        client = Mock()
        client.get_object.return_value = {"Body": io.BytesIO(b"bad")}
        row = {"id": str(uuid.uuid4()), "object_key": "fixture",
               "metadata": {"sha256": recovery.digest(b"good"), "sizeBytes": 4}}
        with tempfile.TemporaryDirectory() as directory, self.assertRaises(ValueError):
            recovery.backup_object(client, row, Path(directory))

    def test_identical_content_retains_distinct_asset_storage(self):
        restore = uuid.uuid4().hex
        first = {"id": str(uuid.uuid4()), "sha256": "a" * 64}
        second = {"id": str(uuid.uuid4()), "sha256": first["sha256"]}
        self.assertNotEqual(recovery.restored_key(restore, first), recovery.restored_key(restore, second))
        self.assertEqual(recovery.restored_key(restore, first), recovery.restored_key(restore, first))

    @unittest.skipUnless(os.name == "posix", "POSIX mode check; Windows ACLs verified in live acceptance")
    def test_backup_root_is_private_under_permissive_umask(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "backup"
            previous = os.umask(0)
            try:
                recovery.private_directory(root)
            finally:
                os.umask(previous)
            self.assertEqual(stat.S_IMODE(root.stat().st_mode), 0o700)
            with self.assertRaises(FileExistsError):
                recovery.private_directory(root)

    def test_bucket_discovery_requires_exact_scope(self):
        bucket = "music-vending-machine"
        scope.validate_bucket_discovery([{"Name": bucket}], bucket)
        for rows in ([], [{"Name": "other"}], [{"Name": bucket}, {"Name": "other"}]):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                scope.validate_bucket_discovery(rows, bucket)


if __name__ == "__main__":
    unittest.main()
