"""tools/publish_rfc.py: the single-file RFC is checked like the page does it, then sent with the same calls."""
import io
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))
import publish_rfc  # noqa: E402
from support import png_bytes  # noqa: E402

GOOD = (ROOT / "tests" / "fixtures" / "valid_bundle.md").read_text(encoding="utf-8")


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def with_image(name="diagram.png"):
    out = GOOD.replace("O problema em uma frase.", f"O problema em uma frase.\n\n![Arquitetura](asset:{name})", 1)
    out = out.replace("The problem in one sentence.", f"The problem in one sentence.\n\n![Architecture](asset:{name})", 1)
    return out.replace("一句话说明问题。", f"一句话说明问题。\n\n![架构](asset:{name})", 1)


class Check(unittest.TestCase):
    def test_a_good_file_passes_and_finds_its_images(self):
        errors, _, meta, md, images = publish_rfc.check_bundle(GOOD)
        self.assertEqual(errors, [])
        self.assertEqual(images, [])
        self.assertEqual(meta["title"]["en"], "Test integration")
        errors, _, _, _, images = publish_rfc.check_bundle(with_image())
        self.assertEqual((errors, images), ([], ["diagram.png"]))

    def test_the_problems_the_page_reports_are_reported(self):
        cases = {
            "no metadata": ("Just text\n", "must start with the metadata block"),
            "todo": (GOOD.replace("O problema em uma frase.", "TODO: escrever", 1), "TODO: marker"),
            "raw html": (GOOD.replace("O problema em uma frase.", "Texto <div class=\"x\">cru</div>", 1), "raw HTML is not allowed"),
            "other paragraphs": (GOOD.replace("The problem in one sentence.", "The problem.\n\nA second paragraph.", 1), "different number of paragraphs"),
        }
        for name, (text, expected) in cases.items():
            with self.subTest(name):
                errors = publish_rfc.check_bundle(text)[0]
                self.assertTrue(any(expected in e for e in errors), errors)

    def test_the_template_is_not_publishable_until_filled(self):
        errors = publish_rfc.check_bundle((ROOT / "templates" / "bundle" / "RFC.md").read_text(encoding="utf-8"))[0]
        self.assertTrue(any("TODO:" in e for e in errors))


class Publish(unittest.TestCase):
    def run_tool(self, text, *args, images=None):
        calls = []

        def fake(req, timeout=0):
            body = json.loads(req.data)
            calls.append((req.full_url.rsplit("/", 1)[1], body))
            if calls[-1][0] == "create_rfc":
                return Response(b'{"rfc_id": "PHZ-0009", "version": "1.0"}')
            if calls[-1][0] == "add_rfc_revision":
                return Response(b'{"rfc_id": "PHZ-0003", "version": "1.2"}')
            return Response(b"")
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "rfc.md").write_text(text, encoding="utf-8")
            for name, data in (images or {}).items():
                (Path(d) / name).write_bytes(data)
            out = io.StringIO()
            with mock.patch.object(publish_rfc.urllib.request, "urlopen", fake), mock.patch.object(sys, "argv", ["publish_rfc.py", str(Path(d) / "rfc.md"), *args]), \
                    mock.patch.object(sys, "stdout", out):
                try:
                    publish_rfc.main()
                    code = 0
                except SystemExit as e:
                    code = e.code
        return calls, code, out.getvalue()

    def test_a_new_rfc_is_created_with_the_name_given(self):
        calls, code, out = self.run_tool(GOOD, "--by", "Ana")
        self.assertEqual(code, 0)
        self.assertEqual([c[0] for c in calls], ["create_rfc"])
        body = calls[0][1]
        self.assertEqual((body["p_by"], body["p_authors"], body["p_token"]), ("Ana", ["Ana"], None))
        self.assertIn("rfc/?id=PHZ-0009", out)

    def test_images_are_staged_first_and_a_new_version_names_the_rfc(self):
        calls, code, out = self.run_tool(with_image(), "--by", "Ana", "--id", "phz-0003", "--note", "Nova figura", images={"diagram.png": png_bytes(3, 3)})
        self.assertEqual(code, 0, out)
        self.assertEqual([c[0] for c in calls], ["stage_rfc_asset", "add_rfc_revision"])
        stage, rev = calls[0][1], calls[1][1]
        self.assertEqual((stage["p_name"], stage["p_mime"]), ("diagram.png", "image/png"))
        self.assertEqual((rev["p_rfc_id"], rev["p_note"], rev["p_token"]), ("PHZ-0003", "Nova figura", stage["p_token"]))

    def test_nothing_is_sent_when_something_is_wrong(self):
        calls, code, _ = self.run_tool(with_image(), "--by", "Ana")                       # the image file is missing
        self.assertNotEqual(code, 0)
        self.assertEqual(calls, [])
        calls, code, _ = self.run_tool(GOOD)                                              # no name
        self.assertNotEqual(code, 0)
        self.assertEqual(calls, [])
        calls, code, _ = self.run_tool(with_image(), "--by", "Ana", images={"diagram.png": b"not a png"})
        self.assertNotEqual(code, 0)
        self.assertEqual(calls, [])

    def test_check_only_sends_nothing(self):
        calls, code, out = self.run_tool(GOOD, "--check")
        self.assertEqual((calls, code), ([], 0))
        self.assertIn("checked", out)


if __name__ == "__main__":
    unittest.main()
