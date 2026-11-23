"""Phase 5: the B2B board (V4 stages, configurable columns, gate checklist), against tests/fake_themes.py (docs/spec/v2/flow-and-metrics.md)."""
import sys
import unittest
from pathlib import Path

from playwright.sync_api import expect

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import SiteCase  # noqa: E402


class BoardTest(SiteCase):
    def setUp(self):
        super().setUp()
        db = self.db
        db.seed_theme("PHZ-0001", "api-platform", title={"pt": "Business Messaging API"}, status="on_track", stage=4, owner="Gleison", tags=["china"])
        db.seed_theme("PHZ-0002", "payments", title={"pt": "Migração CredPay"}, owner="Ana", stage=1)
        db.seed_theme("PHZ-0003", "payments", title={"pt": "Checkout global"}, stage=7, owner="Bo")
        db.seed_theme("PHZ-0010", "outros", kind="task", title={"pt": "Game Center"})
        db.seed_theme("PHZ-0011", "pop", title={"pt": "Bug de login"}, stage=6, route="bug", owner="Caio")

    def col(self, stage, n=0):
        return [c for c in sorted(self.db.columns, key=lambda c: c["position"]) if c["stage"] == stage][n]

    def board(self, query=""):
        self.page.goto(self.base + "/board/" + query)
        expect(self.page.locator("h1")).to_have_text("Quadro B2B")
        expect(self.page.locator("article.kcard").first).to_be_visible()

    def sign(self, name="Ana"):
        self.page.get_by_label("Seu nome").fill(name)

    def card(self, tid):
        return self.page.locator(f'article.kcard[data-theme="{tid}"]')

    def move(self, tid, label):
        self.card(tid).get_by_label(f"Mover para {tid}").select_option(label=label)

    def cfg(self):
        return self.page.get_by_role("region", name="Configurar colunas").get_by_role("status")

    def moves(self, tid):
        return [e for e in self.db.events if e["theme_id"] == tid and e["field"] == "move"]

    # -- the board ------------------------------------------------------------------
    def test_project_themes_are_cards_in_the_column_of_their_stage_and_tasks_are_not_on_the_board(self):
        self.board()
        for tid, stage in (("PHZ-0001", 4), ("PHZ-0002", 1), ("PHZ-0003", 7), ("PHZ-0011", 6)):
            expect(self.page.locator(f'.cell[data-column="{self.col(stage)["id"]}"] article[data-theme="{tid}"]')).to_have_count(1)
        expect(self.page.locator('article[data-theme="PHZ-0010"]')).to_have_count(0)
        expect(self.page.locator(".board .bhead")).to_have_count(10)
        # swimlanes follow the fixed order of the fronts and skip the fronts without projects
        self.assertEqual(self.page.locator(".lane h2").all_inner_texts(), ["POP", "API Platform", "Payments"])

    def test_the_board_is_as_wide_as_its_columns_even_with_very_long_titles(self):
        self.db.seed_theme("PHZ-0030", "pop", title={"pt": "Um título " + "muito comprido " * 30}, stage=3)
        self.board()
        width = self.page.locator(".boardwrap").evaluate("e => e.scrollWidth")
        self.assertLess(width, 10 * 250 + 9 * 8 + 80)                                   # ten fixed columns plus gaps and padding

    def test_a_card_shows_what_the_standard_asks_for(self):
        self.db.seed_blocker("PHZ-0001", {"pt": "Aguardando contrato"})
        self.db.seed_decision("PHZ-0001", {"pt": "Escolher fornecedor"})
        self.db.items.append({"id": "i1", "theme_id": "PHZ-0001", "title": "A", "owner": None, "col": "done", "due_date": None, "milestone": False, "created_at": "2026-11-01T00:00:00+00:00"})
        self.db.items.append({"id": "i2", "theme_id": "PHZ-0001", "title": "B", "owner": None, "col": "todo", "due_date": None, "milestone": False, "created_at": "2026-11-01T00:00:00+00:00"})
        self.db.jira.append({"id": "j1", "theme_id": "PHZ-0001", "item_id": None, "url": "https://jira.example.com/browse/PHZ-77", "label": None, "issue_key": "PHZ-77", "created_at": "x"})
        self.board()
        c = self.card("PHZ-0001")
        expect(c).to_contain_text("Business Messaging API")
        expect(c).to_contain_text("Gleison")
        expect(c).to_contain_text("1/2 itens feitos")
        expect(c).to_contain_text("PHZ-77")
        expect(c).to_contain_text("dias na etapa")
        expect(c.locator('[data-flag="blockers"]')).to_have_text("1 bloqueios abertos")
        expect(c.locator('[data-flag="decisions"]')).to_have_text("1 decisões abertas")
        expect(c.locator('[data-flag="jira"]')).to_have_count(0)
        self.assertEqual(c.locator("a.id").get_attribute("href"), "/themes/PHZ-0001/")

    def test_a_project_at_stage_04_or_later_without_a_jira_link_is_flagged(self):
        self.board()
        expect(self.card("PHZ-0001").locator('[data-flag="jira"]')).to_have_text("Sem link do Jira")
        expect(self.card("PHZ-0002").locator('[data-flag="jira"]')).to_have_count(0)    # stage 01: not yet expected

    # -- moving ---------------------------------------------------------------------
    def test_moving_a_card_to_the_next_stage_records_exactly_one_event_with_the_right_stages(self):
        self.board()
        self.sign()
        self.move("PHZ-0002", "02 Pesquisa")
        expect(self.page.get_by_role("status")).to_contain_text("Movido")
        expect(self.page.locator(f'.cell[data-column="{self.col(2)["id"]}"] article[data-theme="PHZ-0002"]')).to_have_count(1)
        ev = self.moves("PHZ-0002")
        self.assertEqual(len(ev), 1)
        v = ev[0]["new_value"]
        self.assertEqual((v["from_stage"], v["to_stage"], ev[0]["edited_by"]), (1, 2, "Ana"))
        self.assertEqual((v["from_column"], v["to_column"]), (self.col(1)["id"], self.col(2)["id"]))
        self.assertEqual(self.db.themes["PHZ-0002"]["stage"], 2)
        self.assertEqual(self.db.themes["PHZ-0002"]["board_column"], self.col(2)["id"])

    def test_a_move_inside_the_same_stage_changes_the_column_but_records_no_stage_change(self):
        extra = self.db.save_board_column(None, {"name": {"pt": "07 Revisão de código"}, "stage": 7}, "Ana")["id"]
        self.board()
        self.sign()
        self.move("PHZ-0003", "07 Revisão de código")
        expect(self.page.locator(f'.cell[data-column="{extra}"] article[data-theme="PHZ-0003"]')).to_have_count(1)
        ev = self.moves("PHZ-0003")
        self.assertEqual(len(ev), 1)
        self.assertEqual((ev[0]["new_value"]["from_stage"], ev[0]["new_value"]["to_stage"]), (7, 7))
        self.assertEqual(self.db.themes["PHZ-0003"]["stage"], 7)
        self.assertFalse([e for e in self.db.events if e["theme_id"] == "PHZ-0003" and e["field"] == "stage"])
        # and the days in stage do not restart: the same card is still in 07 since its creation
        expect(self.card("PHZ-0003")).to_contain_text("dias na etapa")

    def test_a_card_can_move_with_open_gates_and_the_open_gates_stay_on_the_event(self):
        self.board()
        expect(self.card("PHZ-0002").locator('[data-flag="gates"]')).to_contain_text("2 gates abertos")
        self.sign()
        self.move("PHZ-0002", "02 Pesquisa")
        expect(self.page.get_by_role("status")).to_contain_text("Movido com gates abertos")
        self.assertEqual(self.moves("PHZ-0002")[0]["new_value"]["open_gates"], ["01-triage", "01-owner"])
        expect(self.card("PHZ-0002").locator('[data-flag="gates"]')).to_contain_text("1 gates abertos")      # now the gates of 02

    def test_ticked_gates_are_not_recorded_as_open_on_a_move(self):
        self.db.gate_checks.append({"theme_id": "PHZ-0002", "gate_key": "01-triage", "evidence": "RFC §1", "checked_by": "Ana", "checked_at": "2026-11-20T00:00:00+00:00"})
        self.board()
        expect(self.card("PHZ-0002").locator('[data-flag="gates"]')).to_contain_text("1 gates abertos")
        self.sign()
        self.move("PHZ-0002", "02 Pesquisa")
        expect(self.page.get_by_role("status")).to_contain_text("Movido")
        self.assertEqual(self.moves("PHZ-0002")[0]["new_value"]["open_gates"], ["01-owner"])

    def test_non_waivable_gates_show_in_red(self):
        self.db.seed_theme("PHZ-0020", "pop", title={"pt": "Lançamento"}, stage=9)
        self.board()
        expect(self.card("PHZ-0020").locator('[data-flag="gates"]')).to_have_class("flag lead")
        expect(self.card("PHZ-0002").locator('[data-flag="gates"]')).to_have_class("flag")

    def test_skipping_a_stage_asks_for_a_reason_and_records_it(self):
        self.board()
        self.sign()
        self.move("PHZ-0002", "05 Revisão da solução")
        form = self.page.get_by_role("form", name="Motivo", exact=False)
        expect(form).to_be_visible()
        self.assertEqual(self.moves("PHZ-0002"), [])                                     # nothing happened yet
        expect(form.get_by_role("button", name="Confirmar movimento")).to_be_disabled()
        form.get_by_label("Motivo", exact=False).fill("Já aprovado pela diretoria")
        form.get_by_role("button", name="Confirmar movimento").click()
        expect(self.page.get_by_role("status")).to_contain_text("Movido")
        v = self.moves("PHZ-0002")[0]["new_value"]
        self.assertEqual((v["to_stage"], v["reason"]), (5, "Já aprovado pela diretoria"))
        self.assertEqual(self.db.themes["PHZ-0002"]["stage"], 5)

    def test_moving_back_needs_no_reason_and_is_recorded(self):
        self.board()
        self.sign()
        self.move("PHZ-0003", "06 Planejamento")
        expect(self.page.get_by_role("status")).to_contain_text("Movido")
        v = self.moves("PHZ-0003")[0]["new_value"]
        self.assertEqual((v["from_stage"], v["to_stage"], v["open_gates"], v["reason"]), (7, 6, [], None))

    def test_a_bug_route_theme_moves_to_the_next_stage_without_reason_but_leaving_the_route_needs_one(self):
        self.board()
        self.sign()
        self.move("PHZ-0011", "07 Desenvolvimento")                                      # 06 → 07 is the next stage of the bug route
        expect(self.page.get_by_role("status")).to_contain_text("Movido")
        self.move("PHZ-0011", "03 Decisão")                                              # intake stages are not part of the route
        expect(self.page.get_by_role("form", name="Motivo", exact=False)).to_be_visible()
        self.assertEqual(len(self.moves("PHZ-0011")), 1)

    def test_a_p0_theme_skips_nothing_by_going_from_07_to_08(self):
        self.db.seed_theme("PHZ-0012", "pop", title={"pt": "Incidente"}, stage=7, route="p0")
        self.board()
        self.sign()
        self.move("PHZ-0012", "08 Testes")
        expect(self.page.get_by_role("status")).to_contain_text("Movido")
        self.assertEqual(len(self.moves("PHZ-0012")), 1)

    def test_moving_needs_a_name(self):
        self.board()
        self.move("PHZ-0002", "02 Pesquisa")
        expect(self.page.get_by_role("status")).to_contain_text("Informe seu nome")
        self.assertEqual(self.moves("PHZ-0002"), [])

    def test_a_card_can_be_dragged_to_another_column(self):
        self.board()
        self.sign()
        self.card("PHZ-0002").drag_to(self.page.locator(f'.cell[data-column="{self.col(2)["id"]}"]').first)
        expect(self.page.locator(f'.cell[data-column="{self.col(2)["id"]}"] article[data-theme="PHZ-0002"]')).to_have_count(1)
        self.assertEqual(self.moves("PHZ-0002")[0]["new_value"]["to_stage"], 2)

    def test_the_stage_changed_on_the_theme_page_moves_the_card_to_the_first_column_of_that_stage(self):
        extra = self.db.save_board_column(None, {"name": {"pt": "03 Extra"}, "stage": 3, "position": 99}, "Ana")["id"]
        self.db.themes["PHZ-0002"]["board_column"] = extra               # in the extra column of 03...
        self.db.themes["PHZ-0002"]["stage"] = 3
        self.board()
        expect(self.page.locator(f'.cell[data-column="{extra}"] article[data-theme="PHZ-0002"]')).to_have_count(1)
        self.db.themes["PHZ-0002"]["stage"] = 5                          # ...and then someone sets the stage on the theme page
        self.board()
        expect(self.page.locator(f'.cell[data-column="{self.col(5)["id"]}"] article[data-theme="PHZ-0002"]')).to_have_count(1)

    # -- filters, WIP, reader mode ----------------------------------------------------
    def test_filters_by_front_tag_owner_status_blocked_and_aging(self):
        self.db.seed_blocker("PHZ-0003", {"pt": "Sem acesso"})
        self.board()
        shown = lambda: sorted(self.page.locator("article.kcard").evaluate_all("els => els.map(e => e.dataset.theme)"))  # noqa: E731
        self.assertEqual(shown(), ["PHZ-0001", "PHZ-0002", "PHZ-0003", "PHZ-0011"])
        self.page.get_by_label("Frente").select_option(label="Payments")
        self.assertEqual(shown(), ["PHZ-0002", "PHZ-0003"])
        self.page.get_by_label("Frente").select_option(label="Todos")
        self.page.get_by_label("Etiqueta").select_option(label="#china")
        self.assertEqual(shown(), ["PHZ-0001"])
        self.page.get_by_label("Etiqueta").select_option(label="Todos")
        self.page.get_by_label("Responsável").fill("ana")
        self.assertEqual(shown(), ["PHZ-0002"])
        self.page.get_by_label("Responsável").fill("")
        self.page.get_by_label("Status").select_option(label="No prazo")
        self.assertEqual(shown(), ["PHZ-0001"])
        self.page.get_by_label("Status").select_option(label="Todos")
        self.page.get_by_label("Só com bloqueio").check()
        self.assertEqual(shown(), ["PHZ-0003"])
        self.page.get_by_label("Só com bloqueio").uncheck()
        self.db.themes["PHZ-0001"]["created_at"] = "2026-01-01T00:00:00+00:00"
        self.board()
        self.page.get_by_label("Parados há mais de").select_option(label="30 dias")
        self.assertEqual(shown(), ["PHZ-0001"])

    def test_a_column_over_its_wip_limit_is_marked(self):
        self.db.save_board_column(self.col(1)["id"], {"wip_limit": 1}, "Ana")
        self.db.save_board_column(self.col(4)["id"], {"wip_limit": 3}, "Ana")
        self.db.seed_theme("PHZ-0021", "pop", title={"pt": "Outro"}, stage=1)
        self.board()
        over = self.page.locator(f'.bhead[data-column="{self.col(1)["id"]}"]')
        expect(over).to_have_attribute("data-over", "1")
        expect(over).to_contain_text("2 / 1")
        expect(self.page.locator(f'.bhead[data-column="{self.col(4)["id"]}"]')).to_have_attribute("data-over", "0")

    def test_reader_mode_shows_the_board_without_controls(self):
        self.board("?mode=reader")
        expect(self.card("PHZ-0002")).to_be_visible()
        expect(self.page.get_by_label("Mover para PHZ-0002")).to_have_count(0)
        expect(self.page.get_by_role("button", name="Configurar colunas")).to_have_count(0)
        expect(self.card("PHZ-0002")).to_have_attribute("draggable", "false")

    # -- configurable columns ---------------------------------------------------------
    def test_columns_can_be_renamed_remapped_and_reordered_without_touching_recorded_events(self):
        self.board()
        self.sign()
        self.move("PHZ-0002", "02 Pesquisa")
        expect(self.page.get_by_role("status")).to_contain_text("Movido")
        before = [dict(e) for e in self.db.events]
        self.page.get_by_role("button", name="Configurar colunas").click()
        form = self.page.get_by_role("form", name="Nome da coluna 7")
        form.get_by_label("Nome da coluna (PT)").fill("07 Em construção")
        form.get_by_label("Limite de WIP").fill("2")
        form.get_by_role("button", name="Salvar").click()
        expect(self.cfg()).to_contain_text("Salvo")
        c7 = self.col(7)
        self.assertEqual((c7["name"]["pt"], c7["wip_limit"]), ("07 Em construção", 2))
        expect(self.page.locator(f'.bhead[data-column="{c7["id"]}"]')).to_contain_text("07 Em construção")
        self.assertEqual(self.db.events, before)                                         # the history is untouched
        # reorder: the last column goes up
        last = sorted(self.db.columns, key=lambda c: c["position"])
        self.page.get_by_role("form", name="Nome da coluna 10").get_by_role("button", name="Subir").click()
        expect(self.page.locator(".bhead").nth(8)).to_contain_text("10 Lançamento")
        order = [c["stage"] for c in sorted(self.db.columns, key=lambda c: c["position"])]
        self.assertEqual(order, [1, 2, 3, 4, 5, 6, 7, 8, 10, 9])
        self.assertEqual(len(last), 10)

    def test_a_new_column_can_map_to_a_stage_that_already_has_one(self):
        self.board()
        self.sign()
        self.page.get_by_role("button", name="Configurar colunas").click()
        form = self.page.get_by_role("form", name="Nova coluna")
        form.get_by_label("Nome da coluna (PT)").fill("07 Revisão de código")
        form.get_by_label("Etapa da norma").select_option(label="07 Desenvolvimento")
        form.get_by_role("button", name="Criar").click()
        expect(self.page.locator(".bhead")).to_have_count(11)
        new = [c for c in self.db.columns if c["name"]["pt"] == "07 Revisão de código"][0]
        self.assertEqual(new["stage"], 7)
        self.assertEqual(self.db.themes["PHZ-0003"]["stage"], 7)                          # still in the first column of 07
        expect(self.page.locator(f'.cell[data-column="{self.col(7)["id"]}"] article[data-theme="PHZ-0003"]')).to_have_count(1)

    def test_the_only_column_of_a_stage_with_projects_cannot_be_removed_or_remapped(self):
        self.board()
        self.sign()
        self.page.get_by_role("button", name="Configurar colunas").click()
        self.page.get_by_role("form", name="Nome da coluna 7").get_by_role("button", name="Remover").click()
        expect(self.cfg()).to_contain_text("única coluna")
        self.assertEqual(len(self.db.columns), 10)
        form = self.page.get_by_role("form", name="Nome da coluna 7")
        form.get_by_label("Etapa da norma").select_option(label="08 Testes")
        form.get_by_role("button", name="Salvar").click()
        expect(self.cfg()).to_contain_text("única coluna")
        self.assertEqual(self.col(7)["stage"], 7)

    def test_an_empty_stage_can_lose_its_column(self):
        self.page.goto(self.base + "/board/")
        self.sign()
        self.page.get_by_role("button", name="Configurar colunas").click()
        self.page.get_by_role("form", name="Nome da coluna 10").get_by_role("button", name="Remover").click()
        expect(self.page.locator(".bhead")).to_have_count(9)

    def test_deleting_a_column_sends_its_cards_to_the_first_column_of_the_stage(self):
        extra = self.db.save_board_column(None, {"name": {"pt": "07 Extra"}, "stage": 7}, "Ana")["id"]
        self.db.themes["PHZ-0003"]["board_column"] = extra
        self.db.delete_board_column(extra, "Ana")
        self.board()
        expect(self.page.locator(f'.cell[data-column="{self.col(7)["id"]}"] article[data-theme="PHZ-0003"]')).to_have_count(1)

    # -- the gate checklist on the theme page -------------------------------------------
    def test_gates_are_ticked_with_an_evidence_and_unticked(self):
        self.page.goto(self.base + "/themes/PHZ-0001/")
        self.sign()
        box = self.page.get_by_role("region", name="Checklist de gates")
        expect(box.locator("[data-gate]")).to_have_count(6)               # stage 04 (2), 03 (1), 02 (1), 01 (2)
        row = box.locator('[data-gate="04-prd"]')
        row.get_by_role("button", name="Marcar").click()
        expect(box.get_by_role("status")).to_contain_text("evidência")
        row.get_by_label("Evidência").fill("PRD v3 no Confluence")
        row.get_by_role("button", name="Marcar").click()
        expect(row).to_have_attribute("data-done", "1")
        expect(row).to_contain_text("PRD v3 no Confluence")
        expect(row).to_contain_text("Ana")
        self.assertEqual([(k["gate_key"], k["evidence"]) for k in self.db.gate_checks], [("04-prd", "PRD v3 no Confluence")])
        self.assertTrue([e for e in self.db.events if e["field"] == "gate_checked"])
        row.get_by_role("button", name="Desmarcar").click()
        expect(row).to_have_attribute("data-done", "0")
        self.assertEqual(self.db.gate_checks, [])

    def test_open_gates_of_a_passed_stage_are_flagged_and_gates_of_stages_ahead_are_not_listed(self):
        self.page.goto(self.base + "/themes/PHZ-0001/")
        box = self.page.get_by_role("region", name="Checklist de gates")
        expect(box.locator('[data-gate="03-approved"] .flag')).to_have_text("aberto em etapa anterior")
        expect(box.locator('[data-gate="04-prd"] .flag')).to_have_count(0)
        expect(box.locator('[data-gate="05-conclusions"]')).to_have_count(0)

    def test_a_bug_route_theme_lists_only_the_gates_of_its_route(self):
        self.page.goto(self.base + "/themes/PHZ-0011/")
        box = self.page.get_by_role("region", name="Checklist de gates")
        expect(box.locator('[data-gate="06-milestones"]')).to_have_count(1)
        expect(box.locator('[data-gate="01-triage"]')).to_have_count(0)

    def test_standalone_tasks_have_no_gate_checklist(self):
        self.page.goto(self.base + "/themes/PHZ-0010/")
        expect(self.page.locator("h1")).to_be_visible()
        expect(self.page.get_by_role("region", name="Checklist de gates")).to_have_count(0)

    def test_the_history_of_a_theme_shows_the_move(self):
        self.board()
        self.sign()
        self.move("PHZ-0002", "02 Pesquisa")
        expect(self.page.get_by_role("status")).to_contain_text("Movido")
        self.page.goto(self.base + "/themes/PHZ-0002/")
        expect(self.page.locator(".history")).to_contain_text("card movido: 01 Solicitação → 02 Pesquisa (2 gates abertos)")


if __name__ == "__main__":
    unittest.main()
