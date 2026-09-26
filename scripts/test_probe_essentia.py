"""CLI completion semantics against deterministic service responses."""
from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("probe_essentia", Path(__file__).with_name("probe-essentia.py"))
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class EssentiaInspectionTests(unittest.TestCase):
    def inspect(self, response):
        with tempfile.TemporaryDirectory() as directory:
            receipt = Path(directory) / "receipt.json"
            probe.save(receipt, {"endpoint": probe.ENDPOINT, "state": "queued",
                                 "providerId": "8f1f42bcff9d461b95593321af433216"}, exclusive=True)
            with patch("sys.argv", ["probe", "inspect", "--receipt", str(receipt)]), \
                    patch.object(probe, "request", return_value=response) as request, \
                    redirect_stdout(io.StringIO()):
                try:
                    probe.main()
                    code = 0
                except SystemExit as error:
                    code = error.code
            request.assert_called_once_with("/analyze/studio/jobs/8f1f42bcff9d461b95593321af433216")
            self.assertEqual(json.loads(receipt.read_text())["response"], response)
            return code

    def test_pending_inspection_has_distinct_exit_status(self):
        for state in ("queued", "running"):
            with self.subTest(state=state):
                self.assertEqual(self.inspect({"status": state}), 2)

    def test_completed_inspection_requires_results(self):
        for result in (None, {}, [], "missing"):
            with self.subTest(result=result):
                self.assertEqual(self.inspect({"status": "completed", "result": result}), 1)
        self.assertEqual(self.inspect({"status": "completed"}), 1)

    def test_completed_result_passes_service_inspection(self):
        self.assertEqual(self.inspect({"status": "completed", "result": {
            "schema_version": "studio-audio-v1", "duration": 48, "bpm": 120, "beats": [0.5, 1.0]
        }}), 0)

    def test_failed_cancelled_or_unknown_state_cannot_pass(self):
        for state in ("failed", "cancelled", "unknown"):
            with self.subTest(state=state):
                self.assertEqual(self.inspect({"status": state}), 1)


if __name__ == "__main__":
    unittest.main()
