"""Redesign, PR 2: the theme page in two columns, with the title, the properties and the deliveries edited where they are shown
(docs/spec/v2/redesign.md, "What PR 2 delivers"), against tests/fake_themes.py."""
import sys
import time
import unittest
from pathlib import Path

from playwright.sync_api import expect

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import SiteCase  # noqa: E402


class ThemeLayoutTest(SiteCase):
    def setUp(self):
        super().setUp()
        db = self.db
        db.seed_theme("PHZ-0001", "api-platform", title={"pt": "Business Messaging API"}, status="on_track", stage=3, owner="Gleison",
                      what_it_is={"pt": "Uma API"}, tags=["china"])
        db.seed_theme("PHZ-0010", "outros", kind="task", title={"pt": "Game Center"})

    def theme(self, tid="PHZ-0001", query=""):
        self.page.goto(self.base + f"/themes/{tid}/{query}")
        expect(self.page.locator("h1")).to_be_visible()

    def sign(self, name="Ana"):
        self.prefs()
        self.page.get_by_label("Seu nome").fill(name)
        self.page.keyboard.press("Escape")

    def props(self):
        return self.page.locator("aside.theme-side").get_by_role("region", name="Propriedades")

    def fields(self):
        return [e["field"] for e in self.db.events]

    def until(self, check, timeout=10.0):
        """Wait for a save to reach the fake database (the page may show the new text before the answer comes back)."""
        end = time.time() + timeout
        while time.time() < end:
            if check():
                return
            self.page.wait_for_timeout(100)
        self.fail("the change did not reach the database")

    # -- layout ---------------------------------------------------------------------------------------------------------------------------
    def test_the_properties_jira_and_attachments_are_in_the_right_column(self):
        self.theme()
        side = self.page.locator("aside.theme-side")
        expect(side.get_by_role("region", name="Propriedades")).to_be_visible()
        expect(side.locator("#sec-links")).to_have_count(1)
        expect(side.locator("#sec-attachments")).to_have_count(1)
        main = self.page.locator(".theme-main")
        for sec in ("#sec-summary", "#sec-updates", "#sec-records", "#sec-execution", "#sec-history"):
            expect(main.locator(sec)).to_have_count(1)

    def test_the_properties_show_the_phase_derived_from_the_stage(self):
        self.theme()
        box = self.props()
        expect(box.get_by_label("Status")).to_have_value("on_track")
        expect(box.get_by_label("Etapa")).to_have_value("3")
        expect(box.locator('[data-prop="phase"]')).to_contain_text("Definição")
        expect(box.get_by_label("Responsável")).to_have_value("Gleison")
        expect(box.locator('[data-prop="id"] dd')).to_have_text("PHZ-0001")
        self.theme("PHZ-0010")                                                                        # a task has no stage and no phase
        self.assertEqual(self.props().locator('[data-prop="stage"], [data-prop="phase"]').count(), 0)

    # -- header ---------------------------------------------------------------------------------------------------------------------------
    def test_the_title_is_edited_where_it_is_shown_and_writes_an_event(self):
        self.theme()
        self.sign()
        h1 = self.page.locator("h1")
        h1.fill("Business Messaging API v2")
        h1.press("Enter")
        self.until(lambda: self.db.themes["PHZ-0001"]["title"] == {"pt": "Business Messaging API v2"})
        expect(h1).to_have_text("Business Messaging API v2")
        self.assertEqual(self.fields(), ["title"])

    def test_what_it_is_is_edited_where_it_is_shown(self):
        self.theme()
        self.sign()
        what = self.page.locator('.theme-hero [data-edit="what_it_is"]')
        expect(what).to_have_text("Uma API")
        what.fill("Uma API para empresas falarem com clientes")
        what.blur()
        self.until(lambda: self.db.themes["PHZ-0001"]["what_it_is"] == {"pt": "Uma API para empresas falarem com clientes"})
        expect(what).to_have_text("Uma API para empresas falarem com clientes")

    def test_escape_and_an_empty_title_change_nothing(self):
        self.theme()
        self.sign()
        h1 = self.page.locator("h1")
        h1.fill("Outro nome")
        h1.press("Escape")
        expect(h1).to_have_text("Business Messaging API")
        h1.fill("   ")
        h1.press("Enter")
        expect(h1).to_have_text("Business Messaging API")
        self.assertEqual(self.db.themes["PHZ-0001"]["title"], {"pt": "Business Messaging API"})
        self.assertEqual(self.fields(), [])

    def test_without_a_name_the_title_goes_back_and_the_page_says_why(self):
        self.theme()
        h1 = self.page.locator("h1")
        h1.fill("Sem nome")
        h1.press("Enter")
        expect(self.page.get_by_role("alert").filter(has_text="Informe seu nome para salvar.")).to_be_visible()
        expect(h1).to_have_text("Business Messaging API")
        self.assertEqual(self.fields(), [])

    # -- properties -----------------------------------------------------------------------------------------------------------------------
    def test_each_property_saves_where_it_is_shown(self):
        self.theme()
        self.sign()
        box = self.props()
        box.get_by_label("Status").select_option("at_risk")
        expect(self.page.locator('[data-block="facts"] .badge')).to_have_text("Em risco")
        self.props().get_by_label("Responsável").fill("Luciana")
        self.props().get_by_label("Responsável").press("Enter")
        expect(self.page.locator('[data-block="facts"]')).to_contain_text("Luciana")
        self.props().get_by_label("Conclusão estimada").fill("2027-03-31")
        expect(self.page.locator('[data-block="facts"]')).to_contain_text("2027-03-31")
        self.props().get_by_label("Etapa").select_option("7")
        expect(self.props().locator('[data-prop="phase"]')).to_contain_text("Construção")
        t = self.db.themes["PHZ-0001"]
        self.until(lambda: t["stage"] == 7)
        self.assertEqual((t["status"], t["owner"], t["due_date"], t["stage"]), ("at_risk", "Luciana", "2027-03-31", 7))
        self.assertEqual(self.fields(), ["status", "owner", "due_date", "stage"])

    def test_reader_mode_shows_the_properties_and_the_title_as_text(self):
        self.theme(query="?mode=reader")
        box = self.props()
        expect(box).to_contain_text("No prazo")
        expect(box).to_contain_text("Gleison")
        self.assertEqual(box.locator("input, select").count(), 0)
        self.assertIsNone(self.page.locator("h1").get_attribute("contenteditable"))
        expect(self.page.locator(".theme-hero .theme-what")).to_have_text("Uma API")

    # -- deliveries -----------------------------------------------------------------------------------------------------------------------
    def test_deliveries_have_a_list_view_edited_in_place_and_remembered(self):
        self.theme()
        self.sign()
        box = self.page.get_by_role("region", name="Itens de execução")
        box.get_by_label("Novo item").fill("Mensagens para grupo")
        box.get_by_role("button", name="Adicionar item").click()
        expect(box.locator('[data-col="todo"] .item')).to_have_count(1)             # the board is the default view
        box.get_by_role("button", name="Lista", exact=True).click()
        row = box.locator("table.items-list tbody tr")
        expect(row).to_have_count(1)
        box.get_by_label("Coluna: Mensagens para grupo").select_option("doing")
        expect(box.locator('table.items-list tr[data-col="doing"]')).to_have_count(1)
        self.until(lambda: self.db.items[0]["col"] == "doing")
        box.get_by_label("Início: Mensagens para grupo").fill("2026-12-01")
        self.until(lambda: self.db.items[0]["start_date"] == "2026-12-01")
        box.get_by_label("Conclusão estimada: Mensagens para grupo").fill("2027-02-15")
        self.until(lambda: self.db.items[0]["due_date"] == "2027-02-15")
        box.get_by_label("Marco: Mensagens para grupo").check()
        self.until(lambda: self.db.items[0]["milestone"] is True)
        expect(box.get_by_label("Marco: Mensagens para grupo")).to_be_checked()
        name = box.get_by_label("Nome da entrega: Mensagens para grupo")
        name.fill("Mensagens para grupos")
        name.press("Enter")
        expect(box.get_by_label("Nome da entrega: Mensagens para grupos")).to_have_value("Mensagens para grupos")
        i = self.db.items[0]
        self.until(lambda: i["title"] == "Mensagens para grupos")
        self.assertEqual((i["title"], i["col"], i["start_date"], i["due_date"], i["milestone"]),
                         ("Mensagens para grupos", "doing", "2026-12-01", "2027-02-15", True))
        self.theme()                                                                       # the chosen view is remembered
        expect(self.page.locator("table.items-list")).to_be_visible()

    def test_a_delivery_cannot_start_after_it_ends(self):
        self.db.items.append({"id": "i1", "theme_id": "PHZ-0001", "title": "Go-live", "owner": None, "col": "todo", "start_date": None,
                              "due_date": "2026-12-10", "milestone": True, "created_at": "2026-11-01T00:00:00+00:00", "created_by": "Ana",
                              "updated_at": "2026-11-01T00:00:00+00:00"})
        self.theme()
        self.sign()
        box = self.page.get_by_role("region", name="Itens de execução")
        box.get_by_role("button", name="Lista", exact=True).click()
        box.get_by_label("Início: Go-live").fill("2026-12-20")
        expect(box.locator(".note[role=status]")).to_have_text("Não foi possível salvar.")
        self.assertIsNone(self.db.items[0]["start_date"])

    # -- urgency --------------------------------------------------------------------------------------------------------------------------
    def test_a_blocker_gets_an_urgency_when_added_and_it_changes_on_the_row(self):
        self.theme()
        self.sign()
        box = self.page.get_by_role("region", name="Bloqueios")
        form = box.locator("form")
        expect(form.get_by_label("Urgência", exact=True)).to_have_value("info")
        form.get_by_label("Exige a liderança").check()
        expect(form.get_by_label("Urgência", exact=True)).to_have_value("important")    # needing the leadership makes it important
        form.get_by_label("Urgência", exact=True).select_option("urgent")
        form.get_by_label("O que está bloqueado e por quê").fill("Contrato sem assinatura")
        form.get_by_role("button", name="Adicionar").click()
        row = box.locator('article[data-state="open"]')
        expect(row).to_have_count(1)
        self.assertEqual(self.db.blockers[0]["urgency"], "urgent")
        row.get_by_label("Urgência: Contrato sem assinatura").select_option("info")
        self.until(lambda: self.db.blockers[0]["urgency"] == "info")
        expect(box.get_by_label("Urgência: Contrato sem assinatura")).to_have_value("info")

    def test_a_decision_urgency_is_shown_as_text_in_reader_mode(self):
        self.db.seed_decision("PHZ-0001", {"pt": "Qual parceiro?"}, leadership=True)
        self.theme(query="?mode=reader")
        row = self.page.get_by_role("region", name="Decisões").locator('article[data-state="open"]')
        expect(row.locator(".urg")).to_have_text("Importante")
        self.assertEqual(row.locator("select").count(), 0)


if __name__ == "__main__":
    unittest.main()
