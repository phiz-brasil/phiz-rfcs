"""RFCs created on the site: the new-RFC page (template, prompt, checks, preview, publish, edit), the page that shows them, the index,
and what happens to hostile content. Supabase is tests/fake_supabase.py."""
import re
import sys
import unittest
from pathlib import Path

from playwright.sync_api import expect

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import ROOT, SiteCase  # noqa: E402

BUNDLE = (ROOT / "tests" / "fixtures" / "valid_bundle.md").read_text(encoding="utf-8")
META = {"title": {"pt": "Integração de teste", "en": "Test integration", "zh": "测试集成"},
        "summary": {"pt": "Resumo", "en": "Summary", "zh": "摘要"}, "systems": ["channel", "vault"]}


class LiveRfcTest(SiteCase):
    def fill(self, text):
        self.page.locator("#text").fill(text)

    def publish_valid(self, name="Ana", collabs="Bo, Cy"):
        page = self.page
        page.goto(self.base + "/nova/")
        self.fill(BUNDLE)
        expect(page.locator("#result .ok")).to_be_visible()
        page.locator("#by").fill(name)
        page.locator("#collabs").fill(collabs)
        page.locator("#publish").click()
        page.wait_for_url(re.compile(r"/rfc/\?id=PHZ-\d{4}"))
        page.wait_for_selector(".lang.active h1")

    # -- the new-RFC page ---------------------------------------------------
    def test_page_offers_the_template_and_the_prompt(self):
        page = self.page
        page.goto(self.base + "/nova/")
        self.assertEqual(page.locator("#dl-template").get_attribute("href"), "../assets/templates/RFC.md")
        page.wait_for_function("document.getElementById('prompt').value.length > 200")
        self.assertIn("TODO:", page.locator("#prompt").input_value())
        template = page.request.get(self.base + "/assets/templates/RFC.md").text()
        self.assertIn("<!-- lang:zh -->", template)
        expect(page.locator("#publish")).to_be_disabled()

    def test_the_unfilled_template_is_refused_with_the_reasons(self):
        page = self.page
        page.goto(self.base + "/nova/")
        self.fill((ROOT / "templates" / "bundle" / "RFC.md").read_text(encoding="utf-8"))
        expect(page.locator("#result .bad")).to_be_visible()
        self.assertIn("TODO:", page.locator("#result .issues").inner_text())
        expect(page.locator("#publish")).to_be_disabled()

    def test_each_mistake_is_explained_and_blocks_publishing(self):
        page = self.page
        page.goto(self.base + "/nova/")
        self.fill(BUNDLE.replace("## Summary {#summary}", "## Summary {#resume}"))
        expect(page.locator("#result .issues")).to_contain_text("Section ids differ")
        self.fill(BUNDLE.replace("The problem in one sentence.\n\n", "", 1))
        expect(page.locator("#result .issues")).to_contain_text("different number of paragraphs")
        expect(page.locator("#publish")).to_be_disabled()

    def test_a_file_can_be_chosen_instead_of_pasted(self):
        page = self.page
        page.goto(self.base + "/nova/")
        page.locator("#file").set_input_files(str(ROOT / "tests" / "fixtures" / "valid_bundle.md"))
        expect(page.locator("#result .ok")).to_be_visible()
        self.assertIn("Test integration", page.locator("#text").input_value())
        expect(page.locator("#publish")).to_be_enabled()

    def test_preview_shows_the_rfc_before_publishing(self):
        page = self.page
        page.goto(self.base + "/nova/")
        self.fill(BUNDLE)
        page.locator("#preview-toggle").click()
        frame = page.frame_locator("#preview")
        expect(frame.locator(".lang.active h1")).to_have_text("Integração de teste")
        expect(frame.locator("section")).to_have_count(3)
        page.locator('[data-pl="zh"]').click()
        expect(frame.locator(".lang.active h1")).to_have_text("测试集成")

    # -- publishing and reading ---------------------------------------------
    def test_publishing_creates_the_rfc_with_author_and_collaborators(self):
        self.publish_valid()
        page = self.page
        fn, body = self.db.calls[-1]
        self.assertEqual(fn, "create_rfc")
        self.assertEqual(body["p_authors"], ["Ana"])
        self.assertEqual(body["p_collaborators"], ["Bo", "Cy"])
        self.assertEqual(body["p_by"], "Ana")
        self.assertEqual(body["p_meta"]["title"]["en"], "Test integration")
        self.assertEqual(self.db.ids["PHZ-0003"], "site")                      # the next id of the shared sequence
        hero = page.locator(".lang.active .hero").inner_text()
        self.assertIn("Ana", hero)
        self.assertIn("colaboradores", hero.lower())
        self.assertIn("Bo, Cy", hero)
        self.assertEqual(page.locator(".lang.active section").count(), 3)
        page.wait_for_function("document.querySelectorAll('.lang.active pre.mermaid[data-processed]').length > 0")
        for lang in ("en", "zh"):
            page.click(f"#btn-{lang}")
            self.assertEqual(page.locator(".lang.active section").count(), 3)
        expect(page.locator(".vers summary")).to_have_text(re.compile(r"v1\.0"))

    def test_comments_and_status_work_on_a_site_rfc(self):
        self.db.seed_rfc(BUNDLE, META)
        page = self.page
        page.goto(self.base + "/rfc/?id=PHZ-0003")
        page.wait_for_selector(".lang.active h2 .cmt-btn")
        page.locator("#pt-summary .cmt-btn").click()
        panel = page.locator("#pt-summary + .cmt-panel")
        panel.locator("input[name=author]").fill("Dee")
        panel.locator("textarea[name=body]").fill("A comment on a site RFC")
        panel.locator(".cmt-send").click()
        expect(panel.locator(".cmt-item")).to_have_count(1)
        self.assertEqual(self.db.posts[-1]["rfc_id"], "PHZ-0003")
        badge = page.locator(".rfcno.st")
        badge.click()
        pop = page.locator(".st-pop")
        pop.locator("input").fill("Dee")
        pop.locator('.st-opt[data-st="in-review"]').click()
        expect(badge).to_have_attribute("data-st", "in-review")
        self.assertEqual(self.db.status_log[-1]["rfc_id"], "PHZ-0003")

    def test_unknown_rfc_says_so(self):
        page = self.page
        page.goto(self.base + "/rfc/?id=PHZ-9999")
        expect(page.locator("main .live-state")).to_be_visible()
        page.wait_for_function("document.querySelector('main').innerText.match(/não encontrada/i)")

    def test_a_refused_publication_explains_and_can_be_retried(self):
        self.db.rate_limited = True
        page = self.page
        page.goto(self.base + "/nova/")
        self.fill(BUNDLE)
        page.locator("#by").fill("Ana")
        page.locator("#publish").click()
        expect(page.locator("#publish-note")).to_contain_text("Muitas publicações")
        expect(page.locator("#publish")).to_be_enabled()
        self.assertEqual(self.db.revisions, [])

    def test_a_name_is_required_to_publish(self):
        page = self.page
        page.goto(self.base + "/nova/")
        self.fill(BUNDLE)
        page.locator("#publish").click()
        expect(page.locator("#publish-note")).to_contain_text("nome")
        self.assertEqual(self.db.calls, [])

    # -- editing -----------------------------------------------------------
    def test_editing_adds_a_version_and_keeps_the_old_one(self):
        rid = self.db.seed_rfc(BUNDLE, META, authors=["Ana"], collaborators=["Bo"])
        page = self.page
        page.goto(self.base + f"/nova/?edit={rid}")
        expect(page.locator("#edit-id")).to_have_text(rid)
        expect(page.locator("#result .ok")).to_be_visible()
        self.assertEqual(page.locator("#authors").input_value(), "Ana")
        self.assertEqual(page.locator("#collabs").input_value(), "Bo")
        self.fill(page.locator("#text").input_value().replace("Another sentence.", "A changed sentence."))
        expect(page.locator("#result .ok")).to_be_visible()
        page.locator("#by").fill("Eli")
        page.locator("#note").fill("changed a sentence")
        page.locator("#publish").click()
        page.wait_for_url(re.compile(r"/rfc/\?id=PHZ-0003"))
        page.wait_for_selector(".lang.active h1")
        fn, body = self.db.calls[-1]
        self.assertEqual((fn, body["p_rfc_id"], body["p_by"], body["p_note"]), ("add_rfc_revision", rid, "Eli", "changed a sentence"))
        expect(page.locator(".vers summary")).to_have_text(re.compile(r"v1\.1"))
        self.assertIn("Change 2", page.locator('.lang[data-lang="en"]').inner_html())
        page.click(".vers summary")
        self.assertEqual(page.locator(".vers-pop li").count(), 2)
        self.assertIn("Eli", page.locator(".vers-pop li").first.inner_text())
        # the first version is still there, read-only
        page.goto(self.base + f"/rfc/?id={rid}&v=1.0")
        expect(page.locator(".ver-banner")).to_be_visible()
        page.wait_for_selector(".lang.active h1")
        self.assertEqual(page.locator(".cmt-btn").count(), 0)
        self.assertIn("Another sentence.", page.locator('.lang[data-lang="en"]').text_content())

    def test_editing_a_repository_rfc_is_refused(self):
        page = self.page
        page.goto(self.base + "/nova/?edit=PHZ-0001")
        page.wait_for_function("document.getElementById('result').innerText.match(/não encontrada/i)")

    # -- the index -----------------------------------------------------------
    def test_index_lists_rfcs_from_the_site_with_the_repository_ones(self):
        self.db.seed_rfc(BUNDLE, META)
        page = self.page
        page.goto(self.base + "/")
        page.wait_for_selector('.card-li[data-rfc="PHZ-0003"]')
        card = page.locator('.card-li[data-rfc="PHZ-0003"]')
        self.assertEqual(card.locator("a.card").get_attribute("href"), "rfc/?id=PHZ-0003")
        self.assertIn("Integração de teste", card.inner_text())
        self.assertIn("v1.0", card.inner_text())
        ids = page.locator(".card-li").evaluate_all("els => els.map(e => e.dataset.rfc)")
        self.assertEqual(ids, sorted(ids, reverse=True))
        self.assertEqual(page.locator(".newrfc").get_attribute("href"), "nova/")
        self.db.status_log.append({"rfc_id": "PHZ-0003", "status": "approved", "author": "Ana", "created_at": "2026-10-22T10:00:00Z"})
        page.reload()
        page.wait_for_selector('.card-li[data-rfc="PHZ-0003"][data-status="approved"]')
        page.click('.filters [data-filter="approved"]')
        self.assertEqual(page.locator(".card-li:not([hidden])").count(), 1)

    def test_the_central_comments_page_links_to_site_rfcs(self):
        rid = self.db.seed_rfc(BUNDLE, META)
        self.db.add_comment(rid, "summary", "Dee", "A comment on a site RFC")
        page = self.page
        page.goto(self.base + "/comments/")
        link = page.locator('a[href*="rfc/?id=PHZ-0003"]').first
        link.wait_for()
        self.assertTrue(link.get_attribute("href").startswith("../rfc/?id=PHZ-0003&c="))
        self.assertIn("Integração de teste", page.locator("#cmt-root").inner_text())

    # -- hostile content -------------------------------------------------------
    def test_hostile_markup_in_an_upload_never_runs(self):
        evil = BUNDLE.replace("The problem in one sentence.",
                              '<script>window.__pwned = 1</script> <img src=x onerror="window.__pwned = 2"> [click](javascript:window.__pwned=3) '
                              '![t](http://insecure.example/a.png) ![ok](https://example.com/ok.png)')
        self.db.seed_rfc(evil, META)
        page = self.page
        page.goto(self.base + "/rfc/?id=PHZ-0003")
        page.wait_for_selector(".lang.active h1")
        page.wait_for_timeout(500)
        self.assertIsNone(page.evaluate("window.__pwned"))
        html = page.locator('.lang[data-lang="en"]').inner_html()
        self.assertNotIn("<script", html)                                     # shown as text, not as an element
        self.assertIn("&lt;script&gt;", html)
        self.assertEqual(page.locator("[onerror], [onclick], .lang script").count(), 0)
        self.assertEqual(page.locator('a[href^="javascript"]').count(), 0)
        self.assertEqual(page.locator('img[src^="http://"]').count(), 0)
        self.assertEqual(page.locator('.lang[data-lang="en"] img').count(), 1)
        self.assertEqual(page.locator('.lang[data-lang="en"] img').get_attribute("src"), "https://example.com/ok.png")


if __name__ == "__main__":
    unittest.main()
