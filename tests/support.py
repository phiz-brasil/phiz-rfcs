"""Shared setup of the browser tests: start the site once (the Next.js app by default, see _Site), start a browser, and give every test
a fresh context where Supabase is a FakeSupabase and nothing else leaves the machine."""
import atexit
import base64
import functools
import json
import http.server
import os
import re
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.request
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
    """The revisions of an RFC that came from the repository, as the importer put them in the database (tests/fixtures/imported/)."""
    return json.loads((ROOT / "tests" / "fixtures" / "imported" / f"{rfc_id}.json").read_text(encoding="utf-8"))


def import_rfc(db, rfc_id):
    """What the database holds for an RFC that came from the repository: its revisions and images (tiny stand-ins), under its own id."""
    db.ids[rfc_id] = "site"
    for rev in imported(rfc_id):
        db.add_revision(rfc_id, rev["bundle"], rev["meta"], rev["authors"], rev["collaborators"], by=rev["edited_by"],
                        note=rev["note"] or None, rev=rev["rev"], created_at=rev["created_at"])
        for name in rev["assets"]:
            db.add_asset(rfc_id, name, rev["rev"], png_bytes(4, 3))


class _Site:
    """The site under test, started once per run and shared by every test class:
    - default: the Next.js app (apps/web), built with `npm run build` and served by `next start`;
    - SITE=static: the old static build (tools/build.py), served from dist/ (to compare the two while both exist);
    - SITE_URL=<address>: a site that is already running (a preview deployment, `npm run dev`…).
    SKIP_BUILD=1 reuses the last Next.js build."""
    url = None
    proc = None
    server = None

    @classmethod
    def start(cls):
        if cls.url:
            return cls.url
        if os.environ.get("SITE_URL"):
            cls.url = os.environ["SITE_URL"].rstrip("/")
        elif os.environ.get("SITE") == "static":
            subprocess.run([sys.executable, str(ROOT / "tools" / "build.py")], cwd=ROOT, check=True, capture_output=True)
            cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(ROOT / "dist")))
            threading.Thread(target=cls.server.serve_forever, daemon=True).start()
            cls.url = f"http://127.0.0.1:{cls.server.server_address[1]}"
        else:
            if not os.environ.get("SKIP_BUILD"):
                subprocess.run(["npm", "run", "build"], cwd=ROOT, check=True, capture_output=True)
            with socket.socket() as s:
                s.bind(("127.0.0.1", 0))
                port = s.getsockname()[1]
            cls.proc = subprocess.Popen([str(ROOT / "node_modules" / ".bin" / "next"), "start", "-p", str(port), "-H", "127.0.0.1"],
                                        cwd=ROOT / "apps" / "web", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            atexit.register(lambda: os.killpg(cls.proc.pid, signal.SIGTERM))
            cls.url = f"http://127.0.0.1:{port}"
            for _ in range(300):
                try:
                    urllib.request.urlopen(cls.url + "/", timeout=2).close()
                    break
                except OSError:
                    time.sleep(0.2)
            else:
                raise RuntimeError("next start did not answer")
        return cls.url


class SiteCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = _Site.start()
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch(channel=os.environ.get("PW_CHANNEL") or None)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()

    def setUp(self):
        self.db = FakeSupabase()
        self.context = self.browser.new_context(viewport={"width": 1400, "height": 900}, locale="pt-BR")   # the site picks its language from the browser; CI runs in en-US
        self.context.set_default_timeout(20000)
        # everything outside the local server (fonts, CDNs) is dropped; Playwright tries the last registered route first,
        # so the Supabase route goes after it
        self.context.route(re.compile(r"^(?!%s).*" % re.escape(self.base)), lambda route: route.abort())     # only the site under test
        self.context.route(re.compile(r"https://[^/]*supabase\.co/.*"), lambda route: self.db.handle(route))
        self.page = self.context.new_page()
        self.errors = []
        self.page.on("pageerror", lambda e: self.errors.append(str(e)))

    def serve_page(self, path, html):
        """A page that exists only for the test, answered by the browser itself (the site is not touched)."""
        self.context.route(self.base + path, lambda route: route.fulfill(status=200, content_type="text/html; charset=utf-8", body=html))

    def tearDown(self):
        self.context.close()
        self.assertEqual(self.errors, [], "JavaScript errors on the page")
