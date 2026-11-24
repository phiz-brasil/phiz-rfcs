"""docs/spec/v2/platform.md, "Runtime config": a page rendered on demand runs where the repository is not on disk (Vercel's function). Here the built site is started from
a directory that holds only the build, with no site.config.json above it, and the dynamic routes must still answer."""
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import ROOT, _Site  # noqa: E402


class RuntimeWithoutRepositoryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _Site.build()
        cls.tmp = tempfile.mkdtemp(prefix="phiz-runtime-")
        web = ROOT / "apps" / "web"
        os.symlink(web / ".next", Path(cls.tmp) / ".next")
        os.symlink(ROOT / "node_modules", Path(cls.tmp) / "node_modules")
        for f in ("package.json", "next.config.ts"):
            shutil.copy(web / f, cls.tmp)
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        cls.proc = subprocess.Popen(["node", "node_modules/.bin/next", "start", "-p", str(port), "-H", "127.0.0.1"], cwd=cls.tmp, stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL, start_new_session=True, env={**os.environ, "PHIZ_AUTH_REQUIRED": "0"})
        cls.base = f"http://127.0.0.1:{port}"
        for _ in range(300):
            try:
                urllib.request.urlopen(cls.base + "/themes/", timeout=2).close()
                break
            except urllib.error.HTTPError:
                break
            except OSError:
                time.sleep(0.2)

    @classmethod
    def tearDownClass(cls):
        import signal
        os.killpg(cls.proc.pid, signal.SIGTERM)
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def status(self, path):
        try:
            with urllib.request.urlopen(self.base + path, timeout=20) as r:
                return r.status
        except urllib.error.HTTPError as e:
            return e.code

    def test_the_directory_really_has_no_repository_above_it(self):
        p = Path(self.tmp).resolve()
        self.assertFalse(any((d / "site.config.json").exists() for d in [p, *p.parents]))

    def test_a_theme_page_answers_without_the_repository(self):
        self.assertEqual(self.status("/themes/PHZ-0001/"), 200)

    def test_the_other_routes_answer_too(self):
        for path in ("/themes/", "/slides/", "/overview/", "/board/"):
            self.assertEqual(self.status(path), 200, path)
