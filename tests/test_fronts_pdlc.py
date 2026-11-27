"""Redesign, PR 4 (docs/spec/v2/redesign.md, What PR 4 delivers): the fronts the owner named and the name PDLC B2B. The migration is read as text
(tests/test_sql.py already parses it); the point is that no theme loses its front and that running it twice changes nothing more."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MIGRATION = ROOT / "supabase" / "migrations" / "20261210000000_fronts_pdlc.sql"
I18N = ROOT / "apps" / "web" / "lib" / "i18n.ts"


def statements():
    sql = "\n".join(l for l in MIGRATION.read_text(encoding="utf-8").splitlines() if not l.lstrip().startswith("--"))
    return [s.strip() for s in sql.split(";") if s.strip()]


class FrontsMigrationTest(unittest.TestCase):
    def test_the_two_new_fronts_have_a_name_and_scope_in_the_three_languages_and_are_not_inserted_twice(self):
        ins = next(s for s in statements() if s.startswith("insert into public.fronts"))
        for key, pt in (("parcerias-pocs", "Parcerias e POCs"), ("novos-negocios", "Novos negócios")):
            self.assertIn(f"'{key}'", ins)
            self.assertIn(f'"pt":"{pt}"', ins)
        self.assertEqual(len(re.findall(r'"zh":"', ins)), 4)                    # name and scope of each, in Chinese too
        self.assertTrue(ins.endswith("on conflict (key) do nothing"))

    def test_the_order_is_the_one_the_owner_gave(self):
        order = dict(re.findall(r"update public\.fronts set ord = (\d) where key = '([a-z-]+)'", MIGRATION.read_text(encoding="utf-8")))
        self.assertEqual([order[str(i)] for i in range(1, 6)], ["pop", "payments", "mini-apps", "parcerias-pocs", "novos-negocios"])

    def test_api_platform_themes_move_to_pop_with_an_event_before_any_front_is_deleted(self):
        st = statements()
        event = next(i for i, s in enumerate(st) if s.startswith("insert into public.theme_events"))
        move = next(i for i, s in enumerate(st) if s.startswith("update public.themes set front = 'pop'"))
        delete = next(i for i, s in enumerate(st) if s.startswith("delete from public.fronts"))
        self.assertLess(event, move)                                              # the history is written while the old front is still there
        self.assertLess(move, delete)
        self.assertIn("where front = 'api-platform'", st[event])
        self.assertIn("where front = 'api-platform'", st[move])

    def test_a_front_is_deleted_only_when_no_theme_points_at_it_and_only_the_two_that_leave(self):
        delete = next(s for s in statements() if s.startswith("delete from public.fronts"))
        self.assertIn("('api-platform', 'product-center')", delete)
        self.assertIn("not exists (select 1 from public.themes t where t.front = f.key)", delete)
        self.assertNotIn("delete from public.themes", MIGRATION.read_text(encoding="utf-8"))

    def test_pop_takes_the_scope_of_the_apis_once(self):
        upd = next(s for s in statements() if s.startswith("update public.fronts set scope"))
        self.assertIn("where key = 'pop'", upd)
        self.assertIn("not like '%APIs para empresas%'", upd)                     # a second run leaves it alone
        self.assertIn("APIs para empresas", upd)


class PdlcNameTest(unittest.TestCase):
    def test_no_text_of_the_interface_says_v4(self):
        self.assertNotIn("V4", I18N.read_text(encoding="utf-8"))

    def test_the_board_says_pdlc_b2b_in_the_three_languages(self):
        line = next(l for l in I18N.read_text(encoding="utf-8").splitlines() if l.strip().startswith("boardLead:"))
        self.assertEqual(line.count("PDLC B2B"), 3)


if __name__ == "__main__":
    unittest.main()
