"""pages-redirect/: what GitHub Pages serves at the old address. Every old address (path, query and #hash) must land on the same address of
the site on Vercel. Both hosts are answered by the browser itself; nothing leaves the machine."""
import os
import re
import unittest
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
PAGE = (ROOT / "pages-redirect" / "404.html").read_text(encoding="utf-8")
OLD = "https://phiz-brasil.github.io/phiz-rfcs"
NEW = "https://phiz-rfcs.vercel.app"


class OldAddress(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch(channel=os.environ.get("PW_CHANNEL") or None)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()

    def test_every_old_address_goes_to_the_same_address_on_vercel(self):
        ctx = self.browser.new_context()
        ctx.route(re.compile(r"^(?!https://phiz-brasil\.github\.io/|https://phiz-rfcs\.vercel\.app/).*"), lambda r: r.abort())
        ctx.route(re.compile(r"^https://phiz-brasil\.github\.io/.*"), lambda r: r.fulfill(status=404, content_type="text/html", body=PAGE))
        ctx.route(re.compile(r"^https://phiz-rfcs\.vercel\.app/.*"), lambda r: r.fulfill(status=200, content_type="text/html", body="<p>new</p>"))
        page = ctx.new_page()
        for old, new in [("/", "/"), ("", "/"), ("/rfc/?id=PHZ-0001&c=abc#pt-summary", "/rfc/?id=PHZ-0001&c=abc#pt-summary"),
                         ("/rfcs/PHZ-0002/", "/rfcs/PHZ-0002/"), ("/rfcs/PHZ-0001/v1.0.html", "/rfcs/PHZ-0001/v1.0.html"),
                         ("/nova/?edit=PHZ-0003", "/nova/?edit=PHZ-0003"), ("/assets/skill/phiz-rfc.zip", "/assets/skill/phiz-rfc.zip")]:
            with self.subTest(old=old):
                page.goto(OLD + old)
                page.wait_for_url(NEW + new)
        ctx.close()

    def test_index_and_404_are_the_same_page(self):
        self.assertEqual((ROOT / "pages-redirect" / "index.html").read_text(encoding="utf-8"), PAGE)


if __name__ == "__main__":
    unittest.main()
