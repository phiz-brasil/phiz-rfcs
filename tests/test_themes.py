"""Phase 3: fronts, themes and execution items (docs/spec/v2/domain.md), against the fake Supabase of tests/fake_themes.py."""
import json
import re
import sys
import unittest
from pathlib import Path

from playwright.sync_api import expect

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import SiteCase, import_rfc  # noqa: E402


class ThemesTest(SiteCase):
    def setUp(self):
        super().setUp()
        db = self.db
        db.seed_theme("PHZ-0001", "api-platform", title={"pt": "Business Messaging API", "en": "Business Messaging API"}, status="on_track", stage=3, owner="Gleison")
        db.seed_theme("PHZ-0002", "payments", title={"pt": "Migração CredPay"}, tags=["china"], due_date="2026-12-15")
        db.seed_theme("PHZ-0010", "outros", kind="task", title={"pt": "Game Center"})

    def tform(self):
        return self.page.get_by_role("form", name="theme")             # the theme's own form (the weekly update has fields with the same labels)

    def themes(self):
        self.page.goto(self.base + "/themes/")
        expect(self.page.locator(".card-li").first).to_be_visible()
        return self.page

    def sign(self, name="Ana"):
        self.prefs()
        self.page.get_by_label("Seu nome").fill(name)
        self.page.keyboard.press("Escape")

    # -- the list ----------------------------------------------------------------
    def test_themes_are_listed_by_front_in_order_with_outros_last(self):
        page = self.themes()
        names = page.locator(".front > h2").all_inner_texts()
        self.assertEqual(names, ["POP", "API Platform", "Mini-Apps", "Payments", "Product Center", "Outros"])
        self.assertEqual(page.locator("#front-payments .card-li").count(), 1)
        self.assertEqual(page.locator("#front-api-platform .card-li").first.inner_text().split("\n")[0], "PHZ-0001")
        expect(page.locator("#front-pop .empty")).to_be_visible()
        expect(page.locator('[data-theme="PHZ-0002"] .tag')).to_have_text("#china")

    def test_the_language_changes_labels_and_names(self):
        page = self.themes()
        expect(page.locator("h1")).to_have_text("Temas")
        self.prefs()
        page.get_by_role("button", name="EN-US").click()
        page.keyboard.press("Escape")
        expect(page.locator("h1")).to_have_text("Themes")
        expect(page.locator("#front-outros > h2")).to_have_text("Outros")           # the front's English name is in the data
        expect(page.locator('[data-theme="PHZ-0001"] .badge')).to_have_text("On track")
        expect(page.locator('[data-theme="PHZ-0002"] h3')).to_contain_text("Migração CredPay")      # only written in Portuguese: shown with its language tag
        expect(page.locator('[data-theme="PHZ-0002"] h3 .from')).to_have_text("PT")

    def test_filters_by_type_and_status(self):
        page = self.themes()
        page.get_by_role("group", name="Tipo").get_by_role("button", name="Tarefa avulsa").click()
        self.assertEqual(page.locator(".card-li").count(), 1)
        page.get_by_role("group", name="Tipo").get_by_role("button", name="Todos").click()
        page.get_by_role("group", name="Status").get_by_role("button", name="No prazo").click()
        self.assertEqual(page.locator(".card-li").all_inner_texts()[0].split("\n")[0], "PHZ-0001")
        self.assertEqual(page.locator(".card-li").count(), 1)

    def test_a_new_theme_needs_a_name_and_opens_its_page(self):
        page = self.themes()
        page.get_by_role("button", name="＋ Novo tema").click()
        form = page.get_by_role("form", name="Novo tema")
        form.get_by_label(re.compile("^Título")).fill("Mini-app de pagamentos")
        form.get_by_role("button", name="Criar").click()
        expect(form.locator(".note")).to_have_text("Informe seu nome para salvar.")
        self.assertEqual(self.db.calls, [])
        self.sign()
        form.get_by_label("Tipo").select_option("project")
        form.get_by_label("Frente").select_option("mini-apps")
        form.get_by_role("button", name="Criar").click()
        page.wait_for_url(re.compile(r"/themes/PHZ-\d{4}/$"))
        fn, body = self.db.calls[-1]
        self.assertEqual(fn, "create_theme")
        self.assertEqual((body["p"]["kind"], body["p"]["front"], body["p"]["title"], body["p_by"]), ("project", "mini-apps", {"pt": "Mini-app de pagamentos"}, "Ana"))
        expect(page.locator("h1")).to_have_text("Mini-app de pagamentos")

    def test_the_front_of_a_theme_can_be_changed_and_is_remembered(self):
        self.page.goto(self.base + "/themes/PHZ-0002/")
        expect(self.page.locator("h1")).to_have_text("Migração CredPay")
        self.sign("Ana")
        self.tform().get_by_label("Frente").select_option("pop")
        self.page.get_by_role("button", name="Salvar").click()
        expect(self.page.locator(".note[role=status]").first).to_have_text("Salvo.")
        fn, body = self.db.calls[-1]
        self.assertEqual((fn, body["p_id"], body["p"]), ("update_theme", "PHZ-0002", {"front": "pop"}))      # only what changed
        self.assertEqual(self.db.themes["PHZ-0002"]["front"], "pop")
        self.assertEqual(self.db.events[-1]["field"], "front")
        self.assertEqual((self.db.events[-1]["old_value"], self.db.events[-1]["new_value"], self.db.events[-1]["edited_by"]), ("payments", "pop", "Ana"))
        self.page.goto(self.base + "/themes/")
        expect(self.page.locator("#front-pop .card-li")).to_have_count(1)
        expect(self.page.locator("#front-payments .card-li")).to_have_count(0)

    def test_the_fronts_can_be_edited_but_outros_stays_last(self):
        page = self.themes()
        self.sign()
        page.get_by_role("button", name="Editar frentes").click()
        form = page.get_by_role("form", name="Editar frentes: payments")
        form.get_by_label("Nome da frente (EN)").fill("Payments & Checkout")
        form.get_by_label("Ordem").fill("2")
        form.get_by_role("button", name="Salvar").click()
        expect(form.locator(".note")).to_have_text("Salvo.")
        fr = next(f for f in self.db.fronts if f["key"] == "payments")
        self.assertEqual((fr["name"]["en"], fr["ord"]), ("Payments & Checkout", 2))
        self.assertEqual(page.get_by_role("form", name="Editar frentes: outros").get_by_label("Ordem").count(), 0)   # Outros has no order

    # -- a theme ---------------------------------------------------------------
    def test_text_is_written_per_language_and_the_other_languages_are_kept(self):
        self.page.goto(self.base + "/themes/PHZ-0001/")
        self.sign()
        self.tform().get_by_label("Andamento (uma frase)").fill("Contrato fechado com o parceiro")
        self.page.get_by_role("button", name="Salvar").click()
        expect(self.page.locator(".note[role=status]").first).to_have_text("Salvo.")
        self.assertEqual(self.db.themes["PHZ-0001"]["progress"], {"pt": "Contrato fechado com o parceiro"})
        self.prefs()
        self.page.get_by_role("button", name="EN-US").click()
        self.page.keyboard.press("Escape")
        expect(self.tform().get_by_label("Progress (one sentence)")).to_have_attribute("placeholder", "Contrato fechado com o parceiro")
        self.tform().get_by_label("Progress (one sentence)").fill("Contract closed with the partner")
        self.page.get_by_role("button", name="Save").click()
        expect(self.page.locator(".note[role=status]").first).to_have_text("Saved.")
        self.assertEqual(self.db.themes["PHZ-0001"]["progress"], {"pt": "Contrato fechado com o parceiro", "en": "Contract closed with the partner"})

    def test_machine_translations_are_marked_and_a_correction_makes_them_a_person_text(self):
        self.db.themes["PHZ-0001"]["progress"] = {"pt": "Contrato fechado"}
        self.db.machine_translate("PHZ-0001", "progress", "en", "Contract closed")
        self.page.goto(self.base + "/themes/PHZ-0001/")
        self.sign()
        self.prefs()
        self.page.get_by_role("button", name="EN-US").click()
        self.page.keyboard.press("Escape")
        field = self.tform().get_by_label("Progress (one sentence)")
        expect(field).to_have_value("Contract closed")
        expect(self.page.locator(".field .from.auto")).to_have_text("machine translation")
        field.fill("Contract signed")
        self.page.get_by_role("button", name="Save").click()
        expect(self.page.locator(".note[role=status]").first).to_have_text("Saved.")
        self.assertEqual(self.db.themes["PHZ-0001"]["progress"]["en"], "Contract signed")
        self.assertEqual(self.db.themes["PHZ-0001"]["text_meta"]["progress"], [])             # now written by a person: never overwritten
        expect(self.page.locator(".field .from.auto")).to_have_count(0)

    def test_the_list_marks_machine_translated_text(self):
        self.db.themes["PHZ-0001"]["progress"] = {"pt": "Contrato fechado"}
        self.db.machine_translate("PHZ-0001", "progress", "en", "Contract closed")
        self.themes()
        self.prefs()
        self.page.get_by_role("button", name="EN-US").click()
        self.page.keyboard.press("Escape")
        expect(self.page.locator('[data-theme="PHZ-0001"] p .from.auto')).to_have_text("auto")

    def test_status_stage_dates_owner_and_tags_are_saved(self):
        self.page.goto(self.base + "/themes/PHZ-0001/")
        self.sign()
        self.tform().get_by_label("Status").select_option("at_risk")
        self.tform().get_by_label("Etapa").select_option("5")
        self.tform().get_by_label("Conclusão estimada").fill("2026-12-20")
        self.tform().get_by_label("Etiquetas (separadas por vírgula)").fill("Mission China, #q1")
        self.page.get_by_role("button", name="Salvar").click()
        expect(self.page.locator(".note[role=status]").first).to_have_text("Salvo.")
        t = self.db.themes["PHZ-0001"]
        self.assertEqual((t["status"], t["stage"], t["due_date"], t["tags"]), ("at_risk", 5, "2026-12-20", ["Mission China", "q1"]))
        self.assertEqual({e["field"] for e in self.db.events}, {"status", "stage", "due_date", "tags"})
        expect(self.page.locator(".history li")).to_have_count(4)

    def test_a_task_has_no_stage_and_no_execution_items(self):
        self.page.goto(self.base + "/themes/PHZ-0010/")
        expect(self.page.locator("h1")).to_have_text("Game Center")
        self.assertEqual(self.tform().get_by_label("Etapa").count(), 0)
        self.assertEqual(self.page.get_by_role("region", name="Itens de execução").count(), 0)

    def test_execution_items_are_added_and_moved_between_columns(self):
        self.page.goto(self.base + "/themes/PHZ-0001/")
        self.sign()
        box = self.page.get_by_role("region", name="Itens de execução")
        box.get_by_label("Novo item").fill("Desenhar o contrato")
        box.get_by_role("button", name="Adicionar item").click()
        expect(box.locator('[data-col="todo"] .item')).to_have_count(1)
        box.get_by_role("button", name="Desenhar o contrato → Fazendo").click()
        expect(box.locator('[data-col="doing"] .item')).to_have_count(1)
        expect(box.locator('[data-col="todo"] .item')).to_have_count(0)
        self.assertEqual([e["field"] for e in self.db.events], ["item_created", "item_col"])
        self.assertEqual((self.db.events[-1]["old_value"], self.db.events[-1]["new_value"]), ("todo", "doing"))

    def test_jira_links_show_the_key_and_open_jira_in_another_tab(self):
        self.page.goto(self.base + "/themes/PHZ-0001/")
        self.sign()
        box = self.page.get_by_role("region", name="Links do Jira")
        box.get_by_label("Endereço do item no Jira (https://…)").fill("http://insecure.example/ABC-1")
        box.get_by_role("button", name="Adicionar").click()
        expect(box.locator(".note[role=status]")).to_have_text("Não foi possível salvar.")                   # https only
        box.get_by_label("Endereço do item no Jira (https://…)").fill("https://phizchat.atlassian.net/browse/PHZ-123")
        box.get_by_label("Rótulo (opcional)").fill("Epic")
        box.get_by_role("button", name="Adicionar").click()
        link = box.get_by_role("link", name="PHZ-123")
        expect(link).to_be_visible()
        self.assertEqual((link.get_attribute("href"), link.get_attribute("target"), link.get_attribute("rel")),
                         ("https://phizchat.atlassian.net/browse/PHZ-123", "_blank", "noopener noreferrer"))
        box.get_by_role("button", name="Remover").click()
        expect(box.get_by_role("link", name="PHZ-123")).to_have_count(0)
        self.assertEqual(self.db.jira, [])

    def test_dependencies_link_themes_of_different_fronts_both_ways(self):
        self.page.goto(self.base + "/themes/PHZ-0001/")
        self.sign()
        box = self.page.get_by_role("region", name="Dependências")
        box.get_by_label("Outro tema (PHZ-0000)").fill("phz-0002")
        box.get_by_role("button", name="Adicionar").click()
        expect(box.get_by_role("link", name=re.compile("PHZ-0002"))).to_be_visible()
        self.page.goto(self.base + "/themes/PHZ-0002/")
        expect(self.page.get_by_role("region", name="Dependências").get_by_role("link", name=re.compile("PHZ-0001"))).to_be_visible()
        self.page.goto(self.base + "/themes/PHZ-0001/")
        self.page.get_by_role("region", name="Dependências").get_by_role("button", name="Remover").click()
        expect(self.page.get_by_role("region", name="Dependências").get_by_text("Nada ainda.")).to_be_visible()

    def test_a_name_is_required_to_save_and_a_rate_limit_is_explained(self):
        self.page.goto(self.base + "/themes/PHZ-0001/")
        self.tform().get_by_label("Status").select_option("paused")
        self.page.get_by_role("button", name="Salvar").click()
        expect(self.page.locator(".note[role=status]").first).to_have_text("Informe seu nome para salvar.")
        self.assertEqual(self.db.calls, [])
        self.sign()
        self.db.rate_limited = True
        self.page.get_by_role("button", name="Salvar").click()
        expect(self.page.locator(".note[role=status]").first).to_have_text("Muitas alterações seguidas. Espere um minuto.")

    def test_the_theme_links_to_its_rfc_when_it_has_one(self):
        import_rfc(self.db, "PHZ-0002")
        self.page.goto(self.base + "/themes/PHZ-0002/")
        link = self.page.get_by_role("link", name=re.compile("Abrir a RFC"))
        self.assertEqual(link.get_attribute("href"), "/rfc/?id=PHZ-0002")
        self.page.goto(self.base + "/themes/PHZ-0010/")
        expect(self.page.get_by_text("Este tema ainda não tem RFC.")).to_be_visible()

    def test_the_rfc_page_shows_the_status_and_stage_of_its_theme(self):
        import_rfc(self.db, "PHZ-0002")
        self.db.themes["PHZ-0002"].update(status="at_risk", stage=5)
        self.page.goto(self.base + "/rfc/?id=PHZ-0002")
        self.page.wait_for_selector(".lang.active h2")
        badge = self.page.locator(".rfcno.theme-st")
        expect(badge).to_have_text(re.compile(r"em risco · 05 revisão da solução", re.I))
        self.assertEqual(badge.get_attribute("href"), "../themes/PHZ-0002/")
        self.assertEqual(self.page.locator(".st-btn").count(), 0)                  # the old picker is gone
        expect(self.page.locator(".lang.active .hero .pill")).to_have_text("Em risco · 05 Revisão da solução")
        self.page.get_by_role("button", name="EN-US").click()
        expect(self.page.locator(".lang.active .hero .pill")).to_have_text("At risk · 05 Solution review")
        badge.click()
        self.page.wait_for_url(re.compile(r"/themes/PHZ-0002/$"))

    def test_an_rfc_without_a_theme_keeps_the_old_status_picker(self):
        import_rfc(self.db, "PHZ-0001")                                             # seeded as a theme in setUp only for the list tests
        del self.db.themes["PHZ-0001"]
        self.page.goto(self.base + "/rfc/?id=PHZ-0001")
        self.page.wait_for_selector(".lang.active h2")
        expect(self.page.locator(".rfcno.st.st-btn")).to_be_visible()

    def test_an_unknown_theme_says_so(self):
        self.page.goto(self.base + "/themes/PHZ-9999/")
        expect(self.page.get_by_text("Tema não encontrado.")).to_be_visible()

    def test_the_index_links_to_the_themes(self):
        self.page.goto(self.base + "/")
        self.page.get_by_role("link", name="Temas").click()
        self.page.wait_for_url(re.compile(r"/themes/$"))


if __name__ == "__main__":
    unittest.main()
