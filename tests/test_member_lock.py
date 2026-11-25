"""Phase 2, slice 2 (docs/spec/v2/login.md, "Slice 2 in detail"): the database lock. There is no Postgres in the test environment, so the migration is checked structurally
(parsed with pglast) and the behaviour is checked through the fake, which does what the gate does."""
import re
import sys
import unittest
from pathlib import Path

from playwright.sync_api import expect

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import ROOT, SiteCase, import_rfc  # noqa: E402

try:
    import pglast
    from pglast import ast
except ImportError:      # pragma: no cover
    pglast = None

LOCK = ROOT / "supabase" / "migrations" / "20261201000000_member_lock.sql"
BOARD = ROOT / "supabase" / "migrations" / "20261127000000_board_columns.sql"


def function_body(sql, name):
    m = re.search(r"create or replace function public\.%s\(.*?\$\$(.*?)\$\$;" % name, sql, re.S)
    return m.group(1) if m else None


@unittest.skipUnless(pglast, "pglast is not installed")
class MigrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sql = LOCK.read_text(encoding="utf-8")
        cls.stmts = pglast.parse_sql(cls.sql)

    def text(self, s):
        return self.sql[s.stmt_location:s.stmt_location + s.stmt_len] if s.stmt_len else self.sql[s.stmt_location:]

    def test_it_parses_and_every_function_body_parses(self):
        for s in self.stmts:
            if isinstance(s.stmt, ast.CreateFunctionStmt) and any(o.defname == "language" and o.arg.sval == "plpgsql" for o in s.stmt.options):
                pglast.parse_plpgsql(self.text(s))

    def test_it_creates_the_membership_functions_the_admin_table_and_ping(self):
        names = {s.stmt.funcname[-1].sval for s in self.stmts if isinstance(s.stmt, ast.CreateFunctionStmt)}
        self.assertTrue({"is_member", "is_admin", "check_request", "ping", "save_board_column", "delete_board_column"} <= names, names)
        self.assertIn("create table if not exists public.app_admins", self.sql)

    def test_membership_is_the_role_authenticated_and_an_address_of_the_domain(self):
        body = function_body(self.sql, "is_member")
        self.assertIn("'authenticated'", body)
        self.assertIn("phiz\\.com", body)
        self.assertIn("auth.jwt()", body)

    def test_while_nobody_is_named_every_member_is_an_admin(self):
        body = function_body(self.sql, "is_admin")
        self.assertIn("public.is_member()", body)
        self.assertIn("not exists (select 1 from public.app_admins)", body)
        self.assertIn("public.app_admins", body)

    def test_the_gate_lets_service_role_and_ping_through_and_refuses_anon_with_401_and_others_with_403(self):
        body = function_body(self.sql, "check_request")
        for want in ("service_role", "/rpc/ping", "'PT401'", "'PT403'", "request.jwt.claims", "request.path", "public.is_member()"):
            self.assertIn(want, body)
        self.assertLess(body.index("service_role"), body.index("'PT401'"))
        self.assertLess(body.index("/rpc/ping"), body.index("'PT401'"))
        self.assertLess(body.index("'PT401'"), body.index("'PT403'"))

    def test_anon_loses_every_table_function_and_sequence_and_the_defaults_for_new_ones(self):
        for want in ("revoke all on all tables in schema public from anon", "revoke all on all functions in schema public from anon",
                     "revoke all on all sequences in schema public from anon", "alter default privileges in schema public revoke all on tables from anon",
                     "alter default privileges in schema public revoke all on functions from anon"):
            self.assertIn(want, self.sql)

    def test_what_anon_may_still_run_is_only_the_gate_ping_and_the_membership_test(self):
        grants = [self.text(s) for s in self.stmts if isinstance(s.stmt, ast.GrantStmt) and s.stmt.is_grant and self.text(s).lower().find(" to ") > 0]
        to_anon = [g for g in grants if re.search(r"\banon\b", g.split(" to ", 1)[1])]
        self.assertTrue(to_anon)
        for g in to_anon:
            self.assertRegex(g, r"execute on function public\.(check_request|ping|is_member)\(\)", g)
            self.assertNotRegex(g, r"on (all )?tables|select|insert|update|delete")

    def test_every_table_with_row_security_gets_the_restrictive_members_only_policy(self):
        self.assertIn("relrowsecurity", self.sql)
        self.assertIn("as restrictive for all to authenticated using (public.is_member()) with check (public.is_member())", self.sql)
        self.assertIn("drop policy if exists members_only", self.sql)                           # idempotent

    def test_the_storage_policies_of_attachments_are_for_members_only(self):
        for name in ("attachments read", "attachments upload"):
            self.assertIn(f'drop policy if exists "{name}" on storage.objects', self.sql)
        creates = [self.text(s) for s in self.stmts if isinstance(s.stmt, ast.CreatePolicyStmt) and "storage" in self.text(s)]
        self.assertGreaterEqual(len(creates), 3)                                                # read, upload, and the restrictive one
        for c in creates:
            self.assertNotRegex(c.split(" using ", 1)[0].split(" with check ", 1)[0], r"\banon\b", c)
            self.assertIn("public.is_member()", c)
        self.assertTrue(any("restrictive" in c for c in creates))
        self.assertIn("'^PHZ-[0-9]{4}/[0-9a-f]{8}-", self.sql)                                   # the upload path rule is kept

    def test_the_board_functions_differ_from_their_old_versions_only_by_the_admin_line(self):
        old = BOARD.read_text(encoding="utf-8")
        for name in ("save_board_column", "delete_board_column"):
            was, now = function_body(old, name), function_body(self.sql, name)
            self.assertIsNotNone(was, name)
            self.assertIsNotNone(now, name)
            lines_now = now.split("\n")
            added = [l for l in lines_now if l not in was.split("\n")]
            self.assertEqual(len(added), 1, added)
            self.assertIn("public.is_admin()", added[0])
            self.assertEqual("\n".join(l for l in lines_now if l not in added), was)
            self.assertIn(f"create or replace function public.{name}(", self.sql)

    def test_the_board_functions_keep_their_signature_and_grants(self):
        old = BOARD.read_text(encoding="utf-8")
        for name in ("save_board_column", "delete_board_column"):
            sig = lambda t: re.search(r"create or replace function public\.%s\((.*?)\)\s*returns (.*?) language" % name, t, re.S).groups()  # noqa: E731
            self.assertEqual(sig(old), sig(self.sql))
        self.assertIn("grant execute on function public.save_board_column(uuid, jsonb, text), public.delete_board_column(uuid, text) to authenticated", self.sql)

    def test_the_gate_is_turned_on_last_and_the_undo_is_written_down(self):
        last = self.text(self.stmts[-2]) + self.text(self.stmts[-1])                            # the alter role and the notify
        self.assertIn("pgrst.db_pre_request", last)
        self.assertIn("public.check_request", last)
        self.assertIn("notify pgrst", self.text(self.stmts[-1]).lower())
        self.assertIn("alter role authenticator reset pgrst.db_pre_request", self.sql)          # the undo, as a comment
        pos = self.sql.index("pgrst.db_pre_request")
        self.assertEqual(self.sql[:pos].count("pgrst.db_pre_request"), 0)
        before_gate = self.sql[:pos]
        for later in ("create or replace function public.check_request", "revoke all on all tables", "members_only"):
            self.assertIn(later, before_gate)

    def test_it_is_idempotent_by_construction(self):
        for s in self.stmts:
            t = self.text(s).lower()
            if isinstance(s.stmt, ast.CreateStmt):
                self.assertIn("if not exists", t)
            if isinstance(s.stmt, ast.CreateFunctionStmt):
                self.assertTrue(s.stmt.replace, t[:80])


class WorkflowAndFunctionTest(unittest.TestCase):
    def test_the_keep_alive_job_calls_ping_and_keeps_the_old_read_as_a_fallback(self):
        y = (ROOT / ".github" / "workflows" / "keepalive.yml").read_text(encoding="utf-8")
        self.assertIn("/rest/v1/rpc/ping", y)
        self.assertIn("/rest/v1/rfc_comments?select=id&limit=1", y)
        self.assertLess(y.index("rpc/ping"), y.index("rfc_comments"))

    def test_suggest_summary_asks_who_the_caller_is_only_when_the_secret_says_so(self):
        src = (ROOT / "supabase" / "functions" / "suggest-summary" / "index.ts").read_text(encoding="utf-8")
        self.assertIn('Deno.env.get("REQUIRE_MEMBER")', src)
        self.assertIn("auth.getUser", src)
        self.assertIn("memberEmail", src)
        self.assertIn("401", src)
        self.assertIn("403", src)


class LockedFakeTest(SiteCase):
    """The pages against the fake with the gate on: members work, anonymous visitors get 401, other domains 403, ping answers anyone."""
    def setUp(self):
        super().setUp()
        self.db.lock = True
        self.db.seed_theme("PHZ-0001", "api-platform", title={"pt": "Business API"}, owner="Ana", progress={"pt": "Contrato fechado"})

    def test_a_member_reads_the_pages_with_the_lock_on(self):
        self.sign_in_as("ana.souza@phizchat.com")
        self.page.goto(self.base + "/themes/")
        expect(self.page.locator('tr[data-theme="PHZ-0001"]')).to_contain_text("Business API")
        self.assertEqual(self.db.lock_refused, [])

    def test_a_member_writes_through_rpc_with_the_lock_on(self):
        self.sign_in_as("ana.souza@phizchat.com")
        self.page.goto(self.base + "/themes/PHZ-0001/")
        form = self.page.get_by_role("region", name="Atualização semanal")
        form.get_by_label("Andamento (uma frase)").fill("Piloto aprovado")
        form.get_by_role("button", name="Publicar atualização").click()
        expect(form.locator("article")).to_have_count(1)
        self.assertEqual(self.db.lock_refused, [])

    def test_a_member_uploads_and_opens_an_attachment_with_the_lock_on(self):
        self.sign_in_as("ana.souza@phizchat.com")
        self.page.goto(self.base + "/themes/PHZ-0001/")
        form = self.page.get_by_role("form", name="Adicionar anexo")
        form.locator("input[type=file]").set_input_files(files=[{"name": "a.txt", "mimeType": "text/plain", "buffer": b"oi"}])
        form.get_by_role("button", name="Anexar").click()
        expect(self.page.get_by_role("region", name="Anexos").locator('tr[data-name="a.txt"]')).to_be_visible()
        self.assertEqual(self.db.lock_refused, [])

    def test_the_old_pages_work_for_a_member_with_the_lock_on(self):
        import_rfc(self.db, "PHZ-0002")
        self.sign_in_as("ana.souza@phizchat.com")
        self.page.goto(self.base + "/rfc/?id=PHZ-0002")
        self.page.wait_for_selector(".lang.active h2 .cmt-btn")
        self.assertEqual(self.db.lock_refused, [])

    def test_a_visitor_without_a_session_is_refused_with_401_on_every_kind_of_request(self):
        self.page.goto(self.base + "/themes/")
        self.page.wait_for_timeout(1200)
        self.assertTrue(self.db.lock_refused)
        self.assertTrue(all(code == 401 for code, _ in self.db.lock_refused), self.db.lock_refused)
        expect(self.page.locator("tr.theme-row")).to_have_count(0)                              # nothing was read
        expect(self.page.get_by_text("Não foi possível carregar")).to_be_visible()              # and the page says so instead of breaking

    def test_a_session_of_another_domain_is_refused_with_403(self):
        self.sign_in_as("pessoa@gmail.com")
        self.context.add_init_script("localStorage.setItem('phiz-auth', JSON.stringify(%s))" % __import__("json").dumps(
            {"access_token": "tok-pessoa", "refresh_token": "ref-pessoa", "expires_at": 9999999999, "user": {"email": "pessoa@gmail.com"}}))
        self.page.goto(self.base + "/overview/")                                                # the page ends the session; the first requests can still go out
        self.page.wait_for_timeout(800)
        codes = {c for c, _ in self.db.lock_refused}
        self.assertTrue(codes <= {403, 401})

    def test_ping_answers_anyone(self):
        self.page.goto(self.base + "/overview/")                                                # the fake answers inside the browser, so ask from the page
        got = self.page.evaluate("""async (u) => { const r = await fetch(u + '/rest/v1/rpc/ping', {method: 'POST', headers: {apikey: 'sb_publishable_x', 'Content-Type': 'application/json'}, body: '{}'}); return [r.status, await r.json()]; }""", self.db_url())
        self.assertEqual(got, [200, True])

    def test_the_whole_gate_in_one_table(self):
        cases = [(None, "/rest/v1/themes?select=id", 401), ("tok-ana.souza", "/rest/v1/themes?select=id", 200), ("tok-pessoa", "/rest/v1/themes?select=id", 403),
                 (None, "/rest/v1/rpc/ping", 200), (None, "/storage/v1/object/sign/attachments/x", 401), (None, "/functions/v1/suggest-summary", 401)]
        self.db.refreshable["ref-ana.souza"] = "ana.souza@phizchat.com"
        self.db.tokens["tok-ana.souza"] = "ana.souza@phizchat.com"
        self.db.tokens["tok-pessoa"] = "pessoa@gmail.com"
        for token, path, want in cases:
            with self.subTest((token, path)):
                self.assertEqual(self.db.gate(token, path), want)

    def db_url(self):
        return "https://zuwbjcwfqzucjmxrehad.supabase.co"


if __name__ == "__main__":
    unittest.main()


class GoLiveSwitchTest(unittest.TestCase):
    """Slice 3 (docs/spec/v2/login.md): the switch is on in the file, and the tests can still turn it off."""

    def test_the_switch_is_on_in_the_config_file(self):
        import json
        cfg = json.loads((ROOT / "site.config.json").read_text(encoding="utf-8"))
        self.assertIs(cfg["auth"]["required"], True)

    def test_an_environment_variable_overrides_the_file(self):
        src = (ROOT / "apps" / "web" / "server" / "site" / "auth.ts").read_text(encoding="utf-8")
        self.assertIn("PHIZ_AUTH_REQUIRED", src)
        support = (ROOT / "tests" / "support.py").read_text(encoding="utf-8")
        self.assertIn('"PHIZ_AUTH_REQUIRED"', support)                                           # the suite builds and serves with the switch off


NEW_DOMAIN = ROOT / "supabase" / "migrations" / "20261202000000_member_domain.sql"


@unittest.skipUnless(pglast, "pglast is not installed")
class MemberDomainMigrationTest(unittest.TestCase):
    """docs/spec/v2/login.md, "Decision 2026-11-24": the member domain is phizchat.com, through a new migration (the applied one is never edited)."""

    @classmethod
    def setUpClass(cls):
        cls.sql = NEW_DOMAIN.read_text(encoding="utf-8")
        cls.stmts = pglast.parse_sql(cls.sql)

    def test_it_parses_and_recreates_is_member_for_the_new_domain_only(self):
        body = function_body(self.sql, "is_member")
        self.assertIsNotNone(body)
        self.assertIn("phizchat\\.com", body)
        self.assertNotIn("phiz\\.com", body.replace("phizchat\\.com", ""))
        self.assertIn("'authenticated'", body)
        self.assertIn("auth.jwt()", body)

    def test_the_admin_table_accepts_only_the_new_domain(self):
        self.assertIn("alter table public.app_admins drop constraint if exists app_admins_email_check", self.sql)
        self.assertRegex(self.sql, r"add constraint app_admins_email_check check \(email = lower\(email\) and email ~ '\^\[\^@\]\+@phizchat\\\.com\$'\)")

    def test_it_does_not_touch_the_gate_or_the_policies(self):
        code = "\n".join(l for l in self.sql.splitlines() if not l.strip().startswith("--"))
        for word in ("check_request", "members_only", "pgrst.db_pre_request", "revoke"):
            self.assertNotIn(word, code)

    def test_it_is_idempotent(self):
        self.assertIn("create or replace function public.is_member()", self.sql)

    def test_the_applied_migration_was_not_edited(self):
        self.assertIn("phiz\\.com", LOCK.read_text(encoding="utf-8"))                         # the file that already ran keeps its history


GATE_MESSAGES = ROOT / "supabase" / "migrations" / "20261203000000_gate_messages.sql"


@unittest.skipUnless(pglast, "pglast is not installed")
class GateMessagesMigrationTest(unittest.TestCase):
    """docs/spec/v2/login.md, "Decision 2026-11-24: the gate's messages": same logic as the first gate, only the two texts name phizchat.com."""

    @classmethod
    def setUpClass(cls):
        cls.new_sql = GATE_MESSAGES.read_text(encoding="utf-8")
        cls.old_sql = LOCK.read_text(encoding="utf-8")
        pglast.parse_sql(cls.new_sql)                                                          # it parses

    def test_the_messages_name_the_company_domain(self):
        body = function_body(self.new_sql, "check_request")
        self.assertIn("sign in with a @phizchat.com account", body)
        self.assertIn("only @phizchat.com accounts have access", body)
        self.assertNotIn("phiz.com", body.replace("phizchat.com", ""))

    def test_only_the_two_texts_differ_from_the_first_gate(self):
        old = function_body(self.old_sql, "check_request").replace("@phiz.com", "@phizchat.com")
        self.assertEqual(function_body(self.new_sql, "check_request"), old)

    def test_the_header_of_the_function_is_the_same(self):
        head = lambda sql: re.search(r"create or replace function public\.check_request\(\)(.*?)as \$\$", sql, re.S).group(1)
        self.assertEqual(head(self.new_sql), head(self.old_sql))

    def test_it_only_replaces_the_function_and_touches_nothing_else(self):
        code = "\n".join(l for l in self.new_sql.splitlines() if not l.strip().startswith("--"))
        for word in ("revoke", "alter role", "drop ", "members_only", "create table"):
            self.assertNotIn(word, code)


HOOK = ROOT / "supabase" / "migrations" / "20261204000000_signup_domain_hook.sql"


@unittest.skipUnless(pglast, "pglast is not installed")
class SignupHookMigrationTest(unittest.TestCase):
    """docs/spec/v2/login.md, "Sign-up of other domains": the Auth hook that refuses the creation of a user of another domain (checked by structure, as the lock)."""

    @classmethod
    def setUpClass(cls):
        cls.sql = HOOK.read_text(encoding="utf-8")
        cls.code = "\n".join(l for l in cls.sql.splitlines() if not l.strip().startswith("--"))
        pglast.parse_sql(cls.sql)                                                              # it parses

    def body(self):
        m = re.search(r"create or replace function public\.hook_before_user_created\(event jsonb\)(.*?)as \$\$(.*?)\$\$;", self.sql, re.S)
        self.assertIsNotNone(m, "function not found")
        return m.group(1), m.group(2)

    def test_the_function_allows_with_an_empty_object_and_refuses_with_403_and_the_domain(self):
        head, body = self.body()
        self.assertIn("returns jsonb", head)
        self.assertIn("set search_path = ''", head)
        self.assertIn("'{}'::jsonb", body)
        self.assertIn("'http_code', 403", body)
        self.assertIn("@phizchat.com", body)

    def test_the_email_is_read_from_the_event_and_compared_in_lower_case(self):
        _, body = self.body()
        self.assertIn("event -> 'user' ->> 'email'", body)
        self.assertIn("lower(", body)

    def test_the_pattern_is_the_same_literal_as_is_member(self):
        pat = r"'^[^@]+@phizchat\.com$'"
        _, body = self.body()
        self.assertIn(pat, body)
        self.assertIn(pat, NEW_DOMAIN.read_text(encoding="utf-8"))                              # the one of public.is_member()

    def test_only_the_auth_admin_can_run_it(self):
        self.assertRegex(self.code, r"grant execute on function public\.hook_before_user_created\(jsonb\) to supabase_auth_admin")
        self.assertRegex(self.code, r"revoke execute on function public\.hook_before_user_created\(jsonb\) from (public|authenticated, anon, public|public, anon, authenticated)")
        self.assertRegex(self.code, r"revoke execute on function public\.hook_before_user_created\(jsonb\) from [^;]*\banon\b")
        self.assertRegex(self.code, r"revoke execute on function public\.hook_before_user_created\(jsonb\) from [^;]*\bauthenticated\b")

    def test_it_only_creates_the_function(self):
        for word in ("alter table", "create policy", "alter role", "drop ", "create table", "members_only", "pgrst"):
            self.assertNotIn(word, self.code)

    def test_it_is_idempotent(self):
        self.assertIn("create or replace function", self.sql)
