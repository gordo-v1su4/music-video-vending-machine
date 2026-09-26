"""Session exchange regressions without real credentials or network calls."""
from concurrent.futures import ThreadPoolExecutor
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("private_probe", Path(__file__).with_name("probe-private-api.py"))
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class SessionProbeTests(unittest.TestCase):
    def setUp(self):
        probe._session_token = None

    def test_parallel_requests_share_one_exchange(self):
        with patch.dict("os.environ", {"MVM_OPERATOR_TOKEN": "synthetic-bootstrap"}), \
                patch.object(probe, "request", return_value=(201, b'{"token":"synthetic-session"}')) as request:
            with ThreadPoolExecutor(max_workers=8) as pool:
                tokens = list(pool.map(lambda _: probe.session_token(), range(16)))
            self.assertEqual(tokens, ["synthetic-session"] * 16)
            request.assert_called_once()
            self.assertFalse(request.call_args.kwargs["authenticated"])
            self.assertEqual(request.call_args.args[:2], ("POST", "/api/v1/sessions"))

    def test_failed_exchange_is_not_cached(self):
        with patch.dict("os.environ", {"MVM_OPERATOR_TOKEN": "synthetic-bootstrap"}), \
                patch.object(probe, "request", return_value=(401, b'{}')):
            with self.assertRaisesRegex(ValueError, "HTTP 201"):
                probe.session_token()
            self.assertIsNone(probe._session_token)
