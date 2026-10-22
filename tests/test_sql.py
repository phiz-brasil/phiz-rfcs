"""The migrations must at least parse: a syntax error in one would only show up when someone applies it in the Supabase editor.
Needs pglast (requirements-dev.txt); the tests are skipped without it."""
import unittest
from pathlib import Path

try:
    import pglast
    from pglast import ast
except ImportError:      # pragma: no cover
    pglast = None

ROOT = Path(__file__).resolve().parent.parent
# pglast's PL/pgSQL-to-JSON step cannot read these two trigger functions (they ran fine in Postgres); their statements still parse
KNOWN_UNREADABLE = {"rfc_comments_before_insert", "rfc_status_log_before_insert"}


@unittest.skipUnless(pglast, "pglast is not installed")
class MigrationsParse(unittest.TestCase):
    def test_every_migration_and_function_body_parses(self):
        files = sorted((ROOT / "supabase" / "migrations").glob("*.sql"))
        self.assertGreaterEqual(len(files), 6)
        for f in files:
            sql = f.read_text(encoding="utf-8")
            with self.subTest(f.name):
                stmts = pglast.parse_sql(sql)
                for s in stmts:
                    st = s.stmt
                    if isinstance(st, ast.CreateFunctionStmt) and any(o.defname == "language" and o.arg.sval == "plpgsql" for o in st.options):
                        name = st.funcname[-1].sval
                        if name in KNOWN_UNREADABLE:
                            continue
                        text = sql[s.stmt_location:s.stmt_location + s.stmt_len] if s.stmt_len else sql[s.stmt_location:]
                        pglast.parse_plpgsql(text)

    def test_migration_names_are_ordered_timestamps(self):
        names = [f.name for f in sorted((ROOT / "supabase" / "migrations").glob("*.sql"))]
        for n in names:
            self.assertRegex(n, r"^\d{14}_[a-z_]+\.sql$")
        self.assertEqual(names, sorted(names))


if __name__ == "__main__":
    unittest.main()
