"""Phase 7: the /metrics/ page, against tests/fake_themes.py. The numbers come from histories seeded relative to today, so every expected
value is a whole number of days worked out here (the formulas themselves are tested in tests/test_metrics.py)."""
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from playwright.sync_api import expect

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import SiteCase  # noqa: E402

BASE = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(hours=12)       # yesterday 12:00 UTC: always in the past


def ago(n):
    return (BASE - timedelta(days=n)).strftime("%Y-%m-%dT%H:%M:%SZ")


class MetricsPageTest(SiteCase):
    def project(self, tid, created, steps=(), done=None, front="payments", route="full", stage=None, resolution=None, owner=None, tags=()):
        """A project theme created `created` days ago; steps = [(days ago, from, to, open_gates)] recorded as board moves; done = days ago it was closed as done."""
        last = steps[-1][2] if steps else (1 if route == "full" else 6 if route == "bug" else 7)
        row = self.db.seed_theme(tid, front, "project", {"pt": f"Tema {tid}"}, stage=stage if stage is not None else last, route=route, owner=owner, tags=list(tags),
                                 created_at=ago(created), resolution="done" if done is not None else resolution)
        for d, frm, to, gates in steps:
            self.db.events.append({"id": f"{tid}-{d}", "theme_id": tid, "item_id": None, "at": ago(d), "edited_by": "Ana", "field": "move", "old_value": None,
                                   "new_value": {"from_stage": frm, "to_stage": to, "open_gates": list(gates), "reason": None}})
        if done is not None:
            self.db.events.append({"id": f"{tid}-done", "theme_id": tid, "item_id": None, "at": ago(done), "edited_by": "Ana", "field": "resolution", "old_value": None, "new_value": "done"})
        return row

    def metrics(self, query=""):
        self.page.goto(self.base + "/metrics/" + query)
        expect(self.page.locator("h1")).to_have_text("Métricas")
        expect(self.page.locator('[data-block="times"]')).to_be_visible()

    def cell(self, metric, k):
        return self.page.locator(f'tr[data-metric="{metric}"] td[data-k="{k}"]')

    def setUp(self):
        super().setUp()
        # A: created 50 days ago, 1→4 40 days ago, 4→7 30 days ago, done 10 days ago: lead 40, delivery 30, cycle 20
        self.project("PHZ-0001", 50, [(40, 1, 4, ["04-x"]), (30, 4, 7, [])], done=10, owner="Ana", tags=["china"])
        # B: created 30 days ago, 1→7 20 days ago, done 10 days ago: lead 20, delivery 10, cycle 10
        self.project("PHZ-0002", 30, [(20, 1, 7, [])], done=10, front="api-platform", owner="Bo")
        # C: open at 04 for 12 days; D: open at 04 for 3 days
        self.project("PHZ-0003", 20, [(12, 1, 4, [])], owner="Ana")
        self.project("PHZ-0004", 15, [(3, 1, 4, ["04-prd", "04-jira"])], front="pop")

    # -- times --------------------------------------------------------------------------------------------------
    def test_lead_delivery_and_cycle_time_show_the_median_and_the_85th_percentile(self):
        self.metrics()
        for metric, want in (("leadTime", ("2", "30.0", "40.0")), ("deliveryTime", ("2", "20.0", "30.0")), ("cycleTime", ("2", "15.0", "20.0"))):
            with self.subTest(metric):
                self.assertEqual([self.cell(metric, k).inner_text() for k in ("n", "median", "p85")], list(want))

    def test_a_block_says_how_it_is_computed_and_lists_the_themes_behind_it(self):
        self.metrics()
        block = self.page.locator('[data-block="times"]')
        block.get_by_text("Como é calculado e quais são").first.click()
        expect(block.locator("details").first).to_contain_text("Da criação do tema")
        expect(block.locator("details").first.locator("li")).to_have_count(2)
        expect(block.locator("details").first.get_by_role("link", name="PHZ-0001")).to_have_attribute("href", "/themes/PHZ-0001/")

    def test_themes_with_an_estimated_history_are_left_out_until_asked_for(self):
        self.db.seed_theme("PHZ-0009", "payments", "project", {"pt": "Importado"}, stage=10, created_at=ago(60), resolution="done")      # closed with no event
        self.metrics()
        expect(self.page.locator("[data-estimated]")).to_contain_text("1 temas sem histórico registrado")
        self.assertEqual(self.cell("leadTime", "n").inner_text(), "2")
        self.page.get_by_label("Incluir temas com histórico estimado").check()
        expect(self.cell("leadTime", "n")).to_have_text("3")

    def test_the_period_filter_limits_what_counts_as_finished(self):
        self.project("PHZ-0005", 200, [(190, 1, 7, [])], done=100)
        self.metrics()
        self.assertEqual(self.cell("leadTime", "n").inner_text(), "2")                  # 90 days by default: the one closed 100 days ago is out
        self.page.get_by_label("Período").select_option(label="Todo o histórico")
        expect(self.cell("leadTime", "n")).to_have_text("3")
        self.page.get_by_label("Período").select_option(label="Últimos 30 dias")
        expect(self.cell("leadTime", "n")).to_have_text("2")

    def test_front_tag_route_and_owner_filters(self):
        self.metrics()
        self.page.get_by_label("Frente").select_option(label="Payments")
        expect(self.cell("leadTime", "n")).to_have_text("1")
        self.page.get_by_label("Frente").select_option(label="Todos")
        self.page.get_by_label("Etiqueta").select_option(label="#china")
        expect(self.cell("leadTime", "median")).to_have_text("40.0")
        self.page.get_by_label("Etiqueta").select_option(label="Todos")
        self.page.get_by_label("Responsável").select_option(label="Bo")
        expect(self.cell("leadTime", "median")).to_have_text("20.0")

    def test_a_bug_route_theme_counts_in_lead_and_cycle_but_not_in_delivery(self):
        self.project("PHZ-0006", 12, [(8, 6, 8, [])], done=5, route="bug")
        self.metrics()
        expect(self.cell("leadTime", "n")).to_have_text("3")
        expect(self.cell("deliveryTime", "n")).to_have_text("2")
        expect(self.cell("cycleTime", "n")).to_have_text("3")

    # -- stages, WIP, aging --------------------------------------------------------------------------------------
    def test_time_in_each_stage_and_wip_against_the_column_limit(self):
        self.db.save_board_column(self.db.column_of_stage(4)["id"], {"wip_limit": 1}, "Ana")
        self.metrics()
        row4 = self.page.locator('tr[data-stage="4"]')
        expect(row4.locator('td[data-k="wip"]')).to_have_text("2 / 1")
        expect(row4).to_have_attribute("data-over", "1")
        # stage 04, finished themes: A 10 days (Jan 40 → 30 ago), B none → n=1, median 10
        self.assertEqual([row4.locator(f'td[data-k="{k}"]').inner_text() for k in ("n", "median")], ["1", "10.0"])
        expect(self.page.locator('tr[data-stage="7"] td[data-k="wip"]')).to_have_text("0")

    def test_open_themes_older_than_the_85th_percentile_of_the_finished_ones_are_flagged(self):
        self.metrics()
        a = self.page.locator('[data-block="aging"] tr[data-theme="PHZ-0003"]')
        expect(a).to_have_attribute("data-over", "1")                                    # 12 days in 04; the finished one stayed 10
        expect(a).to_contain_text("acima do P85")
        expect(self.page.locator('[data-block="aging"] tr[data-theme="PHZ-0004"]')).to_have_attribute("data-over", "0")
        first = self.page.locator('[data-block="aging"] tbody tr').first
        expect(first).to_have_attribute("data-theme", "PHZ-0003")                         # the oldest first

    # -- throughput, CFD --------------------------------------------------------------------------------------------
    def test_throughput_has_a_bar_for_each_week_with_something_done(self):
        self.metrics()
        rects = self.page.locator('[data-block="throughput"] rect[data-week]')
        expect(rects).to_have_count(1)                                                    # both were closed on the same day
        expect(rects.first).to_have_attribute("data-value", "2")

    def test_the_cfd_has_a_band_per_stage_and_a_closed_band(self):
        self.metrics()
        svg = self.page.locator('[data-block="cfd"] svg')
        expect(svg).to_have_attribute("data-days", "52")                                  # from the earliest creation (50 days ago, yesterday noon: 51 days back) to today
        bands = svg.locator("path[data-band]").evaluate_all("els => els.map(e => e.dataset.band)")
        self.assertEqual(sorted(bands, key=lambda b: (b == "closed", int(b) if b != "closed" else 0)), ["1", "4", "7", "closed"])
        self.assertEqual(int(svg.get_attribute("data-max")), 4)

    # -- blocked time, gates, triage ---------------------------------------------------------------------------------
    def test_blocked_time_inside_the_cycle_of_finished_themes(self):
        self.db.seed_blocker("PHZ-0001", {"pt": "x"}, created_at=ago(25), resolved_at=ago(20), state="resolved")             # 5 days inside A's cycle (30 → 10 ago)
        self.metrics()
        self.assertEqual([self.cell("blockedDays", k).inner_text() for k in ("n", "median")], ["2", "2.5"])           # A 5 days, B 0
        self.assertEqual(self.cell("blockedShare", "median").inner_text(), "13%")                                         # (0 + 25%) / 2 = 12.5% → "13%"

    def test_moves_with_open_gates(self):
        self.metrics()
        block = self.page.locator('[data-block="gates"]')
        expect(block.locator('[data-k="gates"]')).to_have_text("2 de 5")                 # forward moves: A 2, B 1, C 1, D 1; open gates on A's 1→4 and D's 1→4
        expect(block.locator('li[data-stage="1"]')).to_contain_text("2")

    def test_triage_share(self):
        self.project("PHZ-0007", 20, [(5, 1, 2, [])])                                    # left 01 after 15 days: late
        self.metrics()
        # A 10 days, B 10, C 8, D 12 and the new one 15: none within 2 business days
        expect(self.page.locator('[data-k="triage"]')).to_contain_text("0%")

    # -- items --------------------------------------------------------------------------------------------------------
    def seed_items(self):
        mk = lambda iid, col, created: {"id": iid, "theme_id": "PHZ-0001", "title": iid, "owner": None, "col": col, "due_date": None, "milestone": False,  # noqa: E731
                                         "created_at": ago(created)}
        self.db.items += [mk("I1", "done", 30), mk("I2", "doing", 30), mk("I3", "todo", 5)]
        ev = lambda iid, d, o, n: self.db.events.append({"id": f"{iid}{d}", "theme_id": "PHZ-0001", "item_id": iid, "at": ago(d), "edited_by": "Ana", "field": "item_col",  # noqa: E731
                                                          "old_value": o, "new_value": n})
        ev("I1", 25, "todo", "doing")
        ev("I1", 15, "doing", "done")
        ev("I2", 8, "todo", "doing")

    def test_item_lead_and_cycle_time_wip_and_aging(self):
        self.seed_items()
        self.metrics()
        self.assertEqual([self.cell("itemLead", k).inner_text() for k in ("n", "median")], ["1", "15.0"])                   # created 30 days ago, done 15 ago
        self.assertEqual([self.cell("itemCycle", k).inner_text() for k in ("n", "median")], ["1", "10.0"])                  # doing 25 ago, done 15 ago
        expect(self.page.locator('[data-k="itemwip"] [data-col="doing"]')).to_have_text("Fazendo: 1")
        expect(self.page.locator('[data-k="itemwip"] [data-col="todo"]')).to_have_text("A fazer: 1")
        expect(self.page.locator('[data-block="items"] li[data-item="I2"]')).to_have_text(__import__("re").compile(r"[89]\.\d d$"))     # 8 days before yesterday noon, so 8.5 to 9.5 from now

    def test_the_cfd_of_the_items_of_one_project(self):
        self.seed_items()
        self.metrics()
        self.page.get_by_label("Projeto").select_option(label="PHZ-0001 Tema PHZ-0001")
        svg = self.page.locator('[data-block="items"] svg[aria-label^="Fluxo acumulado dos itens"]')
        expect(svg).to_be_visible()
        self.assertEqual(sorted(svg.locator("path[data-band]").evaluate_all("els => els.map(e => e.dataset.band)")), ["doing", "done", "todo"])

    def test_the_level_filter_shows_themes_items_or_both(self):
        self.metrics()
        expect(self.page.locator('[data-block="items"]')).to_be_visible()
        self.page.get_by_label("Nível").select_option(label="Temas")
        expect(self.page.locator('[data-block="items"]')).to_have_count(0)
        expect(self.page.locator('[data-block="times"]')).to_be_visible()
        self.page.get_by_label("Nível").select_option(label="Itens")
        expect(self.page.locator('[data-block="times"]')).to_have_count(0)
        expect(self.page.locator('[data-block="items"]')).to_be_visible()

    # -- the rest -----------------------------------------------------------------------------------------------------
    def test_every_page_of_events_is_read(self):
        for i in range(1100):                                                            # more than one request of 1000 rows, before the closing event in time order
            self.db.events.append({"id": f"n{i:04d}", "theme_id": "PHZ-0004", "item_id": None, "at": ago(100), "edited_by": "x", "field": "move",
                                   "old_value": None, "new_value": {"from_stage": 4, "to_stage": 4, "open_gates": [], "reason": None}})
        self.metrics()
        self.assertEqual(self.cell("leadTime", "n").inner_text(), "2")                  # the resolution events (later in time) still arrive

    def test_the_header_links_to_the_metrics_and_reader_mode_shows_the_same_page(self):
        self.page.goto(self.base + "/themes/")
        self.page.get_by_role("button", name="Acompanhamento").click()          # grouped in a menu of the top bar
        self.page.get_by_role("link", name="Métricas").click()
        expect(self.page).to_have_url(self.base + "/metrics/")
        self.metrics("?mode=reader")

    def test_with_no_data_the_page_still_loads(self):
        self.db.themes.clear()
        self.db.events.clear()
        self.page.goto(self.base + "/metrics/")
        expect(self.page.locator("h1")).to_have_text("Métricas")
        expect(self.page.locator('[data-block="throughput"] .empty')).to_have_text("Sem dados no período.")


if __name__ == "__main__":
    unittest.main()
