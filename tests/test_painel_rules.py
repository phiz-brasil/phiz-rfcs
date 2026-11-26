"""The rules of the Painel (docs/spec/v2/redesign.md): apps/web/lib/painel.ts run by Node (it is pure), the new data rules of
supabase/migrations/20261209000000_redesign.sql in the fake Supabase (tests/fake_themes.py), and the migration itself."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fake_supabase import FakeSupabase  # noqa: E402
from fake_themes import Invalid  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
MIGRATION = ROOT / "supabase" / "migrations" / "20261209000000_redesign.sql"


def js(expr, data=None):
    code = ("import * as P from './apps/web/lib/painel.ts'; const D = JSON.parse(process.argv[1]);"
            f"console.log(JSON.stringify({expr}));")
    out = subprocess.run(["node", "--input-type=module", "-e", code, json.dumps(data or {})], cwd=ROOT, capture_output=True, text=True)
    if out.returncode:
        raise AssertionError(out.stderr)
    return json.loads(out.stdout)


class Quarters(unittest.TestCase):
    def test_five_quarters_from_the_one_of_today(self):
        qs = js("P.quarters('2026-11-26', 5)")
        self.assertEqual([q["key"] for q in qs], ["2026-Q4", "2027-Q1", "2027-Q2", "2027-Q3", "2027-Q4"])
        self.assertEqual((qs[0]["start"], qs[0]["end"]), ("2026-10-01", "2026-12-31"))
        self.assertEqual((qs[1]["start"], qs[1]["end"]), ("2027-01-01", "2027-03-31"))
        self.assertEqual(js("P.quarterOf('2028-02-29').end"), "2028-03-31")

    def test_a_period_becomes_a_bar_clipped_to_the_timeline(self):
        qs = "P.quarters('2026-11-26', 5)"
        self.assertEqual(js(f"P.barOf({qs}, {{start: '2026-11-01', due: '2027-05-10'}})"), [0, 2])
        self.assertEqual(js(f"P.barOf({qs}, {{start: '2025-01-01', due: '2026-10-02'}})"), [0, 0])         # starts before the timeline
        self.assertEqual(js(f"P.barOf({qs}, {{start: null, due: '2027-02-01'}})"), [1, 1])                  # one date alone
        self.assertIsNone(js(f"P.barOf({qs}, {{start: '2025-01-01', due: '2025-03-01'}})"))                  # all before
        self.assertIsNone(js(f"P.barOf({qs}, {{start: null, due: null}})"))
        self.assertEqual(js(f"P.barOf({qs}, {{start: '2027-12-01', due: '2029-01-01'}})"), [4, 4])         # runs past the end

    def test_a_click_on_a_quarter_sets_stretches_or_shrinks_the_period_at_quarter_bounds(self):
        qs = "P.quarters('2026-11-26', 5)"
        self.assertEqual(js(f"P.stretch({qs}, {{start: null, due: null}}, 2)"), {"start_date": "2027-04-01", "due_date": "2027-06-30"})
        self.assertEqual(js(f"P.stretch({qs}, {{start: '2027-01-10', due: '2027-02-01'}}, 3)"), {"start_date": "2027-01-01", "due_date": "2027-09-30"})
        self.assertEqual(js(f"P.stretch({qs}, {{start: '2027-01-10', due: '2027-08-01'}}, 0)"), {"start_date": "2026-10-01", "due_date": "2027-09-30"})
        self.assertEqual(js(f"P.stretch({qs}, {{start: '2026-10-10', due: '2027-08-01'}}, 1)"), {"start_date": "2026-10-01", "due_date": "2027-03-31"})

    def test_today_line_position(self):
        self.assertAlmostEqual(js("P.positionOf(P.quarters('2026-10-01', 5), '2026-10-01')"), 0)
        self.assertGreater(js("P.positionOf(P.quarters('2026-11-26', 5), '2026-11-26')"), 10)


class ThemeRules(unittest.TestCase):
    def test_the_period_of_a_theme_is_the_span_of_its_deliveries_else_its_own_dates(self):
        self.assertEqual(js("P.themePeriod({start: '2026-10-01', due: '2027-03-31'}, [{start: '2027-01-01', due: '2027-06-30'}, {start: null, due: '2026-12-15'}])"),
                         {"start": "2026-12-15", "due": "2027-06-30"})
        self.assertEqual(js("P.themePeriod({start: '2026-10-01', due: '2027-03-31'}, [{start: null, due: null}])"), {"start": "2026-10-01", "due": "2027-03-31"})

    def test_the_phase_comes_from_the_pdlc_stage(self):
        self.assertEqual(js("[1,2,3,6,7,8,9,10,null].map(P.phaseOf)"),
                         ["discovery", "discovery", "definition", "definition", "build", "build", "launched", "launched", None])

    def test_filters_combine(self):
        rows = [{"id": "A", "front": "pop", "owner": "Ana", "status": "on_track", "tags": ["china"], "kind": "project"},
                {"id": "B", "front": "payments", "owner": "Bo", "status": "at_risk", "tags": [], "kind": "project"},
                {"id": "C", "front": "payments", "owner": "Ana", "status": "at_risk", "tags": ["china"], "kind": "task"}]
        ids = lambda f, att="false", st="false": js(f"P.applyFilters(D.rows, {{...P.NO_FILTERS, ...D.f}}, {{attention: x => {att}, stale: x => {st}}}).map(x => x.id)",
                                                 {"rows": rows, "f": f})
        self.assertEqual(ids({}), ["A", "B", "C"])
        self.assertEqual(ids({"front": "payments", "owner": "Ana"}), ["C"])
        self.assertEqual(ids({"status": "at_risk", "kind": "project"}), ["B"])
        self.assertEqual(ids({"tag": "china"}), ["A", "C"])
        self.assertEqual(ids({"attention": True}, att="x.status === 'at_risk'"), ["B", "C"])
        self.assertEqual(ids({"stale": True}, st="x.id === 'A'"), ["A"])


class Blocks(unittest.TestCase):
    def test_needs_you_keeps_leadership_or_urgent_orders_urgent_first_then_deadline_and_carries_no_name(self):
        data = {"b": [{"id": "b1", "theme_id": "T1", "what": {"pt": "Fornecedor"}, "due_date": "2026-12-20", "needs_leadership": True, "urgency": "important", "created_at": "1", "owner": "Diretoria"},
                      {"id": "b2", "theme_id": "T2", "what": {"pt": "Contrato"}, "due_date": None, "needs_leadership": False, "urgency": "urgent", "created_at": "2", "owner": "Ana"},
                      {"id": "b3", "theme_id": "T2", "what": {"pt": "Menor"}, "due_date": None, "needs_leadership": False, "urgency": "info", "created_at": "3"},
                      {"id": "b4", "theme_id": "GONE", "what": {"pt": "Oculto"}, "due_date": None, "needs_leadership": True, "urgency": "urgent", "created_at": "4"}],
                "d": [{"id": "d1", "theme_id": "T1", "what": {"pt": "Parceiro"}, "due_date": "2026-12-01", "needs_leadership": True, "urgency": None, "created_at": "5", "decider": "Bo"}]}
        lines = js("P.needsYou(D.b, D.d, new Set(['T1', 'T2']))", data)
        self.assertEqual([x["key"] for x in lines], ["b2", "d1", "b1"])               # urgent; then important by deadline
        self.assertEqual([x["urgency"] for x in lines], ["urgent", "important", "important"])     # no urgency stored: from needs_leadership
        self.assertTrue(all(set(x) == {"key", "theme", "kind", "text", "urgency", "date"} for x in lines))

    def test_latest_decisions_newest_first_with_the_decision_text(self):
        d = [{"id": "x", "theme_id": "T1", "what": {"pt": "Q"}, "decision": {"pt": "Sim"}, "decided_at": "2026-10-29T10:00:00Z"},
             {"id": "y", "theme_id": "T1", "what": {"pt": "Escopo"}, "decision": {}, "decided_at": "2026-11-02T10:00:00Z"},
             {"id": "z", "theme_id": "T9", "what": {"pt": "Fora"}, "decision": {"pt": "Fora"}, "decided_at": "2026-11-20T10:00:00Z"}]
        lines = js("P.latestDecisions(D.d, new Set(['T1']))", {"d": d})
        self.assertEqual([(x["key"], x["text"], x["date"]) for x in lines], [("y", {"pt": "Escopo"}, "2026-11-02"), ("x", {"pt": "Sim"}, "2026-10-29")])

    def test_next_milestones_in_ninety_days_by_date(self):
        data = {"t": [{"id": "T1", "due_date": "2027-01-15", "open": True}, {"id": "T2", "due_date": "2026-12-01", "open": False}, {"id": "T3", "due_date": "2027-06-01", "open": True}],
                "m": [{"id": "m1", "theme_id": "T1", "title": "Piloto", "due_date": "2026-12-10", "col": "todo"},
                      {"id": "m2", "theme_id": "T1", "title": "Feito", "due_date": "2026-12-11", "col": "done"},
                      {"id": "m3", "theme_id": "T1", "title": "Velho", "due_date": "2026-11-01", "col": "todo"}]}
        lines = js("P.nextMilestones(D.t, D.m, '2026-11-26', 90)", data)
        self.assertEqual([(x["key"], x["date"], x["urgency"]) for x in lines], [("m1", "2026-12-10", "planned"), ("due-T1", "2027-01-15", "planned")])


class DataRules(unittest.TestCase):
    """The fake mirrors supabase/migrations/20261209000000_redesign.sql."""
    def setUp(self):
        self.db = FakeSupabase()
        self.db.seed_theme("PHZ-0001", "pop")
        self.db.seed_theme("PHZ-0010", "outros", kind="task")

    def test_a_delivery_has_a_period_and_a_change_of_it_is_an_event(self):
        iid = self.db.save_theme_item("PHZ-0001", None, {"title": "Mídia", "start_date": "2027-01-01", "due_date": "2027-03-31"}, "Ana")["id"]
        row = next(i for i in self.db.items if i["id"] == iid)
        self.assertEqual((row["start_date"], row["due_date"]), ("2027-01-01", "2027-03-31"))
        self.db.save_theme_item("PHZ-0001", iid, {"start_date": "2026-10-01"}, "Ana")
        self.assertEqual((row["start_date"], row["due_date"]), ("2026-10-01", "2027-03-31"))
        ev = self.db.events[-1]
        self.assertEqual((ev["field"], ev["item_id"], ev["old_value"]["start_date"], ev["new_value"]["start_date"]), ("item_period", iid, "2027-01-01", "2026-10-01"))
        n = len(self.db.events)
        self.db.save_theme_item("PHZ-0001", iid, {"title": "Mídia e arquivos"}, "Ana")
        self.assertEqual(len(self.db.events), n)                                      # no period change, no event

    def test_a_period_that_ends_before_it_starts_is_refused(self):
        with self.assertRaises(Invalid):
            self.db.save_theme_item("PHZ-0001", None, {"title": "X", "start_date": "2027-04-01", "due_date": "2027-03-31"}, "Ana")
        iid = self.db.save_theme_item("PHZ-0001", None, {"title": "Y", "due_date": "2027-03-31"}, "Ana")["id"]
        with self.assertRaises(Invalid):
            self.db.save_theme_item("PHZ-0001", iid, {"start_date": "2027-06-01"}, "Ana")

    def test_a_task_theme_has_no_deliveries(self):
        with self.assertRaises(Invalid):
            self.db.save_theme_item("PHZ-0010", None, {"title": "X"}, "Ana")

    def test_urgency_is_saved_defaulted_from_needs_leadership_and_validated(self):
        b = self.db.save_theme_blocker("PHZ-0001", None, {"what": {"pt": "A"}, "needs_leadership": True}, "Ana")["id"]
        d = self.db.save_theme_decision("PHZ-0001", None, {"what": {"pt": "B"}}, "Ana")["id"]
        u = self.db.save_theme_decision("PHZ-0001", None, {"what": {"pt": "C"}, "urgency": "urgent"}, "Ana")["id"]
        by = {r["id"]: r["urgency"] for r in self.db.blockers + self.db.decisions}
        self.assertEqual((by[b], by[d], by[u]), ("important", "info", "urgent"))
        self.db.save_theme_blocker("PHZ-0001", b, {"urgency": "urgent"}, "Ana")
        self.assertEqual(next(r for r in self.db.blockers if r["id"] == b)["urgency"], "urgent")
        with self.assertRaises(Invalid):
            self.db.save_theme_blocker("PHZ-0001", None, {"what": {"pt": "D"}, "urgency": "alta"}, "Ana")


class Migration(unittest.TestCase):
    def setUp(self):
        self.sql = MIGRATION.read_text(encoding="utf-8")

    def test_it_adds_the_period_of_deliveries_with_its_rule(self):
        self.assertIn("alter table public.theme_items add column if not exists start_date date", self.sql)
        self.assertIn("check (start_date is null or due_date is null or start_date <= due_date)", self.sql)
        self.assertIn("raise exception 'invalid period'", self.sql)
        self.assertIn("'item_period'", self.sql)

    def test_it_adds_urgency_with_its_check_default_and_one_time_backfill(self):
        for table in ("theme_blockers", "theme_decisions"):
            self.assertIn(f"alter table public.{table} add column if not exists urgency text not null default 'info'", self.sql)
            self.assertIn(f"update public.{table} set urgency = 'important' where needs_leadership and urgency = 'info'", self.sql)
        self.assertIn("check (urgency in ('urgent', 'important', 'info'))", self.sql)
        self.assertIn("return case when lead then 'important' else 'info' end", self.sql)

    def test_it_is_idempotent_and_keeps_the_signatures(self):
        self.assertNotRegex(self.sql, r"(?im)^\s*create (table|function) (?!or replace)(?!if not exists)")
        self.assertIn("if not exists (select 1 from pg_constraint where conname = 'theme_items_period_check')", self.sql)
        for sig in ("save_theme_item(p_theme text, p_item uuid, p jsonb, p_by text)", "save_theme_blocker(p_theme text, p_id uuid, p jsonb, p_by text)",
                    "save_theme_decision(p_theme text, p_id uuid, p jsonb, p_by text)"):
            self.assertIn("create or replace function public." + sig, self.sql)
        self.assertIn("revoke all on function public.theme_urgency(jsonb, boolean) from public, anon, authenticated", self.sql)


if __name__ == "__main__":
    unittest.main()
