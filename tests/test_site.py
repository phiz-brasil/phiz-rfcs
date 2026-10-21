"""Smoke tests of the built site in a real browser, with the Supabase API replaced by tests/fake_supabase.py.

  .venv/bin/python -m unittest discover -s tests -v

Locally, use your installed Chrome:  PW_CHANNEL=chrome .venv/bin/python -m unittest discover -s tests -v
(CI installs Playwright's own Chromium). The tests build the site first (tools/build.py) and serve dist/ on a free port.
"""
import functools
import http.server
import os
import re
import subprocess
import sys
import threading
import unittest
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fake_supabase import FakeSupabase  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RFC = "PHZ-0002"          # a Markdown RFC with diagrams, tables and an archived version (v1.0)
SECTION = "summary"       # its first section


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class SiteTest(unittest.TestCase):
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
        self.context = self.browser.new_context(viewport={"width": 1400, "height": 900})
        self.context.set_default_timeout(8000)
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

    # -- helpers --------------------------------------------------------
    def open(self, path=f"/rfcs/{RFC}/", wait_comments=True):
        self.page.goto(self.base + path)
        if wait_comments:
            self.page.wait_for_selector(".lang.active h2 .cmt-btn")
            self.page.wait_for_function("document.querySelector('.cmt-all')")   # comments loaded
        return self.page

    def section_button(self, section=SECTION):
        return self.page.locator(f"#pt-{section} .cmt-btn")

    def open_section(self, section=SECTION):
        self.section_button(section).click()
        panel = self.page.locator(f"#pt-{section} + .cmt-panel")
        expect(panel).to_be_visible()
        return panel

    def submit(self, panel, body, author="Ana"):
        form = panel.locator("form")
        form.locator("input[name=author]").fill(author)
        form.locator("textarea[name=body]").fill(body)
        form.locator(".cmt-send").click()

    # -- page, languages, versions ----------------------------------------
    def test_languages_toc_and_diagrams(self):
        page = self.open(wait_comments=False)
        sections = page.locator(".lang.active section").count()
        self.assertGreaterEqual(sections, 10)
        self.assertEqual(page.locator(".toc-list.active li").count(), sections)
        page.wait_for_function("document.querySelectorAll('.lang.active pre.mermaid[data-processed]').length > 0")
        self.assertNotIn("Syntax error", page.locator(".lang.active").inner_text())
        pt_title = page.locator(".lang.active h1").inner_text()
        for lang in ("en", "zh"):
            page.click(f"#btn-{lang}")
            expect(page.locator(f'.lang[data-lang="{lang}"]')).to_be_visible()
            self.assertNotEqual(page.locator(".lang.active h1").inner_text(), pt_title)
            self.assertEqual(page.locator(".lang.active section").count(), sections)
        expect(page.locator(".rfcno.st")).to_be_visible()

    def test_versions_and_frozen_page(self):
        page = self.open(wait_comments=False)
        page.click(".vers summary")
        items = page.locator(".vers-pop li")
        self.assertGreaterEqual(items.count(), 2)
        self.assertTrue(items.nth(1).locator("a").count() == 1)         # the archived version links to its page
        page.goto(self.base + f"/rfcs/{RFC}/v1.0.html")
        expect(page.locator(".ver-banner")).to_be_visible()
        page.wait_for_selector(".lang.active h2")
        self.assertEqual(page.locator(".cmt-btn").count(), 0, "archived versions are read-only")

    def test_index_lists_rfcs_and_filters_by_status(self):
        self.db.status_log.append({"rfc_id": RFC, "status": "approved", "author": "Ana", "created_at": "2026-10-21T10:00:00Z"})
        page = self.open("/", wait_comments=False)
        page.wait_for_selector(".card-li")
        self.assertGreaterEqual(page.locator(".card-li").count(), 2)
        self.assertEqual(page.locator(f'.card-li[data-rfc="{RFC}"]').get_attribute("data-status"), "approved")   # live status wins
        page.click('.filters [data-filter="approved"]')
        shown = page.locator(".card-li:not([hidden])")
        self.assertEqual(shown.count(), 1)
        self.assertEqual(shown.first.get_attribute("data-rfc"), RFC)

    # -- comments ---------------------------------------------------------
    def test_comment_then_reply_form_opens_under_the_comment(self):
        self.open()
        panel = self.open_section()
        self.submit(panel, "First comment")
        expect(panel.locator(".cmt-item")).to_have_count(1)
        self.assertEqual(self.db.posts[0]["section"], SECTION)
        self.assertEqual(self.db.posts[0]["rfc_id"], RFC)
        self.assertIsNone(self.db.posts[0]["parent_id"])
        panel.locator(".cmt-acts .cmt-link", has_text="Responder").first.click()
        in_thread = panel.evaluate("p => { const th = p.querySelector('.cmt-thread'); return th.lastElementChild === p._form; }")
        self.assertTrue(in_thread, "the reply form belongs right under the comment, not at the end of the list")
        self.submit(panel, "A reply")
        expect(panel.locator(".cmt-reply")).to_have_count(1)
        self.assertEqual(self.db.posts[1]["parent_id"], self.db.comments[0]["id"])

    def test_delete_comment_hides_it_and_its_replies(self):
        top = self.db.add_comment(RFC, SECTION, "Ana", "To be removed")
        self.db.add_comment(RFC, SECTION, "Bo", "A reply", parent_id=top["id"])
        self.open()
        panel = self.open_section()
        expect(panel.locator(".cmt-item")).to_have_count(2)
        panel.locator(".cmt-thread .cmt-item").first.locator(".cmt-del button").click()
        panel.locator(".cmt-del button", has_text="Sim, excluir").click()
        expect(panel.locator(".cmt-item")).to_have_count(0)
        self.assertEqual(self.db.hides, [top["id"]])

    def test_reaction_counts_as_answer_and_can_be_taken_back(self):
        top = self.db.add_comment(RFC, SECTION, "Ana", "Please confirm")
        self.open()
        self.page.evaluate("localStorage.setItem('phiz-rfc-author', 'Gleison')")
        self.page.reload()
        self.page.wait_for_function("document.querySelector('.cmt-all')")
        panel = self.open_section()
        panel.locator(".cmt-rxadd").click()
        panel.locator(".cmt-rxopt").first.click()                     # 👍
        chip = panel.locator(".cmt-rxchip")
        expect(chip).to_have_count(1)
        self.assertEqual(self.db.posts[-1]["body"], "👍")
        self.assertEqual(self.db.posts[-1]["parent_id"], top["id"])
        expect(panel.locator(".cmt-reply")).to_have_count(0)          # a chip, not a card
        # "Sem resposta" no longer lists it
        self.page.click(".cmt-all")
        self.page.locator(".cmt-drawer .cmt-chip", has_text="Sem resposta").click()
        expect(self.page.locator(".cmt-drawer .cmt-d-item")).to_have_count(0)
        # taking the reaction back hides that reply
        self.page.locator(".cmt-drawer .cmt-x").click()
        chip.click()
        expect(panel.locator(".cmt-rxchip")).to_have_count(0)
        self.assertEqual(len(self.db.hides), 1)

    def test_paragraph_comment_is_numbered_and_listed_in_the_section(self):
        self.open()
        btn = self.page.locator(f'#pt-{SECTION}').locator("xpath=ancestor::section").locator('.cmt-pbtn[data-i="1"]')
        btn.evaluate("b => b.click()")
        panel = self.page.locator(".cmt-para-panel")
        expect(panel).to_be_visible()
        self.submit(panel, "About the second paragraph")
        expect(panel.locator(".cmt-item")).to_have_count(1)
        self.assertEqual(self.db.posts[0]["para"], 1)
        expect(btn.locator(".cmt-n")).to_have_text("1")
        panel_section = self.open_section()
        expect(panel_section.locator(".cmt-ptag")).to_have_text("¶ 2")

    def test_page_works_without_the_para_column(self):
        self.db.has_para = False
        self.db.add_comment(RFC, SECTION, "Ana", "Old style comment")
        self.open()
        self.assertEqual(self.page.locator(".cmt-pbtn").count(), 0)
        panel = self.open_section()
        expect(panel.locator(".cmt-item")).to_have_count(1)
        self.submit(panel, "Still works")
        expect(panel.locator(".cmt-item")).to_have_count(2)
        self.assertNotIn("para", self.db.posts[0])

    # -- status -------------------------------------------------------------
    def test_status_can_be_changed_from_the_page(self):
        page = self.open(wait_comments=False)
        badge = page.locator(".rfcno.st")
        badge.click()
        pop = page.locator(".st-pop")
        expect(pop).to_be_visible()
        pop.locator('.st-opt[data-st="approved"]').click()
        expect(pop.locator(".st-err")).to_be_visible()                 # a name is required
        self.assertEqual(self.db.status_log, [])
        pop.locator("input").fill("Gleison")
        pop.locator('.st-opt[data-st="approved"]').click()
        expect(badge).to_have_attribute("data-st", "approved")
        self.assertEqual(self.db.status_log[-1]["status"], "approved")
        self.assertEqual(self.db.status_log[-1]["author"], "Gleison")
        expect(page.locator('.lang[data-lang="en"] .hero .pill')).to_have_text("Approved")

    def test_live_status_is_shown_on_load(self):
        self.db.status_log.append({"rfc_id": RFC, "status": "implemented", "author": "Ana", "created_at": "2026-10-21T10:00:00Z"})
        page = self.open(wait_comments=False)
        expect(page.locator(".rfcno.st")).to_have_attribute("data-st", "implemented")


if __name__ == "__main__":
    unittest.main()
