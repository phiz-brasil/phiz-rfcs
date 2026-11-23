"""Design part 3: the theme page as a header of key facts plus sections, with the edit form folded, and the themes list as tables."""
import re
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from playwright.sync_api import expect

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import SiteCase  # noqa: E402

TODAY = datetime.now(timezone.utc).date()


class ThemePageTest(SiteCase):
    def setUp(self):
        super().setUp()
        db = self.db
        db.seed_theme("PHZ-0001", "api-platform", title={"pt": "Business Messaging API"}, status="on_track", stage=3, owner="Gleison",
                      due_date=(TODAY - timedelta(days=2)).isoformat(), progress={"pt": "Contrato fechado"}, what_it_is={"pt": "Uma API"}, tags=["china"])
        db.seed_theme("PHZ-0010", "outros", kind="task", title={"pt": "Game Center"})

    def theme(self, tid="PHZ-0001", query=""):
        self.page.goto(self.base + f"/themes/{tid}/{query}")
        expect(self.page.locator("h1")).to_be_visible()

    def test_the_header_shows_the_key_facts_of_the_theme(self):
        self.theme()
        expect(self.page.locator(".theme-hero .eyebrow")).to_have_text(re.compile(r"PHZ-0001 · Projeto · API Platform"))
        facts = self.page.locator('[data-block="facts"]')
        for want in ("No prazo", "03 Decisão", "Gleison", "Contrato fechado"):
            expect(facts).to_contain_text(want)
        expect(facts.locator(".overdue")).to_have_text((TODAY - timedelta(days=2)).isoformat())     # an open theme past its estimate is in red
        self.assertEqual(self.page.locator(".theme-hero").get_by_role("link", name="Exportar .pptx").get_attribute("href"), "/slides/?theme=PHZ-0001")

    def test_a_section_menu_leads_to_each_part_of_the_page(self):
        self.theme()
        links = self.page.get_by_role("navigation", name="Seções do tema").get_by_role("link")
        self.assertEqual(links.evaluate_all("els => els.map(e => e.getAttribute('href'))"),
                         ["#sec-summary", "#sec-updates", "#sec-records", "#sec-execution", "#sec-attachments", "#sec-links", "#sec-history"])
        for href in links.evaluate_all("els => els.map(e => e.getAttribute('href'))"):
            expect(self.page.locator(href)).to_have_count(1)
        self.theme("PHZ-0010")                                                                        # a standalone task has no execution section
        self.assertNotIn("#sec-execution", self.page.get_by_role("navigation", name="Seções do tema").get_by_role("link").evaluate_all("els => els.map(e => e.getAttribute('href'))"))

    def test_the_data_is_read_only_until_someone_presses_edit(self):
        self.theme()
        expect(self.page.get_by_role("form", name="theme")).to_have_count(0)
        ro = self.page.get_by_role("region", name="theme")
        expect(ro).to_contain_text("Uma API")
        expect(ro).to_contain_text("#china")
        expect(ro).not_to_contain_text("Que problema")                                                 # texts nobody wrote are left out
        self.page.get_by_role("button", name="Editar dados do tema").click()
        expect(self.page.get_by_role("form", name="theme")).to_be_visible()
        expect(self.page.get_by_role("region", name="theme")).to_have_count(0)
        self.page.get_by_role("button", name="Concluir edição").click()
        expect(self.page.get_by_role("form", name="theme")).to_have_count(0)

    def test_reader_mode_has_no_edit_button(self):
        self.theme(query="?mode=reader")
        expect(self.page.get_by_role("button", name="Editar dados do tema")).to_have_count(0)
        expect(self.page.get_by_role("region", name="theme")).to_contain_text("Uma API")

    def test_the_themes_list_is_a_table_per_front_and_a_row_opens_the_theme(self):
        self.page.goto(self.base + "/themes/")
        row = self.page.locator('#front-api-platform tr[data-theme="PHZ-0001"]')
        expect(row).to_contain_text("Business Messaging API")
        expect(row).to_contain_text("Contrato fechado")
        expect(row).to_contain_text("#china")
        expect(row.locator(".badge")).to_have_text("No prazo")
        self.assertEqual(self.page.locator("#front-api-platform thead th").all_text_contents(),
                         ["Tema", "Tipo", "Status", "Etapa", "Responsável", "Conclusão estimada", "Etiquetas"])
        row.locator("td").first.click()
        expect(self.page).to_have_url(self.base + "/themes/PHZ-0001/")


if __name__ == "__main__":
    unittest.main()
