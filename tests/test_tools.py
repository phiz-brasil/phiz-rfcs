"""tools/new_rfc.py: where the id of a new repository RFC comes from."""
import io
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import new_rfc  # noqa: E402


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class ReserveId(unittest.TestCase):
    def test_the_id_comes_from_the_shared_sequence(self):
        seen = {}

        def fake(req, timeout=0):
            seen["url"], seen["body"] = req.full_url, json.loads(req.data)
            return Response(b'"PHZ-0007"')
        with mock.patch.object(new_rfc.urllib.request, "urlopen", fake):
            self.assertEqual(new_rfc.reserve_id("Ana"), "PHZ-0007")
        self.assertTrue(seen["url"].endswith("/rest/v1/rpc/reserve_rfc_id"))
        self.assertEqual(seen["body"], {"p_by": "Ana"})

    def test_an_unreachable_database_falls_back_to_the_repository(self):
        with mock.patch.object(new_rfc.urllib.request, "urlopen", side_effect=OSError("offline")):
            self.assertIsNone(new_rfc.reserve_id("Ana"))

    def test_nonsense_answers_are_not_used_as_ids(self):
        for body in (b'"nope"', b"{}", b"null", b'"PHZ-12"'):
            with self.subTest(body=body), mock.patch.object(new_rfc.urllib.request, "urlopen", lambda req, timeout=0, b=body: Response(b)):
                self.assertIsNone(new_rfc.reserve_id("Ana"))


if __name__ == "__main__":
    unittest.main()
