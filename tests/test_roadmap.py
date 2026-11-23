"""Phase 6: the roadmap built from the themes' own dates and milestones (docs/spec/v2/domain.md, Views), against tests/fake_themes.py."""
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


class RoadmapTest(SiteCase):
    def setUp(self):
        super().setUp()
        db = self.db
        db.seed_theme("PHZ-0001", "api-platform", title={"pt": "Business Messaging API"}, status="on_track", stage=4, owner="Gleison", tags=["china"],
                      start_date=day(-30), due_date=day(60))
        db.seed_theme("PHZ-0002", "payments", title={"pt": "Migração CredPay"}, owner="Ana", due_date=day(20))
        db.seed_theme("PHZ-0003", "payments", title={"pt": "Checkout global"}, status="done", stage=10, owner="Bo", start_date=day(-120), due_date=day(-40))
        db.seed_theme("PHZ-0010", "outros", kind="task", title={"pt": "Game Center"}, status="at_risk", start_date=day(10), due_date=day(45))
        db.seed_theme("PHZ-0004", "pop", title={"pt": "OpenPlatform"})                                   # no dates at all
        db.items.append({"id": "m1", "theme_id": "PHZ-0001", "title": "Beta fechado", "owner": None, "col": "todo", "due_date": day(30), "milestone": True, "created_at": "x"})
        db.items.append({"id": "m2", "theme_id": "PHZ-0001", "title": "Contrato assinado", "owner": None, "col": "done", "due_date": day(-10), "milestone": True, "created_at": "x"})
        db.items.append({"id": "i1", "theme_id": "PHZ-0001", "title": "Tarefa comum", "owner": None, "col": "todo", "due_date": day(5), "milestone": False, "created_at": "x"})

    def roadmap(self, query=""):
        self.page.goto(self.base + "/roadmap/" + query)
        expect(self.page.locator("h1")).to_have_text("Roadmap")
        expect(self.page.locator(".rm-row[data-theme]").first).to_be_visible()

    def row(self, tid):
        return self.page.locator(f'.rm-row[data-theme="{tid}"]')

    def test_themes_with_dates_are_rows_grouped_by_front_and_themes_without_dates_are_listed_below(self):
        self.roadmap()
        self.assertEqual(self.page.locator(".rm-front").all_text_contents(), ["API Platform", "Payments", "Outros"])
        self.assertEqual(self.page.locator(".rm-row[data-theme]").evaluate_all("els => els.map(e => e.dataset.theme)"),
                         ["PHZ-0001", "PHZ-0003", "PHZ-0002", "PHZ-0010"])      # newest first inside a front, as on the themes page
        box = self.page.get_by_role("region", name="Sem datas")
        expect(box.locator("[data-theme]")).to_have_count(1)
        expect(box).to_contain_text("PHZ-0004")
        expect(self.row("PHZ-0004")).to_have_count(0)

    def test_a_theme_with_a_start_and_an_estimate_is_a_bar_whose_ends_are_those_dates(self):
        self.roadmap()
        bar = self.row("PHZ-0001").locator(".rm-bar")
        expect(bar).to_have_attribute("data-from", day(-30))
        expect(bar).to_have_attribute("data-to", day(60))
        expect(bar).to_have_attribute("data-s", "on_track")

    def test_the_bar_position_and_width_follow_the_dates_on_the_axis(self):
        self.roadmap()
        track = self.row("PHZ-0001").locator(".rm-track")
        first = self.page.locator(".rm-month").first
        months = self.page.locator(".rm-month").evaluate_all("els => els.map(e => e.dataset.month)")
        axis_from = datetime.strptime(months[0] + "-01", "%Y-%m-%d").date()
        last = datetime.strptime(months[-1] + "-01", "%Y-%m-%d").date()
        axis_to = (last.replace(day=28) + timedelta(days=4)).replace(day=1)
        span = (axis_to - axis_from).days
        want_left = (TODAY - timedelta(days=30) - axis_from).days / span * 100
        want_width = 91 / span * 100                                                     # -30 .. +60 is 91 days, both ends included
        style = self.row("PHZ-0001").locator(".rm-bar").evaluate("e => [parseFloat(e.style.left), parseFloat(e.style.width)]")
        self.assertAlmostEqual(style[0], want_left, delta=0.05)
        self.assertAlmostEqual(style[1], want_width, delta=0.05)
        expect(first).to_be_visible()
        expect(track).to_be_visible()

    def test_the_axis_covers_every_date_and_today_and_has_a_today_line(self):
        self.roadmap()
        months = self.page.locator(".rm-month").evaluate_all("els => els.map(e => e.dataset.month)")
        self.assertEqual(months[0], (TODAY - timedelta(days=120)).isoformat()[:7])        # the earliest date (PHZ-0003's start)
        self.assertGreaterEqual(months[-1], (TODAY + timedelta(days=60)).isoformat()[:7])
        expect(self.row("PHZ-0001").locator(".rm-today")).to_have_attribute("data-today", TODAY.isoformat())

    def test_a_theme_with_only_an_estimate_is_a_marker_on_that_day(self):
        self.roadmap()
        row = self.row("PHZ-0002")
        expect(row.locator(".rm-bar")).to_have_count(0)
        expect(row.locator(".rm-dot")).to_have_attribute("data-at", day(20))

    def test_milestones_are_diamonds_on_their_dates_and_done_ones_look_done(self):
        self.roadmap()
        row = self.row("PHZ-0001")
        expect(row.locator(".rm-ms")).to_have_count(2)                                    # the ordinary item is not a milestone
        expect(row.locator(f'.rm-ms[data-at="{day(30)}"]')).to_have_attribute("data-done", "0")
        expect(row.locator(f'.rm-ms[data-at="{day(-10)}"]')).to_have_attribute("data-done", "1")
        self.assertIn("Beta fechado", row.locator(f'.rm-ms[data-at="{day(30)}"]').get_attribute("title"))

    def test_an_estimate_in_the_past_on_an_open_theme_is_flagged_overdue_but_a_done_theme_is_not(self):
        self.db.themes["PHZ-0002"]["due_date"] = day(-5)
        self.roadmap()
        expect(self.row("PHZ-0002").locator('[data-flag="overdue"]')).to_have_text("Atrasado")
        expect(self.row("PHZ-0003").locator('[data-flag="overdue"]')).to_have_count(0)
        expect(self.row("PHZ-0001").locator('[data-flag="overdue"]')).to_have_count(0)

    def test_a_standalone_task_is_on_the_roadmap(self):
        self.roadmap()
        expect(self.row("PHZ-0010").locator(".rm-bar")).to_have_attribute("data-s", "at_risk")

    def test_a_change_of_date_on_a_theme_shows_on_the_roadmap(self):
        self.roadmap()
        self.db.themes["PHZ-0002"]["start_date"] = day(-15)
        self.db.themes["PHZ-0004"]["due_date"] = day(90)
        self.roadmap()
        expect(self.row("PHZ-0002").locator(".rm-bar")).to_have_attribute("data-from", day(-15))
        expect(self.row("PHZ-0004")).to_have_count(1)
        expect(self.page.get_by_role("region", name="Sem datas")).to_have_count(0)

    def test_a_theme_with_only_a_milestone_date_is_on_the_timeline(self):
        self.db.items.append({"id": "m3", "theme_id": "PHZ-0004", "title": "Piloto", "owner": None, "col": "todo", "due_date": day(15), "milestone": True, "created_at": "x"})
        self.roadmap()
        expect(self.row("PHZ-0004").locator(".rm-ms")).to_have_count(1)

    def test_filters_by_status_front_tag_and_owner(self):
        self.roadmap()
        shown = lambda: self.page.locator(".rm-row[data-theme]").evaluate_all("els => els.map(e => e.dataset.theme)")  # noqa: E731
        self.page.get_by_role("button", name="No prazo").click()
        self.assertEqual(shown(), ["PHZ-0001"])
        self.page.get_by_role("button", name="Todos").click()
        self.page.get_by_label("Frente").select_option(label="Payments")
        self.assertEqual(shown(), ["PHZ-0003", "PHZ-0002"])
        self.page.get_by_label("Frente").select_option(index=0)
        self.page.get_by_label("Etiqueta").select_option(label="#china")
        self.assertEqual(shown(), ["PHZ-0001"])
        self.page.get_by_label("Etiqueta").select_option(index=0)
        self.page.get_by_label("Responsável").select_option(label="Ana")
        self.assertEqual(shown(), ["PHZ-0002"])

    def test_a_filter_with_no_match_says_so(self):
        self.roadmap()
        self.page.get_by_role("button", name="Cancelado").click()
        expect(self.page.get_by_text("Nada para mostrar com esses filtros.")).to_be_visible()

    def test_a_row_opens_the_theme(self):
        self.roadmap()
        self.row("PHZ-0001").locator("a.rm-label").click()
        expect(self.page).to_have_url(self.base + "/themes/PHZ-0001/")

    def test_reader_mode_shows_the_same_roadmap(self):
        self.roadmap("?mode=reader")
        expect(self.row("PHZ-0001")).to_be_visible()

    def test_the_header_links_to_the_roadmap(self):
        self.page.goto(self.base + "/themes/")
        self.page.get_by_role("link", name="Roadmap").click()
        expect(self.page).to_have_url(self.base + "/roadmap/")

    def test_with_no_themes_at_all_the_page_still_loads(self):
        for t in list(self.db.themes):
            del self.db.themes[t]
        self.page.goto(self.base + "/roadmap/")
        expect(self.page.get_by_text("Nada para mostrar com esses filtros.")).to_be_visible()


if __name__ == "__main__":
    unittest.main()
