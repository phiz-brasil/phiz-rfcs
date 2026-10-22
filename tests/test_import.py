"""tools/import_rfcs.py: the RFCs of rfcs/ move to the database as single-file RFCs without losing what they show, and the pages
read them from there."""
import re
import sys
import unittest
from html import unescape
from pathlib import Path

from playwright.sync_api import expect

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import import_rfcs  # noqa: E402
import rfc_md  # noqa: E402
from support import ROOT, SiteCase, import_rfc, imported  # noqa: E402


def visible_text(body):
    body = re.sub(r"<img[^>]*>", " [image] ", body)
    return " ".join(unescape(re.sub(r"<[^>]+>", " ", body)).split())


def sections(bundle):
    parts = re.split(r"<!-- lang:(pt|en|zh) -->\n", bundle)
    return {parts[i]: parts[i + 1] for i in range(1, len(parts), 2)}


class Conversion(unittest.TestCase):
    def convert(self, text):
        return import_rfcs.convert(text, import_rfcs.Assets(ROOT / "rfcs" / "PHZ-0001"))

    def test_a_gallery_becomes_a_list_of_attached_images(self):
        out = self.convert('<div class="shots phones">\n<div class="shot"><a href="mocks/pt/whatsapp/a02-phone-number.png" target="_blank"><img src="mocks/pt/whatsapp/a02-phone-number.png" alt="Um [alt]" width="460" height="1070" loading="lazy"></a>'
                           '<p class="cap"><b>A02.</b> Legenda com <code>code</code></p></div>\n</div>')
        self.assertEqual(out, "::: gallery phones\n- ![Um \\[alt\\]](asset:pt-whatsapp-a02-phone-number.png) **A02.** Legenda com `code`\n:::")

    def test_screens_endpoints_legend_chips_and_captions(self):
        self.assertEqual(self.convert('<div class="screens">\n  <div class="screen"><h5>Painel</h5><span class="path">Muda · Tela 1</span><ul><li>Um <code>x</code></li><li>Dois</li></ul></div>\n</div>'),
                         "::: screens\n##### Painel | Muda · Tela 1\n\n- Um `x`\n- Dois\n:::")
        self.assertEqual(self.convert('<div class="eps-wrap">\n<div class="eps">\n  <div class="ep"><span class="m m-post">POST</span><code class="p">/oauth/token</code><span class="d">Emite <em>token</em></span></div>\n</div></div>'),
                         "::: endpoints\n- POST `/oauth/token` — Emite *token*\n:::")
        self.assertEqual(self.convert('<div class="legend"><span><span class="st eq">igual</span> mesma coisa</span><span><span class="st new">novo</span> não existia</span></div>'),
                         "::: legend\n- [igual]{eq} mesma coisa\n- [novo]{new} não existia\n:::")
        self.assertEqual(self.convert("| a<br>b | <span class=\"no\">Não.</span> e <span class=\"st ch\">muda</span> |"), "| a<br>b | [Não.]{no} e [muda]{ch} |")
        self.assertEqual(self.convert('<p class="cap">Uma nota com <code>orderId</code>.</p>'), "::: caption\nUma nota com `orderId`.\n:::")

    def test_code_is_left_alone_and_unknown_html_is_refused(self):
        code = "```json\n{\"a\": \"<div class=\\\"shots\\\">\"}\n```\n\nUse `channel:<id>` aqui."
        self.assertEqual(self.convert(code), code)
        with self.assertRaises(import_rfcs.ImportError_):
            self.convert("<table><tr><td>x</td></tr></table>")

    def test_images_get_names_the_database_accepts(self):
        for rid in ("PHZ-0001", "PHZ-0002"):
            for rev in imported(rid):
                for name in rev["assets"].files:
                    self.assertRegex(name, r"^[a-z0-9][a-z0-9._-]{0,59}$")
                    mime, data = rev["assets"].read(name)          # a real PNG/JPEG/WebP, at most 1 MB
                    self.assertGreater(len(data), 0)

    def test_nothing_the_pages_show_is_lost(self):
        """Same commentable blocks per section (comments keep their paragraph), same diagrams and code, same text."""
        for rid in ("PHZ-0001", "PHZ-0002"):
            folder = ROOT / "rfcs" / rid
            rev = imported(rid)[0]
            for lang, md in sections(rev["bundle"]).items():
                with self.subTest(rfc=rid, lang=lang):
                    old, _ = rfc_md.render_body((folder / f"rfc.{lang}.md").read_text(encoding="utf-8"), lang)
                    new, _ = rfc_md.render_body(md, lang)
                    so, sn = rfc_md.structure(old), rfc_md.structure(new)
                    self.assertEqual(sn["blocks"], so["blocks"])
                    self.assertEqual((sn["diagrams"], sn["code"]), (so["diagrams"], so["code"]))
                    a, b = visible_text(old), visible_text(new)
                    if (folder / "openapi_gen.py").exists():       # the one paragraph that changed: it links to the interactive page now
                        cut = lambda t: re.split(r"\b(?:Referência OpenAPI|OpenAPI reference|OpenAPI 参考)\b", t)[0]
                        a, b = cut(a), cut(b)
                    self.assertEqual(b, a)

    def test_the_header_data_travels_with_the_revision(self):
        rev = imported("PHZ-0001")[0]
        self.assertEqual((rev["rev"], rev["version"]), (8, "1.7"))          # the next version made on the site is 1.8
        self.assertEqual(rev["meta"]["reviewers"][0], {"name": "Pedro Bettani", "country": "BR"})
        self.assertEqual(rev["meta"]["created"], "2026-10-15")
        self.assertIn("reviewers: Pedro Bettani (BR), Vitor Mozer (BR), Richard Liang (CN)", rev["bundle"])
        self.assertLessEqual(len(rev["note"]), 300)
        self.assertEqual(imported("PHZ-0002")[0]["rev"], 2)

    def test_the_push_is_idempotent_and_makes_the_id_a_site_rfc(self):
        calls = []

        class Api:
            def call(self, method, path, body=None, prefer=None):
                calls.append((method, path.split("?")[0], body, prefer))
                if method == "GET" and path.startswith("rfc_ids"):
                    return [{"rfc_id": "PHZ-0002", "source": "repo"}]
                return [] if method == "GET" else None
        import_rfcs.push(Api(), "PHZ-0002", imported("PHZ-0002")[0])
        steps = [(m, p) for m, p, _, _ in calls]
        self.assertEqual(steps, [("GET", "rfc_ids"), ("PATCH", "rfc_ids"), ("POST", "rfc_revisions"), ("GET", "rfc_status_log"), ("POST", "rfc_status_log")])
        self.assertEqual(calls[1][2], {"source": "site"})
        self.assertIn("ignore-duplicates", calls[2][3])           # running it again changes nothing
        self.assertEqual(calls[2][2]["rev"], 2)
        self.assertEqual(calls[4][2]["status"], "draft")


class ImportedPages(SiteCase):
    def test_the_big_rfc_shows_its_galleries_and_screens_from_the_database(self):
        import_rfc(self.db, "PHZ-0001")
        self.page.goto(self.base + "/rfc/?id=PHZ-0001")
        self.page.wait_for_selector(".lang.active h2")
        self.assertGreater(self.page.locator(".lang.active .shots .shot").count(), 10)
        self.assertGreater(self.page.locator(".lang.active .screens .screen").count(), 5)
        self.assertGreaterEqual(self.page.locator(".lang.active .eps .ep").count(), 3)
        self.page.locator(".lang.active .shots img").first.scroll_into_view_if_needed()
        self.page.wait_for_function("document.querySelector('.lang.active .shots img').src.startsWith('blob:')")
        header = self.page.locator(".lang.active .hero").inner_text()
        self.assertIn("Pedro Bettani (Brasil)", header)
        self.assertIn("2026-10-15".split("-")[2], header)                    # the original date, not the day it was imported
        expect(self.page.locator(".rfcno.ver")).to_have_text("v1.7")

    def test_the_big_rfc_passes_the_checks_of_the_new_rfc_page(self):
        import_rfc(self.db, "PHZ-0001")
        self.page.goto(self.base + "/nova/?edit=PHZ-0001")
        expect(self.page.locator("#result .ok")).to_be_visible()
        expect(self.page.locator("#assets li")).to_have_count(138)

    def test_a_new_version_of_an_imported_rfc_is_the_next_number(self):
        import_rfc(self.db, "PHZ-0002")
        self.page.goto(self.base + "/nova/?edit=PHZ-0002")
        expect(self.page.locator("#result .ok")).to_be_visible()
        self.page.locator("#by").fill("Eli")
        self.page.locator("#publish").click()
        self.page.wait_for_url(re.compile(r"/rfc/\?id=PHZ-0002"))
        self.assertEqual(self.db.revisions[-1]["version"], "1.2")
        self.assertEqual(self.db.revisions[-1]["meta"]["reviewers"][0]["name"], "Pedro Bettani")      # reviewers are kept in the file


if __name__ == "__main__":
    unittest.main()
