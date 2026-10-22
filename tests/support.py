"""Shared setup of the browser tests: build the site once, serve dist/ on a free port, start a browser, and give every test a
fresh context where Supabase is a FakeSupabase and nothing else leaves the machine."""
import base64
import functools
import http.server
import os
import re
import subprocess
import sys
import threading
import struct
import unittest
import zlib
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fake_supabase import FakeSupabase  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

# a loaded machine (or a shared CI runner) can take several seconds to load a page full of Mermaid diagrams
expect.set_options(timeout=15000)


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def png_bytes(width=2, height=2, color=(200, 30, 30)):
    """A real, tiny PNG (solid colour)."""
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    raw = b"".join(b"\x00" + bytes(color) * width for _ in range(height))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


@functools.lru_cache(maxsize=None)
def imported(rfc_id):
    """The revisions tools/import_rfcs.py makes of an RFC of rfcs/ (converted once per run)."""
    sys.path.insert(0, str(ROOT / "tools"))
    import import_rfcs
    return import_rfcs.revisions_of(ROOT / "rfcs" / rfc_id)


def import_rfc(db, rfc_id):
    """What the importer leaves in the database for an RFC of rfcs/: its revisions and images (tiny stand-ins), under its own id."""
    db.ids[rfc_id] = "site"
    for rev in imported(rfc_id):
        db.add_revision(rfc_id, rev["bundle"], rev["meta"], rev["authors"], rev["collaborators"], by=rev["edited_by"],
                        note=rev["note"] or None, rev=rev["rev"], created_at=rev["created_at"])
        for name in rev["assets"].files:
            db.add_asset(rfc_id, name, rev["rev"], png_bytes(4, 3))


class SiteCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run([sys.executable, str(ROOT / "tools" / "build.py")], cwd=ROOT, check=True, capture_output=True)
        handler = functools.partial(Quiet, directory=str(ROOT / "dist"))
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch(channel=os.environ.get("PW_CHANNEL") or None)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        cls.server.shutdown()

    def setUp(self):
        self.db = FakeSupabase()
        self.context = self.browser.new_context(viewport={"width": 1400, "height": 900}, locale="pt-BR")   # the site picks its language from the browser; CI runs in en-US
        self.context.set_default_timeout(20000)
        # everything outside the local server (fonts, CDNs) is dropped; Playwright tries the last registered route first,
        # so the Supabase route goes after it
        self.context.route(re.compile(r"^(?!http://127\.0\.0\.1).*"), lambda route: route.abort())
        self.context.route(re.compile(r"https://[^/]*supabase\.co/.*"), lambda route: self.db.handle(route))
        self.page = self.context.new_page()
        self.errors = []
        self.page.on("pageerror", lambda e: self.errors.append(str(e)))

    def tearDown(self):
        self.context.close()
        self.assertEqual(self.errors, [], "JavaScript errors on the page")
