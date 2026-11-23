"""Smoke tests of the built site in a real browser, with the Supabase API replaced by tests/fake_supabase.py.
The RFCs are the ones of rfcs/ as the importer leaves them in the database (tests/support.py, import_rfc).

  .venv/bin/python -m unittest discover -s tests -v

Locally, use your installed Chrome:  PW_CHANNEL=chrome .venv/bin/python -m unittest discover -s tests -v
(CI installs Playwright's own Chromium). The tests build and start the Next.js app first (tests/support.py, _Site); SITE_URL=<address>
runs them against a deployed site instead.
"""
import sys
import unittest
from pathlib import Path

from playwright.sync_api import expect

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import SiteCase, import_rfc  # noqa: E402
RFC = "PHZ-0002"          # an RFC with diagrams and tables; its first version (v1.0) is an archived page
SECTION = "summary"       # its first section


class SiteTest(SiteCase):
    def setUp(self):
        super().setUp()
        for rid in ("PHZ-0001", "PHZ-0002"):
            import_rfc(self.db, rid)

    # -- helpers --------------------------------------------------------
    def open(self, path=f"/rfc/?id={RFC}", wait_comments=True):
        self.page.goto(self.base + path)
        if path.startswith("/rfc/"):
            self.page.wait_for_selector(".lang.active h2")              # the page is drawn from the database after it loads
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

    def test_versions_and_archived_version(self):
        self.db.seed_theme(RFC, "payments", title={"pt": "CredPay"})
        self.db.seed_attachment(RFC, "v1.0", content_type="text/html", archive_version="1.0", archive_date="2026-10-16", archive_note={"pt": "Primeira versão"})
        page = self.open(wait_comments=False)
        page.click(".vers summary")
        items = page.locator(".vers-pop li")
        self.assertEqual(items.count(), 2)                              # v1.1 from the database, v1.0 an archived page (an attachment of the theme)
        archived = items.nth(1)
        self.assertEqual(archived.locator("a").get_attribute("href"), f"../themes/{RFC}/#attachments")
        self.assertIn("Primeira versão", archived.inner_text())
        archived.locator("a").click()
        expect(page).to_have_url(self.base + f"/themes/{RFC}/#attachments")
        expect(page.get_by_role("region", name="Anexos").locator('tr[data-name="v1.0"]')).to_have_count(1)

    def test_only_archived_versions_the_database_does_not_hold_are_listed(self):
        self.db.seed_attachment(RFC, "v1.0", content_type="text/html", archive_version="1.0", archive_date="2026-10-16")
        self.db.seed_attachment(RFC, "v1.0 de novo", content_type="text/html", archive_version="1.0", archive_date="2026-10-16")      # the same version twice: one entry
        self.db.seed_attachment(RFC, "v1.1", content_type="text/html", archive_version="1.1", archive_date="2026-10-17")                # the database already holds 1.1
        self.db.seed_attachment(RFC, "planilha.xlsx", content_type="application/vnd.ms-excel")                                           # not an archived page
        self.db.seed_attachment("PHZ-0001", "v0.9", content_type="text/html", archive_version="0.9", archive_date="2026-10-01")          # another RFC's
        page = self.open(wait_comments=False)
        page.click(".vers summary")
        self.assertEqual(page.locator(".vers-pop li b").all_inner_texts(), ["v1.1", "v1.0"])

    def test_the_new_version_button_is_in_the_header(self):
        page = self.open(wait_comments=False)
        btn = page.locator("header.bar a.newver")
        expect(btn).to_be_visible()
        self.assertEqual(btn.get_attribute("href"), f"../nova/?edit={RFC}")

    def test_the_old_addresses_under_an_rfc_lead_to_its_attachments(self):
        for path in ("/rfcs/PHZ-0001/openapi/", "/rfcs/PHZ-0001/v1.0.html", "/rfcs/PHZ-0001/openapi.en.yaml", "/rfcs/PHZ-0002/v1.0.html"):
            with self.subTest(path):
                self.page.goto(self.base + path)
                expect(self.page).to_have_url(self.base + f"/themes/{path.split('/')[2]}/#attachments")
        self.page.goto(self.base + "/rfcs/PHZ-0001/")
        expect(self.page).to_have_url(self.base + "/rfc/?id=PHZ-0001")                      # the RFC itself still has its own redirect
        self.assertEqual(self.context.request.get(self.base + "/rfcs/nope/v1.0.html", max_redirects=0).status, 404)

    def test_index_lists_rfcs_and_filters_by_status(self):
        self.db.status_log.append({"rfc_id": RFC, "status": "approved", "author": "Ana", "created_at": "2026-10-21T10:00:00Z"})
        page = self.open("/", wait_comments=False)
        page.wait_for_selector(".card-li")
        self.assertEqual(page.locator(".card-li").count(), 2)
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
        badge = page.locator(".rfcno.st.st-btn")                        # status.js has made the badge a button (it loads last)
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
