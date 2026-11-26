"""The Painel at /overview/ (docs/spec/v2/redesign.md, "Painel"; it replaced the overview of design part 2 on purpose: the attention list, the next four
weeks, the front table and "updated this week" became the three blocks, the front heads, and the "without update" filter), against tests/fake_themes.py.
The numbers on top and the executive view they open are unchanged."""
import re
import sys
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from playwright.sync_api import expect

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import SiteCase  # noqa: E402

TODAY = datetime.now(timezone.utc).date()


def day(n):
    return (TODAY + timedelta(days=n)).isoformat()


def this_week():
    y, w, _ = datetime.now(timezone.utc).isocalendar()
    return f"{y}-W{w:02d}"


def quarters(n=5):
    """The columns of the timeline: (label, first day, last day), from the quarter of today (the same rule as apps/web/lib/painel.ts)."""
    y, q = TODAY.year, (TODAY.month - 1) // 3 + 1
    out = []
    for _ in range(n):
        start = date(y, (q - 1) * 3 + 1, 1)
        end = (date(y + (q == 4), (q % 4) * 3 + 1, 1) - timedelta(days=1))
        out.append((f"Q{q} {y}", start.isoformat(), end.isoformat()))
        y, q = (y + 1, 1) if q == 4 else (y, q + 1)
    return out


class OverviewTest(SiteCase):
    def setUp(self):
        super().setUp()
        db = self.db
        db.week = this_week()
        db.seed_theme("PHZ-0001", "api-platform", title={"pt": "Business Messaging API"}, status="on_track", owner="Gleison", due_date=day(20),
                      progress={"pt": "Contrato fechado"}, what_it_is={"pt": "API para empresas falarem com usuários"})
        db.seed_theme("PHZ-0002", "payments", title={"pt": "Migração CredPay"}, status="at_risk", owner="Ana", due_date=day(-3), tags=["china"])     # at risk and overdue
        db.seed_theme("PHZ-0003", "payments", title={"pt": "Checkout global"}, status="blocked", owner="Bo")
        db.seed_theme("PHZ-0004", "pop", title={"pt": "OpenPlatform"}, status="done", due_date=day(-30))                              # done: not listed
        db.seed_theme("PHZ-0010", "outros", kind="task", title={"pt": "Game Center"}, due_date=day(40))
        db.seed_update("PHZ-0001", progress={"pt": "Contrato fechado"})                                                                 # the only one updated this week
        db.items.append({"id": "m1", "theme_id": "PHZ-0003", "title": "Piloto", "owner": None, "col": "todo", "due_date": day(5), "milestone": True, "created_at": "x"})
        db.items.append({"id": "m2", "theme_id": "PHZ-0003", "title": "Antigo", "owner": None, "col": "todo", "due_date": day(-5), "milestone": True, "created_at": "x"})
        db.seed_blocker("PHZ-0003", {"pt": "Fornecedor parado"}, leadership=True, owner="Diretoria", due_date=day(2))
        db.seed_decision("PHZ-0002", {"pt": "Escolher o parceiro"}, urgency="urgent", decider="Gustavo")
        db.seed_decision("PHZ-0001", {"pt": "Opt-in"}, state="decided", decision={"pt": "A primeira mensagem é sempre entregue"},
                         decided_at=f"{day(-2)}T10:00:00+00:00", decider="Richard")

    def overview(self, query=""):
        self.page.goto(self.base + "/overview/" + query)
        expect(self.page.locator("h1")).to_have_text("Visão geral")
        expect(self.page.locator(".kpis")).to_be_visible()

    def sign(self, name="Ana"):
        self.prefs()
        self.page.get_by_label("Seu nome").fill(name)
        self.page.keyboard.press("Escape")

    def kpi(self, k):
        return self.page.locator(f'.kpi[data-kpi="{k}"] .kpi-n')

    def block(self, name):
        return self.page.get_by_role("region", name=name)

    def timeline(self):
        self.page.get_by_role("group", name="Visualização").get_by_role("button", name="Linha do tempo").click()
        expect(self.page.locator('[data-view="timeline"]')).to_be_visible()

    # -- the numbers (unchanged) ---------------------------------------------------------------------------------------------------------------
    def test_the_numbers_of_the_portfolio(self):
        self.overview()
        want = {"active": "4", "on_track": "1", "at_risk": "2", "overdue": "1", "stale": "3", "leadership": "1"}
        for k, v in want.items():
            with self.subTest(k):
                expect(self.kpi(k)).to_have_text(v)
        expect(self.page.locator('.kpi[data-kpi="leadership"]')).to_have_attribute("data-tone", "alert")
        expect(self.page.locator('.kpi[data-kpi="on_track"]')).not_to_have_attribute("data-tone", re.compile(".+"))

    def test_each_number_opens_the_executive_view_filtered(self):
        self.overview()
        self.page.locator('.kpi[data-kpi="at_risk"]').click()
        expect(self.page).to_have_url(self.base + "/executive/?f=at_risk")
        expect(self.page.locator("tr.theme-row")).to_have_count(2)
        self.assertEqual(sorted(self.page.locator("tr.theme-row").evaluate_all("els => els.map(e => e.dataset.theme)")), ["PHZ-0002", "PHZ-0003"])
        self.page.locator('[data-focus="at_risk"]').click()                                       # the chip removes the filter
        expect(self.page.locator("tr.theme-row")).to_have_count(5)

    def test_the_numbers_on_the_executive_view_filter_it_and_a_second_click_clears(self):
        self.page.goto(self.base + "/executive/")
        expect(self.page.locator("tr.theme-row").first).to_be_visible()
        self.page.locator('.kpi[data-kpi="overdue"]').click()
        expect(self.page.locator("tr.theme-row")).to_have_count(1)
        expect(self.page.locator('tr[data-theme="PHZ-0002"] .signals')).to_contain_text("Atrasados")
        expect(self.page.locator('.kpi[data-kpi="overdue"]')).to_have_attribute("aria-pressed", "true")
        self.page.locator('.kpi[data-kpi="overdue"]').click()
        expect(self.page.locator("tr.theme-row")).to_have_count(5)
        self.page.locator('.kpi[data-kpi="leadership"]').click()
        self.assertEqual(self.page.locator("tr.theme-row").evaluate_all("els => els.map(e => e.dataset.theme)"), ["PHZ-0003"])

    # -- the three blocks ----------------------------------------------------------------------------------------------------------------------
    def test_needs_you_shows_the_theme_then_the_message_then_the_urgency_urgent_first_and_no_names(self):
        self.overview()
        box = self.block("Precisa de vocês")
        rows = box.locator("li")
        self.assertEqual(rows.evaluate_all("els => els.map(e => [e.dataset.theme, e.dataset.urgency])"), [["PHZ-0002", "urgent"], ["PHZ-0003", "important"]])
        first = rows.nth(0)
        self.assertEqual([first.locator(".pn-theme").inner_text(), first.locator(".urg").inner_text(), first.locator(".pn-msg").inner_text()],
                         ["Migração CredPay", "Urgente", "Escolher o parceiro"])
        self.assertEqual(first.locator(".pn-top > *").evaluate_all("els => els.map(e => e.className)")[0], "pn-theme")     # the theme comes first
        expect(rows.nth(1)).to_contain_text(day(2))
        for who in ("Diretoria", "Gustavo", "Ana", "Bo"):
            expect(box).not_to_contain_text(who)
        self.assertEqual(first.locator("a").get_attribute("href"), "/themes/PHZ-0002/")

    def test_latest_decisions_and_next_milestones(self):
        self.overview()
        dec = self.block("Últimas decisões").locator("li")
        expect(dec).to_have_count(1)
        self.assertEqual([dec.locator(".pn-theme").inner_text(), dec.locator(".pn-msg").inner_text(), dec.locator(".urg").inner_text()],
                         ["Business Messaging API", "A primeira mensagem é sempre entregue", "Informativo"])
        expect(self.block("Últimas decisões")).not_to_contain_text("Richard")
        nxt = self.block("Próximos marcos").locator("li")
        self.assertEqual(nxt.evaluate_all("els => els.map(e => e.dataset.theme)"), ["PHZ-0003", "PHZ-0001", "PHZ-0010"])      # by date; the old milestone is out
        expect(nxt.nth(0)).to_contain_text("◆ Piloto")
        expect(nxt.nth(0).locator(".urg")).to_have_text("Planejado")
        expect(nxt.nth(1)).to_contain_text("conclusão estimada")

    def test_empty_blocks(self):
        for t in list(self.db.themes):
            del self.db.themes[t]
        self.db.blockers.clear()
        self.db.decisions.clear()
        self.db.items.clear()
        self.overview()
        expect(self.page.get_by_text("Nada precisa de vocês agora.")).to_be_visible()
        expect(self.page.get_by_text("Nenhuma decisão tomada ainda.")).to_be_visible()
        expect(self.page.get_by_text("Nenhum marco nos próximos 90 dias.")).to_be_visible()

    # -- the list ------------------------------------------------------------------------------------------------------------------------------
    def test_the_list_groups_the_open_themes_by_front_with_the_numbers_of_each_front(self):
        self.overview()
        groups = self.page.locator('[data-view="list"] .pn-group')
        self.assertEqual(groups.evaluate_all("els => els.map(e => e.dataset.front)"), ["api-platform", "payments", "outros"])      # done PHZ-0004 is not listed
        pay = self.page.locator('[data-view="list"] .pn-group[data-front="payments"]')
        expect(pay.locator(".pn-row")).to_have_count(2)
        expect(pay.locator('.flag[data-k="overdue"]')).to_have_text("1 Atrasados")
        expect(pay.locator('.flag[data-k="stale"]')).to_have_text("2 Sem atualização na semana")
        self.assertEqual(pay.locator(".mix").get_attribute("aria-label").split(", ")[1:3], ["Em risco: 1", "Bloqueado: 1"])
        row = self.page.locator('.pn-row[data-theme="PHZ-0001"]')
        expect(row.locator(".pn-what")).to_have_text("API para empresas falarem com usuários")
        expect(row.locator(".pn-progress")).to_have_text("Contrato fechado")
        expect(self.page.locator('.pn-row[data-theme="PHZ-0002"] .flag')).to_have_text("sem atualização esta semana")

    def test_filters_combine_and_a_front_shows_its_scope(self):
        self.overview()
        bar = self.page.get_by_role("group", name="Filtros")
        bar.get_by_label("Frente").select_option("payments")
        expect(self.page.locator(".pn-row")).to_have_count(2)
        expect(self.page.locator(".pn-scope")).to_have_text("Escopo de Payments")
        bar.get_by_label("Responsável").select_option("Ana")
        self.assertEqual(self.page.locator(".pn-row").evaluate_all("els => els.map(e => e.dataset.theme)"), ["PHZ-0002"])
        bar.get_by_role("button", name="Limpar").click()
        expect(self.page.locator(".pn-row")).to_have_count(4)
        bar.get_by_label("Etiqueta").select_option("china")
        expect(self.page.locator(".pn-row")).to_have_count(1)
        bar.get_by_role("button", name="Limpar").click()
        bar.get_by_label("Tipo").select_option("task")
        self.assertEqual(self.page.locator(".pn-row").evaluate_all("els => els.map(e => e.dataset.theme)"), ["PHZ-0010"])
        bar.get_by_role("button", name="Limpar").click()
        bar.get_by_label("Status").select_option("done")                                              # a closed status shows the closed themes
        self.assertEqual(self.page.locator(".pn-row").evaluate_all("els => els.map(e => e.dataset.theme)"), ["PHZ-0004"])

    def test_the_toggles_without_update_and_only_what_needs_attention(self):
        self.overview()
        bar = self.page.get_by_role("group", name="Filtros")
        stale = bar.locator('[data-toggle="stale"]')
        expect(stale).to_have_text("3 sem atualização na semana")
        stale.click()
        self.assertEqual(sorted(self.page.locator(".pn-row").evaluate_all("els => els.map(e => e.dataset.theme)")), ["PHZ-0002", "PHZ-0003", "PHZ-0010"])
        stale.click()
        bar.get_by_role("button", name="Só o que pede atenção").click()
        self.assertNotIn("PHZ-0001", self.page.locator(".pn-row").evaluate_all("els => els.map(e => e.dataset.theme)"))

    def test_status_owner_and_forecast_are_edited_in_the_list(self):
        self.overview()
        self.sign()
        row = self.page.locator('.pn-row[data-theme="PHZ-0003"]')
        row.get_by_label("Status").select_option("at_risk")
        expect(row.get_by_label("Status")).to_have_value("at_risk")
        fn, body = self.db.calls[-1]
        self.assertEqual((fn, body["p_id"], body["p"]), ("update_theme", "PHZ-0003", {"status": "at_risk"}))
        self.assertEqual([e["field"] for e in self.db.events], ["status"])
        row.get_by_label("Responsável").fill("Cristiano")
        row.get_by_label("Responsável").press("Enter")
        expect(row.get_by_label("Responsável")).to_have_value("Cristiano")
        self.assertEqual(self.db.themes["PHZ-0003"]["owner"], "Cristiano")
        label, _, end = quarters()[1]
        row.get_by_label("Previsão").select_option(label=label)
        expect(row.get_by_label("Previsão")).to_have_value(end)
        self.assertEqual(self.db.themes["PHZ-0003"]["due_date"], end)

    def test_without_a_name_nothing_is_written(self):
        self.overview()
        self.page.locator('.pn-row[data-theme="PHZ-0003"]').get_by_label("Status").select_option("at_risk")
        expect(self.page.get_by_role("alert").filter(has_text="Informe seu nome para salvar.")).to_be_visible()
        self.assertEqual(self.db.calls, [])

    # -- the timeline --------------------------------------------------------------------------------------------------------------------------
    def test_the_timeline_has_five_quarters_today_and_a_bar_with_the_forecast(self):
        self.db.themes["PHZ-0001"].update(start_date=quarters()[0][1], due_date=quarters()[1][2])
        self.overview()
        self.timeline()
        self.assertEqual(self.page.locator(".pn-q").all_inner_texts(), [q[0] for q in quarters()])
        expect(self.page.locator(".pn-today")).to_have_text("hoje")
        row = self.page.locator('.pn-tl-theme[data-theme="PHZ-0001"] > .pn-tl-row')
        expect(row.locator(".pn-bar")).to_have_text("Business Messaging API")
        expect(row.locator(".pn-diamond")).to_have_count(1)

    def test_a_click_on_a_quarter_sets_the_period_of_a_theme_without_deliveries(self):
        self.db.seed_theme("PHZ-0020", "pop", title={"pt": "Sem datas"})
        self.overview()
        self.sign()
        self.timeline()
        row = self.page.locator('.pn-tl-theme[data-theme="PHZ-0020"] > .pn-tl-row')
        expect(row.locator(".pn-bar")).to_have_count(0)                                                     # no dates, no bar
        q = quarters()
        row.get_by_label(f"Ajustar o período até {q[1][0]}").click()
        expect(row.locator(".pn-bar")).to_have_count(1)
        self.assertEqual((self.db.themes["PHZ-0020"]["start_date"], self.db.themes["PHZ-0020"]["due_date"]), (q[1][1], q[1][2]))
        row.get_by_label(f"Ajustar o período até {q[3][0]}").click()                                       # stretches the end
        expect(row.locator(".pn-bar")).to_have_text("Sem datas")
        self.assertEqual((self.db.themes["PHZ-0020"]["start_date"], self.db.themes["PHZ-0020"]["due_date"]), (q[1][1], q[3][2]))

    def test_deliveries_open_under_the_theme_are_added_with_enter_and_get_a_period_by_quarter(self):
        self.overview()
        self.sign()
        self.timeline()
        theme = self.page.locator('.pn-tl-theme[data-theme="PHZ-0003"]')
        theme.get_by_label("Mostrar ou esconder as entregas").click()
        items = theme.locator(".pn-item[data-item]")
        expect(items).to_have_count(2)                                                                      # the two milestones of the setup
        box = theme.get_by_label("Nova entrega (Enter para adicionar)")
        box.fill("Suporte a mídia")
        box.press("Enter")
        expect(items).to_have_count(3)
        expect(box).to_have_value("")
        fn, body = self.db.calls[-1]
        self.assertEqual((fn, body["p_theme"], body["p_item"], body["p"]), ("save_theme_item", "PHZ-0003", None, {"title": "Suporte a mídia"}))
        new = theme.locator(f'.pn-item[data-item="{self.db.items[-1]["id"]}"]')
        q = quarters()
        new.get_by_label(f"Ajustar o período até {q[2][0]}").click()
        expect(new.locator(".pn-bar")).to_have_count(1)
        row = self.db.items[-1]
        self.assertEqual((row["start_date"], row["due_date"]), (q[2][1], q[2][2]))
        self.assertEqual(self.db.events[-1]["field"], "item_period")

    def test_on_a_theme_with_dated_deliveries_a_click_sets_the_forecast(self):
        self.overview()
        self.sign()
        self.timeline()
        row = self.page.locator('.pn-tl-theme[data-theme="PHZ-0003"] > .pn-tl-row')
        q = quarters()
        row.get_by_label(f"Marcar a previsão em {q[2][0]}").click()
        expect(row.locator(".pn-diamond")).to_have_count(1)
        fn, body = self.db.calls[-1]
        self.assertEqual((fn, body["p"]), ("update_theme", {"due_date": q[2][2]}))

    def test_title_and_what_it_is_are_edited_in_place_keeping_the_other_languages(self):
        self.db.themes["PHZ-0001"]["title"] = {"pt": "Business Messaging API", "en": "Business Messaging API"}
        self.overview()
        self.sign()
        self.timeline()
        row = self.page.locator('.pn-tl-theme[data-theme="PHZ-0001"] > .pn-tl-row')
        title = row.get_by_label("Título")
        title.fill("API de mensagens para empresas")
        title.press("Enter")
        expect(row.get_by_label("Título")).to_have_value("API de mensagens para empresas")
        self.assertEqual(self.db.themes["PHZ-0001"]["title"], {"pt": "API de mensagens para empresas", "en": "Business Messaging API"})
        what = row.get_by_label("O que é")
        what.fill("Mensagens de empresas para usuários")
        what.press("Enter")
        expect(row.get_by_label("O que é")).to_have_value("Mensagens de empresas para usuários")
        self.assertEqual(self.db.themes["PHZ-0001"]["what_it_is"]["pt"], "Mensagens de empresas para usuários")
        self.assertEqual(row.locator(".pn-open").get_attribute("href"), "/themes/PHZ-0001/")

    def test_the_view_is_remembered(self):
        self.overview()
        self.timeline()
        self.overview()
        expect(self.page.locator('[data-view="timeline"]')).to_be_visible()

    # -- reader mode, top bar, language --------------------------------------------------------------------------------------------------------
    def test_reader_mode_shows_the_same_painel_without_any_control(self):
        self.overview("?mode=reader")
        expect(self.page.locator(".pn-row")).to_have_count(4)
        expect(self.page.locator(".painel .pn-list input, .painel .pn-list select")).to_have_count(0)
        expect(self.page.get_by_role("link", name=re.compile("Novo tema"))).to_have_count(0)
        self.timeline()
        expect(self.page.locator(".pn-tl input, .pn-tl button.pn-cell")).to_have_count(0)
        expect(self.page.locator('.pn-tl-theme[data-theme="PHZ-0001"] .pn-what')).to_have_text("API para empresas falarem com usuários")

    def test_new_theme_opens_the_form_on_the_themes_page(self):
        self.overview()
        self.page.get_by_role("link", name=re.compile("Novo tema")).click()
        expect(self.page).to_have_url(self.base + "/themes/?new=1")
        expect(self.page.get_by_role("form", name="Novo tema")).to_be_visible()

    def test_the_top_bar_is_unchanged(self):
        self.overview()
        expect(self.page.locator("a.brand")).to_have_attribute("href", "/overview/")
        self.assertEqual([x.replace("▾", "").strip() for x in self.page.locator(".mainnav > .menu > .navlink").all_inner_texts()], ["Acompanhamento", "Portfólio", "Documentos"])
        hrefs = self.page.locator(".mainnav .menu-pop a").evaluate_all("els => els.map(e => e.getAttribute('href'))")
        self.assertEqual(hrefs, ["/overview/", "/executive/", "/fup/", "/board/", "/roadmap/", "/metrics/", "/themes/", "/slides/", "/", "/attachments/", "/comments/"])

    def test_the_brand_and_the_menu_lead_to_the_overview(self):
        self.page.goto(self.base + "/themes/")
        self.page.locator("a.brand").click()
        expect(self.page).to_have_url(self.base + "/overview/")
        self.page.get_by_role("button", name="Acompanhamento").click()
        expect(self.page.locator(".menu-pop a").first).to_have_text("Visão geral")

    def test_the_overview_in_english(self):
        self.overview()
        self.prefs()
        self.page.get_by_role("button", name="EN-US").click()
        expect(self.page.locator("h1")).to_have_text("Overview")
        expect(self.page.get_by_role("region", name="Needs you")).to_be_visible()
        expect(self.page.locator('.kpi[data-kpi="overdue"] .kpi-label')).to_have_text("Overdue")
        expect(self.page.locator('[data-urgency="urgent"] .urg')).to_have_text("Urgent")


if __name__ == "__main__":
    unittest.main()
