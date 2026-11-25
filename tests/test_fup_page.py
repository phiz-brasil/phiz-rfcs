"""The FUP pages (docs/spec/v2/fup.md): /fup/ and /fup/<id>/, against tests/fake_themes.py."""
import re
import sys
import unittest
from pathlib import Path

from playwright.sync_api import expect

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import SiteCase  # noqa: E402


class FupPageTest(SiteCase):
    def setUp(self):
        super().setUp()
        db = self.db
        db.seed_theme("PHZ-0001", "api-platform", title={"pt": "Business Messaging API"}, status="on_track", what_it_is={"pt": "A API para empresas"})
        db.seed_theme("PHZ-0004", "pop", title={"pt": "Evolução da OpenPlatform"}, status="at_risk")
        db.seed_theme("PHZ-0009", "outros", kind="task", title={"pt": "PhizShop e vendas via live"})
        db.seed_theme("PHZ-0006", "payments", title={"pt": "Checkout global"}, status="done")
        self.point = db.seed_decision("PHZ-0001", {"pt": "A validar: janela de 24h"})

    def sign(self, name="Pedro"):
        self.prefs()
        self.page.get_by_label("Seu nome").fill(name)
        self.page.keyboard.press("Escape")

    def meeting(self, agenda=None):
        agenda = agenda or [{"theme": t, "kind": k, "on": True, "star": False} for t, k in (("PHZ-0004", "discuss"), ("PHZ-0001", "decide"), ("PHZ-0009", "inform"))]
        fid = self.db.save_fup(None, {"title": "FUP 25/nov", "held_on": "2026-11-25", "agenda": agenda}, "Pedro")["id"]
        self.page.goto(self.base + f"/fup/{fid}/")
        expect(self.page.locator("h1")).to_contain_text("FUP 25/nov")
        self.sign()
        return fid

    def present(self):
        self.page.get_by_role("tab", name="Apresentação").click()

    def test_a_new_fup_starts_with_the_suggested_agenda(self):
        self.page.goto(self.base + "/fup/")
        self.sign()
        self.page.get_by_label("Título").fill("FUP Gustavo")
        self.page.get_by_role("button", name="Criar FUP").click()
        self.page.wait_for_url(re.compile(r"/fup/[0-9a-f-]{36}/$"))
        f = self.db.fups[0]
        self.assertEqual(f["title"], "FUP Gustavo")
        rows = {a["theme"]: (a["kind"], a["on"]) for a in f["agenda"]}
        self.assertEqual(rows, {"PHZ-0001": ("decide", True), "PHZ-0004": ("discuss", True), "PHZ-0009": ("inform", False)})
        expect(self.page.locator(".fup-row[data-theme='PHZ-0001']")).to_contain_text("0/1")
        expect(self.page.locator(".fup-row.off")).to_have_count(1)

    def test_the_agenda_switches_themes_and_kinds(self):
        self.meeting()
        row = self.page.locator(".fup-row[data-theme='PHZ-0009']")
        row.get_by_role("button", name="Na pauta").click()
        expect(row).to_have_class(re.compile(r"\boff\b"))
        row.get_by_label("Tipo de tratamento PHZ-0009").select_option("decide")
        row.get_by_role("button", name="Favoritar PHZ-0009").click()
        expect(row.get_by_role("button", name="Favoritar PHZ-0009")).to_have_attribute("aria-pressed", "true")
        a = next(x for x in self.db.fups[0]["agenda"] if x["theme"] == "PHZ-0009")
        self.assertEqual((a["on"], a["kind"], a["star"]), (False, "decide", True))

    def test_records_go_straight_to_the_theme(self):
        self.meeting()
        self.present()
        expect(self.page.locator(".fup-card h2")).to_contain_text("Evolução da OpenPlatform")
        self.page.keyboard.press("ArrowRight")
        expect(self.page.locator(".fup-card h2")).to_contain_text("Business Messaging API")
        cap = self.page.get_by_role("complementary", name="Registrar agora")
        cap.get_by_role("button", name="Em risco").click()
        expect(cap.get_by_role("button", name="Em risco")).to_have_attribute("aria-pressed", "true")
        self.assertEqual(self.db.themes["PHZ-0001"]["status"], "at_risk")
        cap.get_by_role("button", name="Decisão").click()
        cap.get_by_label("Texto").fill("A troca para a nova API é transparente")
        cap.get_by_role("button", name="Registrar", exact=True).click()
        expect(cap.locator(".fup-log li")).to_have_count(1)
        d = next(x for x in self.db.decisions if x["what"] == {"pt": "A troca para a nova API é transparente"})
        self.assertEqual((d["state"], d["decision"]), ("decided", {"pt": "A troca para a nova API é transparente"}))
        cap.get_by_role("button", name="Ação").click()
        cap.get_by_role("button", name="Doing").click()
        cap.get_by_label("Texto").fill("Definir a janela de 24h, Gleison")
        cap.get_by_label("Prazo").fill("2026-11-27")
        cap.get_by_role("button", name="Registrar", exact=True).click()
        expect(cap.locator(".fup-log li")).to_have_count(2)
        item = self.db.items[-1]
        self.assertEqual((item["theme_id"], item["title"], item["col"], item["due_date"]), ("PHZ-0001", "Definir a janela de 24h, Gleison", "doing", "2026-11-27"))
        cap.locator(".fup-log li").nth(1).locator(".fup-prog").click()
        expect(cap.locator(".fup-log li").nth(1).locator(".fup-prog")).to_have_text("Done")
        self.assertEqual(self.db.items[-1]["col"], "done")
        log = self.db.fups[0]["log"]
        self.assertEqual([(r["type"], r["progress"], r["ref"] is not None) for r in log], [("decision", "todo", True), ("action", "done", True)])

    def test_an_action_on_a_task_theme_becomes_an_open_decision(self):
        self.meeting()
        self.present()
        self.page.get_by_role("button", name="Próximo →").click()
        self.page.get_by_role("button", name="Próximo →").click()
        expect(self.page.locator(".fup-card h2")).to_contain_text("PhizShop")
        cap = self.page.get_by_role("complementary", name="Registrar agora")
        cap.get_by_role("button", name="Ação").click()
        cap.get_by_label("Texto").fill("Levantar quem usa o PhizShop")
        cap.get_by_role("button", name="Registrar", exact=True).click()
        expect(cap.locator(".fup-log li")).to_have_count(1)
        self.assertEqual(self.db.items, [])
        d = self.db.decisions[-1]
        self.assertEqual((d["theme_id"], d["what"], d["state"]), ("PHZ-0009", {"pt": "Levantar quem usa o PhizShop"}, "open"))

    def test_answering_a_point_decides_it(self):
        self.meeting()
        self.present()
        self.page.keyboard.press("ArrowRight")
        box = self.page.locator(".fup-points")
        expect(box).to_contain_text("A validar: janela de 24h")
        box.get_by_label(re.compile("Resposta")).fill("24h a partir da última mensagem do usuário")
        box.get_by_role("button", name="Marcar como respondido").click()
        expect(box.locator("li[data-done]")).to_have_count(1)
        self.assertEqual((self.point["state"], self.point["decision"]), ("decided", {"pt": "24h a partir da última mensagem do usuário"}))
        self.page.get_by_role("tab", name="Pauta").click()
        expect(self.page.locator(".fup-row[data-theme='PHZ-0001']")).to_contain_text("1/1")

    def test_the_minutes_and_closing(self):
        self.meeting()
        self.present()
        cap = self.page.get_by_role("complementary", name="Registrar agora")
        cap.get_by_label("Texto").fill("Diegão vê mini-apps e Pay")
        cap.get_by_role("button", name="Registrar", exact=True).click()
        expect(cap.locator(".fup-log li")).to_have_count(1)
        self.page.get_by_role("tab", name="Ata").click()
        ata = self.page.get_by_test_id("fup-minutes")
        expect(ata).to_contain_text("PHZ-0004 Evolução da OpenPlatform")
        expect(ata).to_contain_text("Nota [To do]: Diegão vê mini-apps e Pay")
        expect(ata).to_contain_text("A validar: janela de 24h")
        self.page.get_by_role("button", name="Fechar FUP").click()
        self.page.get_by_role("button", name="Fechar FUP").click()
        expect(self.page.locator(".fup-band")).to_contain_text("FUP fechado em")
        self.assertIsNotNone(self.db.fups[0]["closed_at"])
        self.assertEqual([(u["theme_id"], u["advanced"]) for u in self.db.updates], [("PHZ-0004", {"pt": "Diegão vê mini-apps e Pay"})])
        self.present()
        expect(self.page.get_by_role("button", name="Registrar", exact=True)).to_have_count(0)

    def test_the_menu_links_to_the_fup_and_the_page_reads_in_three_languages(self):
        self.page.goto(self.base + "/overview/")
        self.page.get_by_role("button", name=re.compile("Acompanhamento")).click()
        self.page.get_by_role("link", name="FUP", exact=True).click()
        self.page.wait_for_url(re.compile(r"/fup/$"))
        fid = self.db.save_fup(None, {"title": "FUP 25/nov", "held_on": "2026-11-25", "agenda": [{"theme": "PHZ-0001", "kind": "inform", "on": True, "star": False}]}, "Pedro")["id"]
        for lang, tabs in (("en", ("Agenda", "Presentation", "Minutes")), ("zh", ("议程", "演示", "会议纪要"))):
            self.page.evaluate(f"localStorage.setItem('phiz-rfc-lang', '{lang}')")
            self.page.goto(self.base + f"/fup/{fid}/")
            for name in tabs:
                expect(self.page.get_by_role("tab", name=name)).to_be_visible()

    def test_the_presentation_fits_a_phone(self):
        self.page.set_viewport_size({"width": 400, "height": 800})
        self.meeting()
        self.present()
        expect(self.page.locator(".fup-card h2")).to_be_visible()
        self.assertLessEqual(self.page.evaluate("document.documentElement.scrollWidth"), 400)


if __name__ == "__main__":
    unittest.main()
