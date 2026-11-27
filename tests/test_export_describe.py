"""Describe the material and Google Slides on /slides/ (docs/spec/v2/redesign.md, What PR 3 delivers), against tests/fake_themes.py; the Edge Function
plan-deck and Google are stubbed. The point: the slides carry only what the themes hold, and a sentence the model could not trace is dropped."""
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

from playwright.sync_api import expect

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import SiteCase  # noqa: E402
from test_slides import read_pptx  # noqa: E402

PLAN = {"title": "Status de Payments", "slides": [
    {"kind": "cover", "title": "Payments para o Gustavo", "subtitle": "Novembro"},
    {"kind": "numbers", "title": "Onde estamos", "themes": ["PHZ-0001", "PHZ-0002"]},
    {"kind": "decisions", "title": "Precisa de decisão", "items": [{"theme": "PHZ-0001", "text": "Escolher a adquirente até 01/12"},
                                                                   {"theme": "PHZ-0999", "text": "Frase inventada"}]},
    {"kind": "theme", "theme": "PHZ-0001"},
    {"kind": "theme", "theme": "PHZ-0003"},
    {"kind": "roadmap", "title": "Roadmap", "themes": ["PHZ-0002", "PHZ-0001"]},
]}

GIS_STUB = """window.google = { accounts: { oauth2: { initTokenClient: function (c) {
  window.__gis = c; return { requestAccessToken: function () { c.callback({ access_token: 'tok-google' }); } }; } } } };"""


class ExportDescribeTest(SiteCase):
    def setUp(self):
        super().setUp()
        db = self.db
        db.seed_theme("PHZ-0001", "payments", title={"pt": "Checkout global"}, owner="Luciana", status="at_risk", start_date="2026-10-01", due_date="2026-12-15",
                      problem={"pt": "Cada país tem um checkout."}, solution={"pt": "Um checkout só."}, success={"pt": "Três países no ar."},
                      answers={k: {"state": "confirmed"} for k in ("problem", "solution", "success")})
        db.seed_theme("PHZ-0002", "payments", title={"pt": "Migração CredPay"}, owner="Ana", status="on_track", due_date="2027-01-31")
        db.seed_theme("PHZ-0003", "payments", title={"pt": "Projeto encerrado"}, status="done")
        db.plan_response = PLAN

    def open(self):
        self.page.goto(self.base + "/slides/")
        expect(self.page.locator("h1")).to_have_text("Slides")
        self.page.get_by_role("button", name="Descrever o material").click()

    def describe(self, request="Status de Payments para o Gustavo"):
        self.page.get_by_label("Descreva o material").fill(request)
        self.page.get_by_role("button", name="Montar prévia").click()

    def test_choose_themes_is_the_default_and_unchanged(self):
        self.page.goto(self.base + "/slides/")
        expect(self.page.get_by_role("button", name="Escolher temas")).to_have_attribute("aria-pressed", "true")
        expect(self.page.locator("li[data-theme]").first).to_be_visible()
        expect(self.page.get_by_role("button", name=re.compile(r"Exportar \.pptx"))).to_be_visible()
        self.assertEqual(self.page.get_by_role("button", name="Criar no Google Slides").count(), 0)    # no client id: no Google button

    def test_the_request_goes_to_plan_deck_and_the_preview_keeps_only_what_has_a_theme(self):
        self.open()
        self.describe()
        preview = self.page.get_by_role("region", name="Prévia")
        expect(preview).to_be_visible()
        self.assertEqual(self.db.plan_calls, [{"request": "Status de Payments para o Gustavo", "lang": "pt", "by": ""}])
        kinds = preview.locator("ol.deck-slides > li").evaluate_all("els => els.map(e => e.dataset.kind)")
        self.assertEqual(kinds, ["cover", "numbers", "decisions", "theme", "roadmap"])                 # PHZ-0003 is done: its slide is dropped
        expect(preview.locator('li[data-kind="decisions"] li')).to_have_count(1)
        expect(preview.locator('li[data-kind="decisions"]')).to_contain_text("PHZ-0001 · Checkout global: Escolher a adquirente até 01/12")
        expect(preview).not_to_contain_text("Frase inventada")
        expect(preview.locator("[data-dropped]")).to_have_text("1 frase(s) sem tema de origem foram descartadas.")
        expect(preview.locator('li[data-kind="theme"]')).to_contain_text("PHZ-0001 · Checkout global")

    def test_the_deck_is_drawn_from_the_themes_and_the_plan(self):
        self.open()
        self.describe()
        expect(self.page.get_by_role("region", name="Prévia")).to_be_visible()
        with tempfile.TemporaryDirectory() as d:
            with self.page.expect_download() as dl:
                self.page.get_by_role("button", name="Baixar .pptx").click()
            self.assertRegex(dl.value.suggested_filename, r"^PHIZ-material-\d{4}-\d{2}-\d{2}\.pptx$")
            path = Path(d) / dl.value.suggested_filename
            dl.value.save_as(path)
            slides, _ = read_pptx(path)
        self.assertEqual(len(slides), 5)
        self.assertIn("Payments para o Gustavo", slides[0])
        self.assertIn("Novembro", slides[0])
        self.assertIn("2 | temas", slides[1].replace("\n", " "))                                        # the number comes from the themes, not the model
        self.assertIn("1 em risco ou bloqueados", slides[1])
        self.assertIn("Checkout global: Escolher a adquirente até 01/12", slides[2])
        self.assertNotIn("Frase inventada", " ".join(slides))
        for want in ("Checkout global", "Cada país tem um checkout.", "Um checkout só.", "Três países no ar.", "Responsável: Luciana"):
            self.assertIn(want, slides[3])                                                                # the theme slide is the database's
        self.assertLess(slides[4].index("PHZ-0001"), slides[4].index("PHZ-0002"))                       # the roadmap is by date
        self.assertIn("2026-10-01", slides[4])
        self.assertIn("2027-01-31", slides[4])

    def test_an_empty_request_sends_nothing(self):
        self.open()
        self.page.get_by_role("button", name="Montar prévia").click()
        expect(self.page.locator(".describe .note[role=status]")).to_have_text("Descreva o que você quer no material.")
        self.assertEqual(self.db.plan_calls, [])

    def test_a_failing_function_says_so_and_a_plan_with_nothing_traceable_says_that(self):
        self.db.plan_status = 502
        self.open()
        self.describe()
        expect(self.page.locator(".describe .note[role=status]")).to_have_text("Não foi possível montar o material agora.")
        self.db.plan_status = 200
        self.db.plan_response = {"slides": [{"kind": "theme", "theme": "PHZ-0999"}]}
        self.page.get_by_role("button", name="Montar prévia").click()
        expect(self.page.locator(".describe .note[role=status]")).to_have_text("A IA não devolveu nada que dê para mostrar. Tente descrever de outro jeito.")
        self.assertEqual(self.page.get_by_role("region", name="Prévia").count(), 0)

    def test_the_slide_language_goes_with_the_request(self):
        self.open()
        self.page.get_by_label("Idioma do slide").select_option(label="EN-US")
        self.describe("Payments status")
        expect(self.page.get_by_role("region", name="Prévia")).to_be_visible()
        self.assertEqual(self.db.plan_calls[0]["lang"], "en")

    def test_google_slides_signs_in_and_uploads_the_deck_with_conversion(self):
        self.context.add_init_script("try { localStorage.setItem('phiz-google-client-id', 'client-123.apps.googleusercontent.com') } catch (e) {}")
        self.context.route("https://accounts.google.com/gsi/client", lambda r: r.fulfill(status=200, content_type="text/javascript", body=GIS_STUB))
        uploads = []

        def upload(route):
            req = route.request
            if req.method == "OPTIONS":
                return route.fulfill(status=204, headers={"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "authorization, content-type",
                                                          "Access-Control-Allow-Methods": "POST"})
            uploads.append({"auth": req.headers.get("authorization"), "url": req.url, "body": req.post_data_buffer or b""})
            route.fulfill(status=200, content_type="application/json", headers={"Access-Control-Allow-Origin": "*"}, body=json.dumps({"id": "deck-42"}))
        self.context.route(re.compile(r"https://www\.googleapis\.com/upload/drive/v3/files.*"), upload)
        self.context.route(re.compile(r"https://docs\.google\.com/.*"), lambda r: r.fulfill(status=200, content_type="text/html", body="<p>deck</p>"))
        self.open()
        self.describe()
        expect(self.page.get_by_role("region", name="Prévia")).to_be_visible()
        with self.page.context.expect_page() as tab:
            self.page.get_by_role("button", name="Criar no Google Slides").click()
        tab.value.wait_for_url(re.compile(r"https://docs\.google\.com/presentation/d/deck-42/edit"))
        expect(self.page.locator(".describe .note[role=status]")).to_have_text("Apresentação criada no Google Slides.")
        self.assertEqual(len(uploads), 1)
        self.assertEqual(uploads[0]["auth"], "Bearer tok-google")
        self.assertIn("uploadType=multipart", uploads[0]["url"])
        self.assertIn(b'"mimeType":"application/vnd.google-apps.presentation"', uploads[0]["body"])
        self.assertEqual(self.page.evaluate("window.__gis.scope"), "https://www.googleapis.com/auth/drive.file")
        self.assertEqual(self.page.evaluate("window.__gis.client_id"), "client-123.apps.googleusercontent.com")


if __name__ == "__main__":
    unittest.main()
