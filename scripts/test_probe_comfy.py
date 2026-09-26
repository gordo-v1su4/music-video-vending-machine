"""Deterministic submission/reconciliation guards; no real generation in CI."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("probe_comfy", Path(__file__).with_name("probe-comfy.py"))
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class ProbeReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "receipt.json"
        self.workflow = Path(self.temp.name) / "workflow.json"
        self.workflow.write_text(json.dumps({"1": {"class_type": "LocalNode", "inputs": {}}}))

    def initial(self, provider_id=None):
        probe.persist(self.path, {"probeId": "test-probe", "providerId": provider_id,
                                  "endpoint": probe.ENDPOINT, "state": "submission_intent"}, exclusive=True)

    def test_lost_submission_response_keeps_intent_then_recovers_same_job(self):
        observed = []

        def provider(route, payload=None):
            observed.append(route)
            if route == "/object_info":
                return {"LocalNode": {"api_node": False}}
            if route == "/queue":
                return {"queue_running": [], "queue_pending": []}
            if route == "/system_stats":
                return {}
            if route == "/prompt":
                intent = json.loads(self.path.read_text())
                self.assertEqual(intent["state"], "submission_intent")
                self.assertEqual(payload["extra_data"]["mvm_probe_id"], intent["probeId"])
                raise TimeoutError("response lost")
            self.fail(f"Unexpected route {route}")

        with patch.object(probe, "request", side_effect=provider):
            record = probe.start(self.workflow, self.path)
        self.assertEqual(record["state"], "reconciliation_required")
        self.assertEqual(observed.count("/prompt"), 1)
        history = {"known-job": {
            "prompt": [0, "known-job", {}, {"mvm_probe_id": record["probeId"]}],
            "status": {"completed": True, "status_str": "success"},
            "outputs": {"1": {"images": [{"filename": "result.png"}]}},
        }}
        with patch.object(probe, "request", side_effect=[history, {"queue_running": [], "queue_pending": []}]) as remote:
            recovered = probe.inspect(self.path)
        self.assertEqual(recovered["providerId"], "known-job")
        self.assertEqual(recovered["state"], "generated_unverified")
        self.assertEqual([call.args[0] for call in remote.call_args_list], ["/history", "/queue"])

    def test_missing_receipt_stays_uncertain_without_post(self):
        self.initial("provider-job")
        with patch.object(probe, "request", side_effect=[{}, {"queue_running": [], "queue_pending": []}]) as remote:
            record = probe.inspect(self.path)
        self.assertEqual(record["state"], "reconciliation_required")
        self.assertNotIn("/prompt", [call.args[0] for call in remote.call_args_list])

    def test_existing_intent_cannot_be_submitted_again(self):
        self.initial()
        original = self.path.read_bytes()
        with patch.object(probe, "request", side_effect=[
            {"LocalNode": {"api_node": False}}, {"queue_running": [], "queue_pending": []}, {}
        ]) as remote:
            with self.assertRaises(FileExistsError):
                probe.start(self.workflow, self.path)
        self.assertEqual(self.path.read_bytes(), original)
        self.assertNotIn("/prompt", [call.args[0] for call in remote.call_args_list])

    def test_paid_node_is_rejected_before_intent_or_submission(self):
        with patch.object(probe, "request", return_value={"LocalNode": {"api_node": True}}) as remote:
            with self.assertRaisesRegex(ValueError, "paid API node"):
                probe.start(self.workflow, self.path)
        self.assertEqual(remote.call_count, 1)
        self.assertFalse(self.path.exists())

    def test_ambiguous_provider_jobs_do_not_get_picked(self):
        self.initial()
        entries = [[0, name, {}, {"mvm_probe_id": "test-probe"}] for name in ("first", "second")]
        with patch.object(probe, "request", side_effect=[{}, {"queue_running": entries, "queue_pending": []}]):
            record = probe.inspect(self.path)
        self.assertEqual(record["state"], "ambiguous_provider_receipt")
        self.assertIsNone(record["providerId"])


if __name__ == "__main__":
    unittest.main()
