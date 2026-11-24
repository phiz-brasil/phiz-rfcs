"""Phase 2, slice 1 (docs/spec/v2/login.md): the sign-in page, the session, the token on every request, the account in the menu, the guard behind the switch."""
import re
import sys
import time
import unittest
from pathlib import Path

from playwright.sync_api import expect

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import SiteCase, import_rfc  # noqa: E402


def stored(page):
    return page.evaluate("JSON.parse(localStorage.getItem('phiz-auth') || 'null')")


class LoginPageTest(SiteCase):
    def login(self, query=""):
        self.page.goto(self.base + "/login/" + query)
        expect(self.page.get_by_label("E-mail")).to_be_visible()

    def calls(self, name):
        return [b for n, b in self.db.auth_calls if n == name]

    def test_an_address_outside_the_domain_is_refused_without_any_request(self):
        self.login()
        self.page.get_by_label("E-mail").fill("pessoa@gmail.com")
        self.page.get_by_role("button", name="Enviar código").click()
        expect(self.page.locator("main [role=alert]")).to_contain_text("@phizchat.com")
        self.assertEqual(self.db.auth_calls, [])

    def test_a_company_address_asks_for_a_code_and_shows_the_code_field(self):
        self.login()
        self.page.get_by_label("E-mail").fill("Ana.Souza@PHIZCHAT.com")
        self.page.get_by_role("button", name="Enviar código").click()
        expect(self.page.get_by_text("Enviamos um código para ana.souza@phizchat.com")).to_be_visible()
        (otp,) = self.calls("otp")
        self.assertEqual((otp["email"], otp["create_user"]), ("ana.souza@phizchat.com", True))
        self.assertTrue(otp["_q"]["redirect_to"].endswith("/login/"))
        expect(self.page.get_by_label("Código de 6 dígitos")).to_be_visible()
        expect(self.page.get_by_role("button", name="Enviar de novo")).to_be_disabled()           # not before 30 seconds

    def test_the_right_code_makes_a_session_and_leads_to_the_overview(self):
        self.login()
        self.page.get_by_label("E-mail").fill("ana.souza@phizchat.com")
        self.page.get_by_role("button", name="Enviar código").click()
        self.page.get_by_label("Código de 6 dígitos").fill("123456")
        self.page.get_by_role("button", name="Entrar").click()
        self.page.wait_for_url(re.compile(r"/overview/$"))
        s = stored(self.page)
        self.assertEqual((s["user"]["email"], s["access_token"], s["refresh_token"]), ("ana.souza@phizchat.com", "tok-ana.souza", "ref-ana.souza"))
        self.assertGreater(s["expires_at"], time.time() + 3000)
        (v,) = self.calls("verify")
        self.assertEqual((v["type"], v["email"], v["token"]), ("email", "ana.souza@phizchat.com", "123456"))

    def test_a_wrong_code_shows_an_error_and_keeps_the_form(self):
        self.login()
        self.page.get_by_label("E-mail").fill("ana.souza@phizchat.com")
        self.page.get_by_role("button", name="Enviar código").click()
        self.page.get_by_label("Código de 6 dígitos").fill("000000")
        self.page.get_by_role("button", name="Entrar").click()
        expect(self.page.locator("main [role=alert]")).to_contain_text("inválido ou expirou")
        self.assertIsNone(stored(self.page))
        expect(self.page.get_by_label("Código de 6 dígitos")).to_be_visible()

    def test_the_link_in_the_message_brings_the_tokens_in_the_address_and_signs_the_person_in(self):
        self.db.refreshable["ref-bo"] = "bo@phizchat.com"
        self.page.goto(self.base + "/login/?next=%2Fthemes%2F#access_token=tok-bo&refresh_token=ref-bo&expires_in=3600&token_type=bearer&type=magiclink")
        self.page.wait_for_url(re.compile(r"/themes/$"))
        s = stored(self.page)
        self.assertEqual((s["user"]["email"], s["access_token"]), ("bo@phizchat.com", "tok-bo"))
        self.assertEqual(self.calls("user")[0]["_auth"], "Bearer tok-bo")
        self.assertNotIn("access_token", self.page.url)

    def test_a_session_of_an_outside_address_is_ended_with_a_message(self):
        self.db.refreshable["ref-x"] = "x@gmail.com"
        self.page.goto(self.base + "/login/#access_token=tok-x&refresh_token=ref-x&expires_in=3600&token_type=bearer&type=magiclink")
        expect(self.page.locator("main [role=alert]")).to_contain_text("@phizchat.com")
        self.assertIsNone(stored(self.page))

    def test_next_must_stay_on_this_site(self):
        for evil in ("https://evil.example/x", "//evil.example/x"):
            with self.subTest(evil):
                self.db.refreshable["ref-bo"] = "bo@phizchat.com"
                self.page.goto(self.base + f"/login/?next={evil}#access_token=tok-bo&refresh_token=ref-bo&expires_in=3600&type=magiclink")
                self.page.wait_for_url(re.compile(r"/overview/$"))
                self.page.evaluate("localStorage.clear()")

    def test_the_page_is_translated(self):
        self.page.goto(self.base + "/login/")
        self.page.get_by_role("button", name="EN-US").click()
        expect(self.page.get_by_label("E-mail")).to_be_visible()
        expect(self.page.get_by_role("button", name="Send code")).to_be_visible()


class SessionTest(SiteCase):
    def setUp(self):
        super().setUp()
        self.db.seed_theme("PHZ-0001", "api-platform", title={"pt": "Business API"}, owner="Ana")

    def test_react_pages_send_the_access_token_and_without_a_session_nothing_is_sent(self):
        self.page.goto(self.base + "/themes/")
        expect(self.page.locator("tr.theme-row").first).to_be_visible()
        self.assertTrue(self.db.rest_auth and all(a is None for a in self.db.rest_auth))
        self.db.rest_auth.clear()
        self.sign_in_as()
        self.page.goto(self.base + "/themes/")
        expect(self.page.locator("tr.theme-row").first).to_be_visible()
        self.assertTrue(self.db.rest_auth and all(a == "Bearer tok-ana.souza" for a in self.db.rest_auth), set(self.db.rest_auth))

    def test_the_old_pages_send_it_too(self):
        self.sign_in_as()
        for path in ("/", "/comments/"):
            self.db.rest_auth.clear()
            self.page.goto(self.base + path)
            self.page.wait_for_timeout(1200)
            self.assertTrue(self.db.rest_auth, path)
            self.assertTrue(all(a == "Bearer tok-ana.souza" for a in self.db.rest_auth), (path, set(self.db.rest_auth)))

    def test_the_auth_calls_themselves_do_not_get_the_token_added(self):
        self.sign_in_as(expires_in=10)                                                        # about to expire: the page refreshes first
        self.page.goto(self.base + "/themes/")
        expect(self.page.locator("tr.theme-row").first).to_be_visible()
        (tok,) = [b for n, b in self.db.auth_calls if n == "token"]
        self.assertIsNone(tok["_auth"])
        self.assertEqual(tok["refresh_token"], "ref-ana.souza")

    def test_an_expiring_token_is_refreshed_before_the_request_and_the_new_one_is_used(self):
        self.sign_in_as(expires_in=10)
        self.page.goto(self.base + "/themes/")
        expect(self.page.locator("tr.theme-row").first).to_be_visible()
        self.assertTrue(all(a == "Bearer tok-ana.souza-r" for a in self.db.rest_auth), set(self.db.rest_auth))
        self.assertEqual(stored(self.page)["access_token"], "tok-ana.souza-r")

    def test_a_refresh_that_fails_ends_the_session(self):
        self.sign_in_as(expires_in=10, fake_refresh=False)
        self.page.goto(self.base + "/themes/")
        expect(self.page.locator("tr.theme-row").first).to_be_visible()
        self.assertIsNone(stored(self.page))
        self.assertTrue(all(a is None for a in self.db.rest_auth))

    def test_the_account_is_in_the_menu_and_signing_out_clears_the_session(self):
        self.sign_in_as("ana.souza@phizchat.com")
        self.page.goto(self.base + "/themes/")
        self.prefs()
        expect(self.page.locator(".user-pop")).to_contain_text("ana.souza@phizchat.com")
        expect(self.page.get_by_label("Seu nome")).to_have_count(0)                          # the typed name is gone
        self.page.get_by_role("button", name="Sair").click()
        self.page.wait_for_function("localStorage.getItem('phiz-auth') === null")
        self.assertIn(("logout", {"_auth": "Bearer tok-ana.souza"}), self.db.auth_calls)

    def test_without_a_session_the_menu_still_asks_for_a_typed_name(self):
        self.page.goto(self.base + "/themes/")
        self.prefs()
        expect(self.page.get_by_label("Seu nome")).to_be_visible()
        expect(self.page.get_by_role("button", name="Sair")).to_have_count(0)

    def test_writes_carry_the_name_of_the_account(self):
        self.sign_in_as("ana.souza@phizchat.com")
        self.page.goto(self.base + "/themes/PHZ-0001/")
        form = self.page.get_by_role("region", name="Atualização semanal")
        form.get_by_label("Andamento (uma frase)").fill("Contrato fechado")
        form.get_by_role("button", name="Publicar atualização").click()
        expect(form.locator("article")).to_have_count(1)
        (call,) = [b for n, b in self.db.calls if n == "post_theme_update"]
        self.assertEqual(call["p_by"], "Ana Souza")

    def test_a_name_in_the_account_wins_over_the_one_made_from_the_address(self):
        self.sign_in_as("a.souza@phizchat.com", name="Ana Paula Souza")
        self.page.goto(self.base + "/themes/PHZ-0001/")
        form = self.page.get_by_role("region", name="Atualização semanal")
        form.get_by_label("Andamento (uma frase)").fill("x")
        form.get_by_role("button", name="Publicar atualização").click()
        expect(form.locator("article")).to_have_count(1)
        self.assertEqual([b["p_by"] for n, b in self.db.calls if n == "post_theme_update"], ["Ana Paula Souza"])

    def test_the_old_pages_remember_the_account_name_for_their_own_name_field(self):
        self.sign_in_as("bo.lima@phizchat.com")
        self.page.goto(self.base + "/nova/")
        expect(self.page.locator("#by")).to_have_value("Bo Lima")
        self.assertEqual(self.page.evaluate("localStorage.getItem('phiz-rfc-author')"), "Bo Lima")

    def test_a_comment_on_an_rfc_is_written_by_the_account_with_the_token(self):
        import_rfc(self.db, "PHZ-0002")
        self.sign_in_as("bo.lima@phizchat.com")
        self.page.goto(self.base + "/rfc/?id=PHZ-0002")
        self.page.wait_for_selector(".lang.active h2 .cmt-btn")
        self.page.locator("#pt-summary .cmt-btn").click()
        panel = self.page.locator("#pt-summary + .cmt-panel")
        expect(panel.locator("input[name=author]")).to_have_value("Bo Lima")
        panel.locator("textarea[name=body]").fill("Concordo com o resumo.")
        self.db.rest_auth.clear()
        panel.locator(".cmt-send").click()
        expect(panel.locator(".cmt-item")).to_have_count(1)
        self.assertEqual(self.db.posts[-1]["author"], "Bo Lima")
        self.assertTrue(self.db.rest_auth and all(a == "Bearer tok-bo.lima" for a in self.db.rest_auth), set(self.db.rest_auth))

    def test_the_old_pages_show_the_account_and_a_way_out(self):
        self.sign_in_as("bo.lima@phizchat.com")
        self.page.goto(self.base + "/")
        expect(self.page.locator("header.appbar [data-auth-slot]")).to_contain_text("bo.lima@phizchat.com")
        self.page.locator("header.appbar [data-auth-slot] button").click()
        self.page.wait_for_function("localStorage.getItem('phiz-auth') === null")


class GuardTest(SiteCase):
    def test_with_the_switch_on_a_page_without_a_session_goes_to_the_sign_in_and_remembers_where(self):
        self.require_sign_in()
        self.page.goto(self.base + "/themes/?x=1#top")
        self.page.wait_for_url(re.compile(r"/login/\?next="))
        self.assertIn("next=%2Fthemes%2F%3Fx%3D1%23top", self.page.url)
        self.assertEqual(self.db.rest_auth, [])                                              # not a single request before the person signs in

    def test_the_old_pages_are_guarded_too(self):
        self.require_sign_in()
        for path in ("/", "/comments/", "/nova/", "/rfc/?id=PHZ-0001"):
            with self.subTest(path):
                self.page.goto(self.base + path)
                self.page.wait_for_url(re.compile(r"/login/\?next="))

    def test_with_a_session_the_guard_lets_the_page_through_and_the_sign_in_page_never_redirects(self):
        self.require_sign_in()
        self.sign_in_as()
        self.page.goto(self.base + "/overview/")
        expect(self.page.locator("h1")).to_have_text("Visão geral")
        self.page.goto(self.base + "/login/")
        expect(self.page.get_by_label("E-mail")).to_be_visible()
        self.assertTrue(self.page.url.endswith("/login/"))

    def test_the_sign_in_page_works_with_the_switch_on_and_no_session(self):
        self.require_sign_in()
        self.page.goto(self.base + "/login/")
        expect(self.page.get_by_label("E-mail")).to_be_visible()

    def test_a_session_of_an_outside_address_does_not_pass_the_guard(self):
        self.require_sign_in()
        self.sign_in_as("pessoa@gmail.com")
        self.page.goto(self.base + "/themes/")
        self.page.wait_for_url(re.compile(r"/login/"))
        self.assertIsNone(stored(self.page))

    def test_the_switch_off_changes_nothing_for_a_visitor_without_a_session(self):
        self.page.goto(self.base + "/overview/")
        expect(self.page.locator("h1")).to_have_text("Visão geral")
        self.assertTrue(self.page.url.endswith("/overview/"))


if __name__ == "__main__":
    unittest.main()


class LongWindowTest(SiteCase):
    """docs/spec/v2/login.md, "A long window of sign-in": the session ends only when Supabase says the refresh token is invalid, and the token is renewed before it is needed."""
    def setUp(self):
        super().setUp()
        self.db.seed_theme("PHZ-0001", "api-platform", title={"pt": "Business API"}, owner="Ana")

    def tokens(self):
        return [b for n, b in self.db.auth_calls if n == "token"]

    def themes(self):
        self.page.goto(self.base + "/themes/")
        expect(self.page.locator("tr.theme-row").first).to_be_visible()

    def test_a_refresh_that_fails_for_a_reason_that_is_not_final_keeps_the_session(self):
        for status in (500, 503, 429):
            with self.subTest(status):
                self.db.token_status = status
                self.page.goto(self.base + "/themes/")
                self.page.evaluate("localStorage.clear(); sessionStorage.clear()")
                self.sign_in_as(expires_in=10)
                self.page.reload()
                expect(self.page.locator("tr.theme-row").first).to_be_visible()
                self.assertIsNotNone(stored(self.page), f"a {status} must not end the session")
                self.assertEqual(stored(self.page)["refresh_token"], "ref-ana.souza")

    def test_a_refresh_that_never_arrives_keeps_the_session(self):
        self.sign_in_as(expires_in=10)
        self.context.route(re.compile(r".*/auth/v1/token.*"), lambda r: r.abort())
        self.page.goto(self.base + "/themes/")
        expect(self.page.locator("tr.theme-row").first).to_be_visible()
        self.assertIsNotNone(stored(self.page))

    def test_an_invalid_refresh_token_ends_the_session_for_every_final_status(self):
        for status in (400, 401, 403):
            with self.subTest(status):
                self.db.token_status = status
                self.sign_in_as(expires_in=10)
                self.page.goto(self.base + "/themes/")
                expect(self.page.locator("tr.theme-row").first).to_be_visible()
                self.assertIsNone(stored(self.page))
                self.page.evaluate("sessionStorage.clear()")

    def test_a_session_that_expired_a_month_ago_renews_on_the_first_request_and_works(self):
        self.sign_in_as(expires_in=-30 * 86400)
        self.themes()
        self.assertEqual(len(self.tokens()), 1)
        self.assertTrue(all(a == "Bearer tok-ana.souza-r" for a in self.db.rest_auth), set(self.db.rest_auth))
        self.assertGreater(stored(self.page)["expires_at"], time.time() + 3000)

    def test_coming_back_to_a_tab_renews_a_token_that_is_about_to_expire_without_any_page_request(self):
        self.sign_in_as(expires_in=3600)
        self.themes()
        self.page.evaluate("(() => { const s = JSON.parse(localStorage.getItem('phiz-auth')); s.expires_at = Math.floor(Date.now() / 1000) + 120; localStorage.setItem('phiz-auth', JSON.stringify(s)); })()")
        before = len(self.tokens())
        self.page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
        self.page.wait_for_function("JSON.parse(localStorage.getItem('phiz-auth')).access_token.endsWith('-r')")
        self.assertEqual(len(self.tokens()), before + 1)

    def test_a_token_with_plenty_of_time_left_is_not_renewed_when_coming_back(self):
        self.sign_in_as(expires_in=3600)
        self.themes()
        self.page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
        self.page.wait_for_timeout(500)
        self.assertEqual(self.tokens(), [])

    def test_a_tab_left_open_renews_the_token_by_itself_before_it_expires(self):
        self.sign_in_as(expires_in=3600)
        self.page.clock.install()
        self.page.goto(self.base + "/themes/")
        expect(self.page.locator("tr.theme-row").first).to_be_visible()
        self.assertEqual(self.tokens(), [])
        self.page.clock.run_for(56 * 60 * 1000)                                            # 4 minutes from the end of the hour: renews within one tick
        self.page.wait_for_function("JSON.parse(localStorage.getItem('phiz-auth')).access_token.endsWith('-r')")

    def test_two_tabs_that_need_a_new_token_at_the_same_moment_make_one_call(self):
        self.sign_in_as(expires_in=10)
        other = self.context.new_page()
        self.page.goto(self.base + "/themes/")
        other.goto(self.base + "/themes/")
        expect(self.page.locator("tr.theme-row").first).to_be_visible()
        expect(other.locator("tr.theme-row").first).to_be_visible()
        self.assertEqual(len(self.tokens()), 1)
        self.assertTrue(all(a == "Bearer tok-ana.souza-r" for a in self.db.rest_auth), set(self.db.rest_auth))


class CodeOnlyTextsTest(SiteCase):
    """docs/spec/v2/login.md, "Decision 2026-11-24": the message carries only the code, so the page never promises a link."""

    def test_the_page_speaks_of_a_code_and_never_of_a_link(self):
        self.page.goto(self.base + "/login/")
        main = self.page.locator("main")
        expect(main).to_contain_text("código de 6 dígitos")
        expect(main).not_to_contain_text("link")
        expect(self.page.get_by_role("button", name="Enviar código")).to_be_visible()

    def test_the_form_tells_that_each_request_replaces_the_previous_code(self):
        self.page.goto(self.base + "/login/")
        self.page.get_by_label("E-mail").fill("ana.souza@phizchat.com")
        self.page.get_by_role("button", name="Enviar código").click()
        expect(self.page.locator("main")).to_contain_text("o último substitui os anteriores")
