"""Phase 4: weekly updates, blockers and decisions, the executive view and reader mode (docs/spec/v2/domain.md), against tests/fake_themes.py."""
import re
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import expect

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import SiteCase  # noqa: E402


def this_week():
    y, w, _ = datetime.now(timezone.utc).isocalendar()
    return f"{y}-W{w:02d}"


class WeeklyTest(SiteCase):
    def setUp(self):
        super().setUp()
        db = self.db
        db.week = this_week()
        db.seed_theme("PHZ-0001", "api-platform", title={"pt": "Business Messaging API"}, status="on_track", stage=3, owner="Gleison", tags=["china"])
        db.seed_theme("PHZ-0002", "payments", title={"pt": "Migração CredPay"}, owner="Ana", due_date="2026-12-15")
        db.seed_theme("PHZ-0003", "payments", title={"pt": "Checkout global"}, status="done", stage=10, owner="Bo")
        db.seed_theme("PHZ-0010", "outros", kind="task", title={"pt": "Game Center"})

    def sign(self, name="Ana"):
        self.page.get_by_label("Seu nome").fill(name)

    def theme(self, tid="PHZ-0001"):
        self.page.goto(self.base + f"/themes/{tid}/")
        expect(self.page.locator("h1")).to_be_visible()

    # -- weekly update -------------------------------------------------------------
    def test_a_weekly_update_changes_the_progress_status_and_estimate_of_the_theme(self):
        self.theme("PHZ-0002")
        self.sign()
        box = self.page.get_by_role("region", name="Atualização semanal")
        box.get_by_label("Andamento (uma frase)").fill("Contrato fechado com a CredPay")
        box.get_by_label("O que avançou").fill("Fechamos o contrato e o escopo da ponte.")
        box.get_by_label("Próximo passo").fill("Pilotar o PIX")
        box.get_by_label("Status").select_option("at_risk")
        box.get_by_label("Conclusão estimada").fill("2026-12-20")
        box.get_by_label("Por que a previsão mudou?").fill("Dependência da CredPay")
        box.get_by_role("button", name="Publicar atualização").click()
        expect(box.locator("article")).to_have_count(1)
        fn, body = self.db.calls[-1]
        self.assertEqual(fn, "post_theme_update")
        self.assertEqual(body["p"], {"progress": {"pt": "Contrato fechado com a CredPay"}, "status": "at_risk", "advanced": {"pt": "Fechamos o contrato e o escopo da ponte."},
                                     "next_step": {"pt": "Pilotar o PIX"}, "due_date": "2026-12-20", "due_reason": "Dependência da CredPay"})
        t = self.db.themes["PHZ-0002"]
        self.assertEqual((t["status"], t["due_date"], t["progress"]), ("at_risk", "2026-12-20", {"pt": "Contrato fechado com a CredPay"}))
        self.assertEqual([e["field"] for e in self.db.events], ["update_posted", "status", "due_date"])
        row = self.db.updates[0]
        self.assertEqual((row["status_from"], row["status_to"], row["due_from"], row["due_to"], row["week"]), ("not_started", "at_risk", "2026-12-15", "2026-12-20", self.db.week))
        text = box.locator("article").inner_text()
        self.assertIn("Contrato fechado com a CredPay", text)
        self.assertIn("Não iniciado → Em risco", text)
        self.assertIn("2026-12-15 → 2026-12-20 (Dependência da CredPay)", text)

    def test_the_estimate_reason_only_asks_when_the_date_changes_and_unchanged_values_are_not_sent(self):
        self.theme("PHZ-0002")
        self.sign()
        box = self.page.get_by_role("region", name="Atualização semanal")
        self.assertEqual(box.get_by_label("Por que a previsão mudou?").count(), 0)
        box.get_by_label("Conclusão estimada").fill("2026-12-30")
        expect(box.get_by_label("Por que a previsão mudou?")).to_be_visible()
        box.get_by_label("Conclusão estimada").fill("2026-12-15")                 # back to the original
        self.assertEqual(box.get_by_label("Por que a previsão mudou?").count(), 0)
        box.get_by_label("Andamento (uma frase)").fill("Sem novidades")
        box.get_by_role("button", name="Publicar atualização").click()
        expect(box.locator("article")).to_have_count(1)
        self.assertNotIn("due_date", self.db.calls[-1][1]["p"])
        self.assertEqual(self.db.updates[0]["status_to"], None)                     # the status did not change either

    def test_the_progress_sentence_and_a_name_are_required(self):
        self.theme()
        box = self.page.get_by_role("region", name="Atualização semanal")
        box.get_by_role("button", name="Publicar atualização").click()
        expect(box.locator(".note[role=status]")).to_have_text("Escreva a frase de andamento.")
        box.get_by_label("Andamento (uma frase)").fill("Algo")
        box.get_by_role("button", name="Publicar atualização").click()
        expect(box.locator(".note[role=status]")).to_have_text("Informe seu nome para salvar.")
        self.assertEqual(self.db.calls, [])

    def test_an_update_is_written_in_the_language_of_the_page_and_history_is_kept(self):
        self.db.seed_update("PHZ-0001", week="2026-W40", progress={"pt": "Começamos"}, by="Bo")
        self.theme()
        self.sign()
        self.page.get_by_role("button", name="EN-US").click()
        box = self.page.get_by_role("region", name="Weekly update")
        box.get_by_label("Progress (one sentence)").fill("Contract signed")
        box.get_by_role("button", name="Post update").click()
        expect(box.locator("article")).to_have_count(2)
        self.assertEqual(self.db.updates[-1]["progress"], {"en": "Contract signed"})
        self.assertEqual(self.db.themes["PHZ-0001"]["progress"], {"en": "Contract signed"})
        expect(box.locator("article").first).to_contain_text("Contract signed")              # the newest first
        expect(box.locator("article").nth(1)).to_contain_text("Começamos")                   # the old one stays, with its language tag
        expect(box.locator("article").nth(1).locator(".from")).to_have_text("PT")

    # -- blockers and decisions -----------------------------------------------------
    def test_a_blocker_is_recorded_flagged_for_leadership_and_resolved(self):
        self.theme()
        self.sign()
        box = self.page.get_by_role("region", name="Bloqueios")
        box.get_by_label("O que está bloqueado e por quê").fill("Aprovação jurídica pendente")
        box.get_by_label("Quem resolve").fill("Jurídico")
        box.get_by_label("Até quando").fill("2026-12-05")
        box.get_by_label("Exige a liderança").check()
        box.get_by_role("button", name="Adicionar").click()
        row = box.locator('article[data-state="open"]')
        expect(row).to_have_count(1)
        expect(row).to_contain_text("Aprovação jurídica pendente")
        expect(row.locator(".flag.lead")).to_have_text("Exige a liderança")
        b = self.db.blockers[0]
        self.assertEqual((b["what"], b["owner"], b["due_date"], b["needs_leadership"]), ({"pt": "Aprovação jurídica pendente"}, "Jurídico", "2026-12-05", True))
        row.get_by_role("button", name="Resolver").click()
        row.get_by_label("Como foi resolvido").fill("Parecer recebido")
        row.get_by_role("button", name="Resolver").click()
        expect(box.locator('article[data-state="open"]')).to_have_count(0)
        expect(box.locator("details summary")).to_have_text("Resolvidos (1)")
        self.assertEqual((self.db.blockers[0]["state"], self.db.blockers[0]["how_resolved"]), ("resolved", {"pt": "Parecer recebido"}))
        self.assertEqual([e["field"] for e in self.db.events], ["blocker_added", "blocker_resolved"])

    def test_a_decision_can_be_decided_or_dropped(self):
        self.theme()
        self.sign()
        box = self.page.get_by_role("region", name="Decisões")
        for what in ("Usar o parceiro A?", "Adiar o piloto?"):
            box.get_by_label("O que precisa ser decidido").fill(what)
            box.get_by_label("Quem decide").fill("Pedro")
            box.get_by_role("button", name="Adicionar").click()
            expect(box.get_by_text(what)).to_be_visible()
        first = box.locator('article[data-state="open"]').filter(has_text="Usar o parceiro A?")
        first.get_by_role("button", name="Decidir").click()
        first.get_by_label("A decisão").fill("Sim, parceiro A")
        first.get_by_role("button", name="Decidir").click()
        second = box.locator('article[data-state="open"]').filter(has_text="Adiar o piloto?")
        second.get_by_role("button", name="Decidir").click()
        second.get_by_role("button", name="Descartar").click()
        expect(box.locator('article[data-state="open"]')).to_have_count(0)
        self.assertEqual([(d["state"], d["decision"]) for d in self.db.decisions], [("decided", {"pt": "Sim, parceiro A"}), ("dropped", {})])
        self.assertEqual([e["field"] for e in self.db.events][-2:], ["decision_decided", "decision_dropped"])

    def test_a_decision_needs_the_text_of_the_decision_to_be_decided(self):
        self.db.seed_decision("PHZ-0001", {"pt": "Qual parceiro?"})
        self.theme()
        self.sign()
        row = self.page.get_by_role("region", name="Decisões").locator("article").first
        row.get_by_role("button", name="Decidir").click()
        row.get_by_role("button", name="Decidir").click()
        expect(self.page.get_by_role("region", name="Decisões").locator(".note[role=status]")).to_have_text("Não foi possível salvar.")
        self.assertEqual(self.db.decisions[0]["state"], "open")

    def test_items_can_be_milestones_with_a_date(self):
        self.theme()
        self.sign()
        box = self.page.get_by_role("region", name="Itens de execução")
        box.get_by_label("Novo item").fill("Go-live do piloto")
        box.get_by_label("Até quando").fill("2026-12-10")
        box.get_by_label("Marcos").check()
        box.get_by_role("button", name="Adicionar item").click()
        expect(box.locator(".item")).to_contain_text("◆ Go-live do piloto")
        self.assertEqual((self.db.items[0]["milestone"], self.db.items[0]["due_date"]), (True, "2026-12-10"))

    # -- executive view -----------------------------------------------------------
    def executive(self):
        self.page.goto(self.base + "/executive/")
        expect(self.page.locator(".card-li").first).to_be_visible()

    def test_the_executive_view_groups_by_front_and_shows_what_matters(self):
        self.db.seed_update("PHZ-0001", progress={"pt": "Contrato fechado"})
        self.db.themes["PHZ-0001"]["progress"] = {"pt": "Contrato fechado"}
        self.db.items.append({"id": "i1", "theme_id": "PHZ-0001", "title": "Go-live", "owner": None, "col": "todo", "due_date": "2026-12-10", "milestone": True,
                              "created_at": "2026-11-01T00:00:00+00:00", "created_by": "Ana", "updated_at": "2026-11-01T00:00:00+00:00"})
        self.executive()
        page = self.page
        self.assertEqual(page.locator(".front > h2").all_inner_texts(), ["POP", "API Platform", "Mini-Apps", "Payments", "Product Center", "Outros"])
        card = page.locator('[data-theme="PHZ-0001"]')
        expect(card).to_contain_text("Business Messaging API")
        expect(card.locator("p.progress")).to_have_text("Contrato fechado")
        expect(card).to_contain_text("Gleison")
        expect(card.locator(".badge")).to_have_text("No prazo")
        expect(card).to_contain_text("◆ Go-live 2026-12-10")
        self.assertEqual(card.locator(".flag").count(), 0)                                     # updated this week: no flag
        expect(page.locator('[data-theme="PHZ-0002"] .flag')).to_have_text("sem atualização esta semana")
        self.assertEqual(page.locator('[data-theme="PHZ-0003"] .flag').count(), 0)             # done themes are not chased
        page.locator('[data-theme="PHZ-0001"] a.card').click()
        page.wait_for_url(re.compile(r"/themes/PHZ-0001/$"))

    def test_what_needs_the_leadership_is_on_top_and_links_to_the_theme(self):
        self.db.seed_blocker("PHZ-0002", {"pt": "Jurídico não aprovou"}, leadership=True, owner="Jurídico", due_date="2026-12-01")
        self.db.seed_decision("PHZ-0001", {"pt": "Qual parceiro?"}, leadership=True, decider="Pedro")
        self.db.seed_blocker("PHZ-0003", {"pt": "Detalhe interno"})                              # not for the leadership
        self.db.seed_blocker("PHZ-0003", {"pt": "Já resolvido"}, leadership=True, state="resolved")
        self.executive()
        items = self.page.get_by_role("region", name="Exige a liderança").locator("li")
        self.assertEqual(items.count(), 2)
        expect(items.nth(0)).to_contain_text("Jurídico não aprovou")                             # earliest deadline first
        expect(items.nth(0)).to_contain_text("PHZ-0002")
        expect(items.nth(1)).to_contain_text("Qual parceiro?")
        items.nth(0).get_by_role("link").click()
        self.page.wait_for_url(re.compile(r"/themes/PHZ-0002/$"))

    def test_the_executive_view_says_when_nothing_needs_the_leadership(self):
        self.executive()
        expect(self.page.get_by_text("Nada exige a liderança agora.")).to_be_visible()

    def test_open_blockers_and_decisions_are_counted_on_each_theme(self):
        self.db.seed_blocker("PHZ-0002", {"pt": "A"})
        self.db.seed_blocker("PHZ-0002", {"pt": "B"})
        self.db.seed_decision("PHZ-0002", {"pt": "C"})
        self.executive()
        card = self.page.locator('[data-theme="PHZ-0002"]')
        expect(card).to_contain_text("2 bloqueios abertos")
        expect(card).to_contain_text("1 decisões abertas")

    def test_the_executive_view_filters_by_status_tag_owner_and_attention(self):
        self.db.seed_update("PHZ-0001")
        self.db.seed_update("PHZ-0002")
        self.db.themes["PHZ-0002"]["status"] = "at_risk"
        self.executive()
        page = self.page
        page.get_by_role("group", name="Status").get_by_role("button", name="Em risco").click()
        self.assertEqual([c.get_attribute("data-theme") for c in page.locator(".card-li").all()], ["PHZ-0002"])
        page.get_by_role("group", name="Status").get_by_role("button", name="Todos").click()
        page.get_by_label("Etiqueta").select_option("china")
        self.assertEqual([c.get_attribute("data-theme") for c in page.locator(".card-li").all()], ["PHZ-0001"])
        page.get_by_label("Etiqueta").select_option("")
        page.get_by_label("Responsável").select_option("Bo")
        self.assertEqual([c.get_attribute("data-theme") for c in page.locator(".card-li").all()], ["PHZ-0003"])
        page.get_by_label("Responsável").select_option("")
        page.get_by_label("Só o que pede atenção").check()
        self.assertEqual([c.get_attribute("data-theme") for c in page.locator(".card-li").all()], ["PHZ-0002", "PHZ-0010"])      # at risk; and the one with no update

    def test_the_executive_view_is_translated_and_marks_machine_translations(self):
        self.db.themes["PHZ-0001"]["progress"] = {"pt": "Contrato fechado"}
        self.db.machine_translate("PHZ-0001", "progress", "en", "Contract closed")
        self.executive()
        self.page.get_by_role("button", name="EN-US").click()
        expect(self.page.locator("h1")).to_have_text("Executive view")
        expect(self.page.locator('[data-theme="PHZ-0001"] p.progress')).to_contain_text("Contract closed")
        expect(self.page.locator('[data-theme="PHZ-0001"] p.progress .from.auto')).to_have_text("auto")
        expect(self.page.get_by_text("Nothing needs leadership now.")).to_be_visible()

    # -- reader mode ---------------------------------------------------------------
    def test_reader_mode_hides_every_control_and_is_remembered(self):
        self.db.seed_blocker("PHZ-0001", {"pt": "Aprovação"}, leadership=True)
        self.page.goto(self.base + "/themes/")
        expect(self.page.get_by_role("button", name="＋ Novo tema")).to_be_visible()
        self.page.get_by_role("button", name="Modo leitor").click()
        expect(self.page.get_by_role("button", name="Modo edição")).to_have_attribute("aria-pressed", "true")
        self.assertEqual(self.page.get_by_role("button", name="＋ Novo tema").count(), 0)
        self.assertEqual(self.page.get_by_role("button", name="Editar frentes").count(), 0)
        self.assertEqual(self.page.get_by_label("Seu nome").count(), 0)
        self.page.goto(self.base + "/themes/PHZ-0001/")                                          # remembered across pages and reloads
        expect(self.page.get_by_role("button", name="Modo edição")).to_be_visible()
        expect(self.page.get_by_role("region", name="Bloqueios")).to_contain_text("Aprovação")
        self.assertEqual(self.page.locator("form").count(), 0)                                   # no forms at all
        self.assertEqual(self.page.locator("textarea, select").count(), 0)
        self.assertEqual(self.page.get_by_role("button", name=re.compile("Salvar|Adicionar|Resolver|Publicar")).count(), 0)
        self.assertEqual(self.page.locator(".moves").count(), 0)
        self.page.goto(self.base + "/executive/")
        expect(self.page.get_by_role("button", name="Modo edição")).to_be_visible()
        self.page.get_by_role("button", name="Modo edição").click()
        self.page.goto(self.base + "/themes/PHZ-0001/")
        expect(self.page.get_by_role("button", name="Salvar")).to_be_visible()

    def test_reader_mode_shows_the_texts_of_the_theme_as_read_only(self):
        self.db.themes["PHZ-0001"].update(problem={"pt": "Integração lenta"}, solution={"pt": "API pública"}, success={"pt": "10 clientes"})
        self.page.goto(self.base + "/themes/PHZ-0001/?mode=reader")
        panel = self.page.get_by_role("region", name="theme")
        expect(panel).to_contain_text("Integração lenta")
        expect(panel).to_contain_text("API pública")
        expect(panel).to_contain_text("10 clientes")
        expect(panel).to_contain_text("API Platform")
        self.assertEqual(self.page.locator("input").count(), 0)
        expect(self.page.get_by_role("region", name="Links do Jira")).to_be_visible()

    def test_a_link_can_open_edit_mode_even_when_reader_mode_was_remembered(self):
        self.page.goto(self.base + "/themes/PHZ-0001/?mode=reader")
        expect(self.page.get_by_role("button", name="Modo edição")).to_be_visible()
        self.page.goto(self.base + "/themes/PHZ-0001/?mode=edit")
        expect(self.page.get_by_role("button", name="Salvar")).to_be_visible()

    def test_the_index_links_to_the_executive_view(self):
        self.page.goto(self.base + "/")
        self.page.get_by_role("link", name="Visão executiva").click()
        self.page.wait_for_url(re.compile(r"/executive/$"))


if __name__ == "__main__":
    unittest.main()
