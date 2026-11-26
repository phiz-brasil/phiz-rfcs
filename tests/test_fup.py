"""The FUP's data (docs/spec/v2/fup.md, supabase/migrations/20261205000000_fup.sql), against the mirror in tests/fake_themes.py."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fake_supabase import FakeSupabase  # noqa: E402
from fake_themes import Invalid  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
MIGRATION = ROOT / "supabase" / "migrations" / "20261205000000_fup.sql"


def agenda(*themes, on=True):
    return [{"theme": t, "kind": "discuss", "on": on, "star": False} for t in themes]


class FupDataTest(unittest.TestCase):
    def setUp(self):
        self.db = FakeSupabase()
        self.db.seed_theme("PHZ-0001", "api-platform", status="on_track")
        self.db.seed_theme("PHZ-0004", "pop")
        self.db.seed_theme("PHZ-0009", "outros", kind="task")

    def new(self, **p):
        return self.db.save_fup(None, {"title": "FUP 25/nov", "held_on": "2026-11-25", **p}, "Pedro")["id"]

    def test_a_fup_needs_a_title_and_a_name(self):
        with self.assertRaises(Invalid):
            self.db.save_fup(None, {"title": "  "}, "Pedro")
        with self.assertRaises(Invalid):
            self.db.save_fup(None, {"title": "FUP"}, " ")
        fid = self.new()
        self.assertEqual(self.db.fups[0]["id"], fid)
        self.assertEqual((self.db.fups[0]["agenda"], self.db.fups[0]["log"]), ([], []))

    def test_the_agenda_and_the_records_are_checked(self):
        fid = self.new()
        for bad in ([{"theme": "PHZ-1", "kind": "discuss", "on": True, "star": False}], [{"theme": "PHZ-0001", "kind": "talk", "on": True, "star": False}],
                    [{"theme": "PHZ-0001", "kind": "inform", "on": "yes", "star": False}], {"theme": "PHZ-0001"}):
            with self.subTest(bad=bad), self.assertRaises(Invalid):
                self.db.save_fup(fid, {"agenda": bad}, "Pedro")
        for bad in ([{"theme": "PHZ-0001", "type": "task", "text": "x", "progress": "todo"}], [{"theme": "PHZ-0001", "type": "note", "text": " ", "progress": "todo"}],
                    [{"theme": "PHZ-0001", "type": "note", "text": "x", "progress": "later"}], [{"theme": "PHZ-0001", "type": "action", "text": "x", "progress": "todo", "due": "27/11"}]):
            with self.subTest(bad=bad), self.assertRaises(Invalid):
                self.db.save_fup(fid, {"log": bad}, "Pedro")
        self.db.save_fup(fid, {"agenda": agenda("PHZ-0001", "PHZ-0004"), "log": [{"theme": "PHZ-0001", "type": "note", "text": "ok", "progress": "todo"}]}, "Pedro")
        self.assertEqual(len(self.db.fups[0]["agenda"]), 2)

    def test_closing_writes_one_weekly_update_per_theme_with_records(self):
        log = [{"theme": "PHZ-0001", "type": "decision", "text": "A troca para a nova API é transparente", "progress": "done"},
               {"theme": "PHZ-0001", "type": "action", "text": "Definir a janela de 24h", "progress": "todo", "due": "2026-11-27"},
               {"theme": "PHZ-0001", "type": "note", "text": "Gleison apresenta o plano", "progress": "todo"},
               {"theme": "PHZ-0004", "type": "action", "text": "Falar com Diegão", "progress": "doing"}]
        fid = self.new(agenda=agenda("PHZ-0001", "PHZ-0004", "PHZ-0009"), log=log)
        res = self.db.close_fup(fid, "Pedro")
        self.assertEqual(res["updates"], 2)
        ups = {u["theme_id"]: u for u in self.db.updates}
        self.assertEqual(set(ups), {"PHZ-0001", "PHZ-0004"})
        self.assertEqual(ups["PHZ-0001"]["progress"], {"pt": "Tratado no FUP de 25/11/2026.", "en": "Discussed in the FUP of 25/11/2026.", "zh": "已在 25/11/2026 的 FUP 会议上讨论。"})
        self.assertEqual(ups["PHZ-0001"]["advanced"], {"pt": "Decidido: A troca para a nova API é transparente\nGleison apresenta o plano"})
        self.assertEqual(ups["PHZ-0001"]["next_step"], {"pt": "Definir a janela de 24h (até 27/11)"})
        self.assertEqual(ups["PHZ-0004"]["advanced"], {})
        self.assertEqual(self.db.themes["PHZ-0001"]["status"], "on_track")
        snap = self.db.fups[0]["snapshot"]
        self.assertEqual(snap["statuses"], {"PHZ-0001": "on_track", "PHZ-0004": "not_started", "PHZ-0009": "not_started"})
        self.assertEqual((snap["log"], snap["closed_by"]), (log, "Pedro"))

    def test_a_closed_fup_refuses_changes(self):
        fid = self.new()
        self.db.close_fup(fid, "Pedro")
        self.assertEqual(self.db.updates, [])
        with self.assertRaises(Invalid):
            self.db.save_fup(fid, {"title": "outro"}, "Pedro")
        with self.assertRaises(Invalid):
            self.db.close_fup(fid, "Pedro")

    def test_a_hidden_theme_is_skipped_on_closing(self):
        self.db.themes["PHZ-0004"]["hidden"] = True
        fid = self.new(log=[{"theme": "PHZ-0004", "type": "note", "text": "x", "progress": "todo"}])
        self.assertEqual(self.db.close_fup(fid, "Pedro")["updates"], 0)


class FupMigrationTest(unittest.TestCase):
    def test_the_migration_has_the_table_the_functions_and_the_member_lock(self):
        sql = MIGRATION.read_text(encoding="utf-8")
        for needle in ("create table if not exists public.fup_meetings", "function public.save_fup(p_id uuid, p jsonb, p_by text)",
                       "function public.close_fup(p_id uuid, p_by text)", "perform public.post_theme_update(", "if f.closed_at is not null then raise exception 'fup closed'",
                       "create policy members_only on public.fup_meetings as restrictive", "grant execute on function public.save_fup(uuid, jsonb, text), public.close_fup(uuid, text) to authenticated"):
            with self.subTest(needle=needle):
                self.assertIn(needle, sql)
        self.assertNotIn("to anon", sql.split("revoke all on function public.save_fup")[1])


class FupCloseMessageMigrationTest(unittest.TestCase):
    """The fixed sentence of the closing is written in the three languages by the function (the machine translation made it "Treaty on the FUP")."""
    SQL = (ROOT / "supabase" / "migrations" / "20261206000000_fup_close_message.sql").read_text(encoding="utf-8")

    def test_the_progress_sentence_carries_pt_en_and_zh(self):
        self.assertIn("'pt', 'Tratado no FUP de ' || day", self.SQL)
        self.assertIn("'en', 'Discussed in the FUP of ' || day", self.SQL)
        self.assertIn("'zh', '已在 ' || day", self.SQL)

    def test_it_only_recreates_close_fup_and_keeps_its_grants(self):
        self.assertIn("create or replace function public.close_fup(p_id uuid, p_by text)", self.SQL)
        self.assertNotIn("create table", self.SQL)
        self.assertIn("grant execute on function public.close_fup(uuid, text) to authenticated", self.SQL)
        self.assertIn("revoke all on function public.close_fup(uuid, text) from public, anon", self.SQL)


class FupRemoveTestsMigrationTest(unittest.TestCase):
    """The two FUPs made to validate writing in production are removed by id, and only if still titled TESTE; nothing else is touched."""
    SQL = (ROOT / "supabase" / "migrations" / "20261207000000_fup_remove_tests.sql").read_text(encoding="utf-8")

    def test_it_deletes_exactly_two_fups_by_id_and_title(self):
        self.assertEqual(self.SQL.count("delete from"), 1)
        self.assertIn("delete from public.fup_meetings", self.SQL)
        for fid in ("1b345f9f-cf92-4e6a-923a-41af26a4744a", "c00b76aa-cdae-4dd8-9a48-869977bb58d1"):
            self.assertIn(fid, self.SQL)
        self.assertIn("title like 'TESTE%'", self.SQL)

    def test_it_touches_nothing_else(self):
        for word in ("drop ", "truncate", "alter ", "theme_updates", "themes"):
            self.assertNotIn(word, self.SQL.split("\n", 2)[2])


class CleanPhz0015MigrationTest(unittest.TestCase):
    """The test data left on PHZ-0015 is deleted, scoped by theme and author or week; the theme itself and the audit log stay."""
    SQL = (ROOT / "supabase" / "migrations" / "20261208000000_clean_theme_test_data.sql").read_text(encoding="utf-8")
    CODE = "\n".join(l for l in SQL.splitlines() if not l.startswith("--"))

    def test_every_delete_is_scoped_to_the_theme_and_to_the_test_author_or_week(self):
        deletes = [x for x in self.CODE.split(";") if "delete from" in x]
        self.assertEqual(len(deletes), 3)
        for d in deletes:
            with self.subTest(d.strip()[:40]):
                self.assertIn("theme_id = 'PHZ-0015'", d)
                self.assertTrue("created_by = 'Claude (teste)'" in d or "week = '2026-W48'" in d)

    def test_it_empties_only_that_themes_progress_and_never_deletes_the_theme_or_its_events(self):
        self.assertIn("update public.themes set progress = '{}'::jsonb", self.CODE)
        self.assertIn("where id = 'PHZ-0015'", self.CODE)
        for word in ("delete from public.themes", "theme_events", "drop ", "truncate"):
            self.assertNotIn(word, self.CODE)


if __name__ == "__main__":
    unittest.main()
