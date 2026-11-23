"""apps/web/lib/metrics.ts on fixed event histories, with the expected values worked out by hand (docs/spec/v2/flow-and-metrics.md, Acceptance).
The module is pure, so Node runs it directly. Calendar of the histories: 2026-01-01 is a Thursday; every event is at 12:00 UTC."""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def js(expr, data=None):
    code = ("import * as M from './apps/web/lib/metrics.ts';"
            "const D = JSON.parse(process.argv[1]); const A = D.themes ? M.tracksOf(D.themes, D.events) : null;"
            f"console.log(JSON.stringify({expr}));")
    out = subprocess.run(["node", "--input-type=module", "-e", code, json.dumps(data or {})], cwd=ROOT, capture_output=True, text=True)
    if out.returncode:
        raise AssertionError(out.stderr)
    return json.loads(out.stdout)


def at(day, hour=12):
    return f"2026-{day[:2]}-{day[3:]}T{hour:02d}:00:00Z"        # "01-03" -> 2026-01-03T12:00:00Z


def theme(tid, created, stage, route="full", resolution=None, front="payments", tags=(), owner=None):
    return {"id": tid, "kind": "project", "front": front, "owner": owner, "tags": list(tags), "route": route, "stage": stage, "status": "on_track",
            "resolution": resolution, "created_at": at(created)}


def move(tid, day, frm, to, gates=()):
    return {"theme_id": tid, "item_id": None, "at": at(day), "field": "move", "old_value": None,
            "new_value": {"from_stage": frm, "to_stage": to, "open_gates": list(gates), "reason": None}}


def stage(tid, day, frm, to):
    return {"theme_id": tid, "item_id": None, "at": at(day), "field": "stage", "old_value": frm, "new_value": to}


def resolve(tid, day, kind, hour=12):
    return {"theme_id": tid, "item_id": None, "at": at(day, hour), "field": "resolution", "old_value": None, "new_value": kind}


# H1, full route: 1 → 2 (Jan 3) → 4, skipping 3 (Jan 10) → 7 (Jan 20) → 8 (Feb 1) → back to 7 (Feb 5) → 8 (Feb 10) → 10 (Feb 15) → done (Feb 20)
H1 = [theme("H1", "01-01", 10, resolution="done"),
      move("H1", "01-03", 1, 2), move("H1", "01-10", 2, 4, ["04-prd"]), stage("H1", "01-20", 4, 7), move("H1", "02-01", 7, 8, ["07-pipeline", "07-selftest"]),
      move("H1", "02-05", 8, 7), move("H1", "02-10", 7, 8), move("H1", "02-15", 8, 10), resolve("H1", "02-20", "done")]
# H2, bug route (enters at 06): 6 → 7 (Jan 8) → 8 (Jan 12) → done (Jan 15)
H2 = [theme("H2", "01-05", 8, route="bug", resolution="done"), move("H2", "01-08", 6, 7), move("H2", "01-12", 7, 8), resolve("H2", "01-15", "done")]
# H3, P0 (enters at 07): done a day and a half after it was created
H3 = [theme("H3", "01-10", 7, route="p0", resolution="done"), resolve("H3", "01-11", "done")]
H3[1]["at"] = "2026-01-11T00:00:00Z"                                      # created Jan 10 12:00, done Jan 11 00:00 = 0.5 day
# H4, declined at 03: 1 → 2 (Jan 2) → 3 (Jan 4) → declined (Jan 6)
H4 = [theme("H4", "01-01", 3, resolution="declined"), move("H4", "01-02", 1, 2), move("H4", "01-04", 2, 3), resolve("H4", "01-06", "declined")]
# H5, still open at 02 since Jan 3
H5 = [theme("H5", "01-01", 2), move("H5", "01-03", 1, 2)]
# H6, left 01 only on Jan 7 (4 business days after it was created on a Thursday)
H6 = [theme("H6", "01-01", 2), move("H6", "01-07", 1, 2)]


def hist(*parts):
    themes = [p[0] for p in parts]
    events = [e for p in parts for e in p[1:]]
    return {"themes": themes, "events": events}


def one(part):
    return hist(part)


@unittest.skipUnless(shutil.which("node"), "node is not installed")
class MetricsTest(unittest.TestCase):
    # -- the stage history ------------------------------------------------------------------------------------------
    def test_a_stage_history_is_replayed_from_the_events_and_a_backward_move_opens_a_new_period(self):
        spans = js("A[0].spans.map(s => [s.stage, s.from, s.to].map(x => typeof x === 'number' && x > 1e6 ? M.dayKey(x) : x))", one(H1))
        self.assertEqual(spans, [[1, "2026-01-01", "2026-01-03"], [2, "2026-01-03", "2026-01-10"], [4, "2026-01-10", "2026-01-20"], [7, "2026-01-20", "2026-02-01"],
                                 [8, "2026-02-01", "2026-02-05"], [7, "2026-02-05", "2026-02-10"], [8, "2026-02-10", "2026-02-15"], [10, "2026-02-15", "2026-02-20"]])

    def test_a_move_inside_a_stage_is_not_a_stage_change(self):
        d = one(H5)
        d["events"].append(move("H5", "01-08", 2, 2))
        self.assertEqual(js("A[0].spans.length", d), 2)

    def test_a_skipped_stage_has_no_period(self):
        self.assertEqual(js("M.timeInStage(A[0], 0)[3] ?? 0", one(H1)), 0)

    # -- times ------------------------------------------------------------------------------------------------------
    def test_lead_delivery_and_cycle_time_of_a_full_route_theme(self):
        r = js("[M.leadTime(A[0]), M.deliveryTime(A[0]), M.cycleTime(A[0])]", one(H1))
        self.assertEqual(r, [50, 41, 31])               # Jan 1 → Feb 20; Jan 10 → Feb 20; Jan 20 → Feb 20

    def test_a_bug_route_theme_has_no_delivery_time_and_its_cycle_starts_at_06(self):
        self.assertEqual(js("[M.leadTime(A[0]), M.deliveryTime(A[0]), M.cycleTime(A[0])]", one(H2)), [10, None, 10])

    def test_a_p0_theme_cycle_starts_at_07(self):
        self.assertEqual(js("[M.leadTime(A[0]), M.deliveryTime(A[0]), M.cycleTime(A[0])]", one(H3)), [0.5, None, 0.5])

    def test_a_theme_declined_at_03_has_no_lead_time_and_is_not_throughput(self):
        d = one(H4)
        self.assertEqual(js("[M.leadTime(A[0]), M.cycleTime(A[0]), A[0].closeKind, M.throughputByWeek(A)]", d), [None, None, "declined", {}])

    def test_time_in_stage_adds_up_every_period_and_an_open_period_runs_to_now(self):
        t = js("M.timeInStage(A[0], 0)", one(H1))
        self.assertEqual({k: t[k] for k in sorted(t, key=int)}, {"1": 2, "2": 7, "4": 10, "7": 17, "8": 9, "10": 5})   # 7: 12 + 5 days; 8: 4 + 5 days
        now = Date_ms("2026-01-13T12:00:00Z")
        self.assertEqual(js(f"M.timeInStage(A[0], {now})", one(H5)), {"1": 2, "2": 10})

    def test_stage_statistics_use_the_median_and_the_nearest_rank_85th_percentile(self):
        d = hist(H1, H4)
        r = js("M.stageStats(A, 0)[2]", d)
        self.assertEqual(r, {"n": 2, "median": 4.5, "p85": 7})     # stage 2: H1 7 days, H4 2 days

    def test_percentiles_of_a_list(self):
        self.assertEqual(js("[M.median([3,1,2]), M.median([4,1,3,2]), M.p85([1,2,3,4,5,6,7,8,9,10]), M.p85([5]), M.median([])]"), [2, 2.5, 9, 5, None])

    # -- throughput, WIP, aging -------------------------------------------------------------------------------------
    def test_throughput_counts_done_themes_per_iso_week(self):
        r = js("M.throughputByWeek(A)", hist(H1, H2, H3, H4, H5))
        self.assertEqual(r, {"2026-W08": 1, "2026-W03": 1, "2026-W02": 1})

    def test_wip_counts_open_themes_per_stage(self):
        self.assertEqual(js("M.wipByStage(A)", hist(H1, H4, H5, H6)), {"2": 2})

    def test_aging_compares_the_open_themes_with_the_85th_percentile_of_the_finished_ones(self):
        now = Date_ms("2026-01-13T12:00:00Z")
        r = js(f"M.agingWip(A, {now})", hist(H1, H4, H5))
        self.assertEqual(r, [{"id": "H5", "stage": 2, "inStage": 10, "sinceKickoff": None, "p85": 7, "over": True}])

    def test_aging_since_kickoff_counts_from_the_first_entry_into_04(self):
        d = hist((theme("K", "01-01", 5), move("K", "01-05", 1, 4), move("K", "01-12", 4, 5)))
        now = Date_ms("2026-01-20T12:00:00Z")
        r = js(f"M.agingWip(A, {now})[0]", d)
        self.assertEqual((r["inStage"], r["sinceKickoff"], r["over"]), (8, 15, False))

    # -- cumulative flow --------------------------------------------------------------------------------------------
    def test_the_cfd_matches_a_hand_built_table_day_by_day(self):
        r = js("M.cfd(A, '2026-01-01', '2026-01-06').map(x => [x.day.slice(8), x.counts])", hist(H1, H4))
        self.assertEqual(r, [["01", {"1": 2}], ["02", {"1": 1, "2": 1}], ["03", {"2": 2}], ["04", {"2": 1, "3": 1}], ["05", {"2": 1, "3": 1}], ["06", {"2": 1, "closed": 1}]])

    def test_a_backward_move_shows_in_the_cfd_on_the_day_it_happened(self):
        r = js("M.cfd(A, '2026-02-04', '2026-02-06').map(x => x.counts)", one(H1))
        self.assertEqual(r, [{"8": 1}, {"7": 1}, {"7": 1}])

    def test_the_cfd_does_not_count_a_theme_before_it_was_created(self):
        self.assertEqual(js("M.cfd(A, '2025-12-30', '2026-01-01').map(x => x.counts)", one(H5)), [{}, {}, {"1": 1}])

    # -- blocked time, open-gate moves, triage ------------------------------------------------------------------------
    def test_blocked_time_counts_overlapping_blockers_once_and_is_a_share_of_the_cycle_time(self):
        d = one(H1)
        d["blockers"] = [{"theme_id": "H1", "created_at": at("01-22"), "resolved_at": at("01-25")}, {"theme_id": "H1", "created_at": at("01-24"), "resolved_at": at("01-27")},
                         {"theme_id": "H1", "created_at": at("01-01"), "resolved_at": at("01-05")}]        # the last one is before the cycle started
        r = js("M.blockedInCycle(A[0], D.blockers)", d)
        self.assertEqual(r["days"], 5)
        self.assertAlmostEqual(r["share"], 5 / 31)

    def test_an_open_blocker_runs_to_the_end_of_the_window(self):
        self.assertEqual(js("M.blockedMs([{theme_id:'x', created_at:'2026-01-01T00:00:00Z', resolved_at:null}], Date.parse('2026-01-02T00:00:00Z'), Date.parse('2026-01-04T00:00:00Z')) / M.DAY"), 2)

    def test_moves_with_open_gates_are_counted_per_stage_left(self):
        r = js("M.openGateMoves(D.events)", hist(H1, H2))
        self.assertEqual(r, {"byStage": {"2": 1, "7": 1}, "total": 2, "moves": 7})
        # forward `move` events: H1 has 5 (1→2, 2→4, 7→8, 7→8, 8→10; the move back and the `stage` edit 4→7 are not counted), H2 has 2

    def test_triage_is_the_share_of_themes_that_left_01_within_two_business_days(self):
        r = js("M.triage(A)", hist(H1, H4, H5, H6))
        self.assertEqual(r, {"n": 4, "within": 3, "share": 0.75})        # H6 left after 4 business days; the others after 1

    def test_business_days_skip_weekends(self):
        r = js("[M.businessDaysBetween(Date.parse('2026-01-02T12:00:00Z'), Date.parse('2026-01-05T12:00:00Z')), M.businessDaysBetween(Date.parse('2026-01-01T12:00:00Z'), Date.parse('2026-01-03T12:00:00Z'))]")
        self.assertEqual(r, [1, 1])           # Fri → Mon is one business day; Thu → Sat is one (the Friday)

    # -- estimated themes -------------------------------------------------------------------------------------------
    def test_a_theme_with_no_recorded_history_is_marked_estimated(self):
        d = hist((theme("IMP", "01-01", 5),), (theme("NEW", "01-01", 1),), (theme("IMPDONE", "01-01", 10, resolution="done"),))
        self.assertEqual(js("A.map(t => [t.theme.id, t.estimated])", d), [["IMP", True], ["NEW", False], ["IMPDONE", True]])

    # -- execution items --------------------------------------------------------------------------------------------
    def test_item_lead_and_cycle_time_and_throughput(self):
        items = [{"id": "A", "theme_id": "T", "col": "done", "created_at": at("01-01")}, {"id": "B", "theme_id": "T", "col": "done", "created_at": at("01-01")}]
        ev = [item_ev("A", "01-02", "todo", "doing"), item_ev("A", "01-04", "doing", "blocked"), item_ev("A", "01-05", "blocked", "doing"), item_ev("A", "01-08", "doing", "done"),
              item_ev("B", "01-03", "todo", "done")]
        d = {"items": items, "events": ev}
        self.assertEqual(js("M.itemTracks(D.items, D.events).map(t => [M.itemLead(t), M.itemCycle(t)])", d), [[7, 6], [2, None]])
        self.assertEqual(js("M.itemThroughputByWeek(M.itemTracks(D.items, D.events))", d), {"2026-W02": 1, "2026-W01": 1})      # A done Thu Jan 8, B done Sat Jan 3

    def test_item_cfd_replays_the_column_changes(self):
        items = [{"id": "A", "theme_id": "T", "col": "done", "created_at": at("01-01")}]
        ev = [item_ev("A", "01-02", "todo", "doing"), item_ev("A", "01-04", "doing", "blocked"), item_ev("A", "01-05", "blocked", "doing"), item_ev("A", "01-08", "doing", "done")]
        r = js("M.itemCfd(M.itemTracks(D.items, D.events), '2026-01-01', '2026-01-08').map(x => Object.keys(x.counts)[0])", {"items": items, "events": ev})
        self.assertEqual(r, ["todo", "doing", "doing", "blocked", "doing", "doing", "doing", "done"])

    def test_item_wip_and_aging(self):
        items = [{"id": "A", "theme_id": "T", "col": "doing", "created_at": at("01-01")}, {"id": "B", "theme_id": "T", "col": "todo", "created_at": at("01-01")},
                 {"id": "C", "theme_id": "T", "col": "done", "created_at": at("01-01")}]
        ev = [item_ev("A", "01-02", "todo", "doing"), item_ev("C", "01-03", "todo", "done")]
        now = Date_ms("2026-01-12T12:00:00Z")
        d = {"items": items, "events": ev}
        self.assertEqual(js("M.itemWip(M.itemTracks(D.items, D.events))", d), {"doing": 1, "todo": 1})
        self.assertEqual(js(f"M.itemAging(M.itemTracks(D.items, D.events), {now})", d), [{"id": "A", "theme_id": "T", "col": "doing", "inCol": 10}])


def item_ev(item, day, old, new):
    return {"theme_id": "T", "item_id": item, "at": at(day), "field": "item_col", "old_value": old, "new_value": new}


def Date_ms(iso):
    from datetime import datetime
    return int(datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=__import__("datetime").timezone.utc).timestamp() * 1000)


if __name__ == "__main__":
    unittest.main()
