"""Design part 2: the overview (the leadership's home) and the executive view's numbers as filters, against tests/fake_themes.py."""
import re
import sys
import unittest
from datetime import datetime, timedelta, timezone
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


class OverviewTest(SiteCase):
    def setUp(self):
        super().setUp()
        db = self.db
        db.week = this_week()
        db.seed_theme("PHZ-0001", "api-platform", title={"pt": "Business Messaging API"}, status="on_track", owner="Gleison", due_date=day(20),
                      progress={"pt": "Contrato fechado"})
        db.seed_theme("PHZ-0002", "payments", title={"pt": "Migração CredPay"}, status="at_risk", owner="Ana", due_date=day(-3))     # at risk and overdue
        db.seed_theme("PHZ-0003", "payments", title={"pt": "Checkout global"}, status="blocked", owner="Bo")
        db.seed_theme("PHZ-0004", "pop", title={"pt": "OpenPlatform"}, status="done", due_date=day(-30))                              # done: never chased
        db.seed_theme("PHZ-0010", "outros", kind="task", title={"pt": "Game Center"}, due_date=day(40))                                 # beyond 4 weeks
        db.seed_update("PHZ-0001", progress={"pt": "Contrato fechado"})                                                                 # the only one updated this week
        db.items.append({"id": "m1", "theme_id": "PHZ-0003", "title": "Piloto", "owner": None, "col": "todo", "due_date": day(5), "milestone": True, "created_at": "x"})
        db.items.append({"id": "m2", "theme_id": "PHZ-0003", "title": "Antigo", "owner": None, "col": "todo", "due_date": day(-5), "milestone": True, "created_at": "x"})
        db.seed_blocker("PHZ-0003", {"pt": "Fornecedor parado"}, leadership=True, owner="Diretoria", due_date=day(2))

    def overview(self):
        self.page.goto(self.base + "/overview/")
        expect(self.page.locator("h1")).to_have_text("Visão geral")
        expect(self.page.locator(".kpis")).to_be_visible()

    def kpi(self, k):
        return self.page.locator(f'.kpi[data-kpi="{k}"] .kpi-n')

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

    def test_what_needs_attention_lists_the_leadership_first_then_themes_at_risk_blocked_or_overdue(self):
        self.overview()
        box = self.page.get_by_role("region", name="Pede atenção")
        expect(box.get_by_role("region", name="Exige a liderança").locator("li")).to_have_count(1)
        expect(box.get_by_role("region", name="Exige a liderança")).to_contain_text("Fornecedor parado")
        watch = box.locator("ul.lines li")
        self.assertEqual(watch.evaluate_all("els => els.map(e => e.dataset.theme)"), ["PHZ-0003", "PHZ-0002"])     # blocked first
        expect(box.locator('li[data-theme="PHZ-0002"]')).to_contain_text("Atrasados · " + day(-3))

    def test_the_next_four_weeks_show_milestones_and_estimates_in_date_order(self):
        self.overview()
        rows = self.page.get_by_role("region", name="Próximas 4 semanas").locator("li")
        self.assertEqual(rows.evaluate_all("els => els.map(e => e.dataset.theme)"), ["PHZ-0003", "PHZ-0001"])        # the old milestone, the done theme and day +40 are out
        expect(rows.nth(0)).to_contain_text(day(5))
        expect(rows.nth(0)).to_contain_text("◆ Piloto")
        expect(rows.nth(1)).to_contain_text("conclusão estimada")

    def test_each_front_in_one_line(self):
        self.overview()
        row = self.page.locator('.fronts-sum tr[data-front="payments"]')
        self.assertEqual([row.locator(f'td[data-k="{k}"]').inner_text() for k in ("active", "at_risk", "overdue", "stale")], ["2", "2", "1", "2"])
        self.assertEqual(row.locator(".mix").get_attribute("aria-label").split(", ")[1:3], ["Em risco: 1", "Bloqueado: 1"])
        self.assertEqual(self.page.locator(".fronts-sum tbody tr").evaluate_all("els => els.map(e => e.dataset.front)"), ["pop", "api-platform", "payments", "outros"])
        self.assertEqual(row.locator("a").get_attribute("href"), "/executive/#front-payments")

    def test_the_themes_updated_this_week_with_their_sentence(self):
        self.overview()
        box = self.page.get_by_role("region", name="Atualizados nesta semana")
        expect(box.locator("li")).to_have_count(1)
        expect(box.locator("li")).to_contain_text("Contrato fechado")

    def test_empty_states(self):
        for t in list(self.db.themes):
            del self.db.themes[t]
        self.db.blockers.clear()
        self.db.items.clear()
        self.db.updates.clear()
        self.overview()
        expect(self.page.get_by_text("Nada exige a liderança agora.")).to_be_visible()
        expect(self.page.get_by_text("Nada pede atenção agora.")).to_be_visible()
        expect(self.page.get_by_text("Nada vence nas próximas 4 semanas.")).to_be_visible()
        expect(self.page.get_by_text("Nenhum tema foi atualizado nesta semana.")).to_be_visible()

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
        expect(self.page.get_by_role("region", name="Needs attention")).to_be_visible()
        expect(self.page.locator('.kpi[data-kpi="overdue"] .kpi-label')).to_have_text("Overdue")


if __name__ == "__main__":
    unittest.main()
