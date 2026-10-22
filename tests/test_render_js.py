"""The parts of the browser renderer that have no Python twin: reading the single-file RFC, and sanitising what visitors submit."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import ROOT, SiteCase  # noqa: E402
from test_parity import HOST  # noqa: E402

GOOD = """---
title_pt: Título
title_en: Title
title_zh: 标题
summary_pt: Resumo
summary_en: Summary
summary_zh: 摘要
systems: channel, card-vault
---
<!-- lang:pt -->

## Resumo {#summary}

Texto.

<!-- lang:en -->

## Summary {#summary}

Text.

<!-- lang:zh -->

## 摘要 {#summary}

文本。
"""

XSS = [
    '<script>alert(1)</script>',
    '<img src=x onerror=alert(1)>',
    '<a href="javascript:alert(1)">x</a>',
    '<iframe src="https://evil.example"></iframe>',
    '<div onclick="alert(1)">x</div>',
    '<style>body{display:none}</style>',
    '<svg onload=alert(1)>',
    '<form action="https://evil.example"><input name=x></form>',
    '<button>fake</button>',
    '<h2 id="PHIZ_SITE">clobber</h2>',
    '<img src="http://insecure.example/i.png">',
]


class RenderJsTest(SiteCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        (ROOT / "dist" / "__render_host.html").write_text(HOST, encoding="utf-8")

    def setUp(self):
        super().setUp()
        self.page.goto(self.base + "/__render_host.html")
        self.page.wait_for_function("window.ready === true")

    def js(self, expr, arg=None):
        return self.page.evaluate(expr, arg)

    # -- single-file RFC ---------------------------------------------------
    def test_bundle_is_read_into_metadata_and_three_languages(self):
        r = self.js("(t) => R.bundle.parseBundle(t)", GOOD)
        self.assertEqual(r["errors"], [])
        self.assertEqual(r["meta"]["title"], {"pt": "Título", "en": "Title", "zh": "标题"})
        self.assertEqual(r["meta"]["systems"], ["channel", "card-vault"])
        self.assertTrue(r["md"]["pt"].startswith("## Resumo {#summary}"))
        self.assertIn("文本", r["md"]["zh"])

    def test_bundle_problems_are_all_reported_at_once(self):
        r = self.js("(t) => R.bundle.parseBundle(t)", "title_pt: x\n\n<!-- lang:pt -->\n## A {#a}\n")
        text = " ".join(r["errors"])
        self.assertIn("metadata block", text)
        self.assertIn("lang:en", text)
        self.assertIn("lang:zh", text)
        r = self.js("(t) => R.bundle.parseBundle(t)", GOOD.replace("title_en: Title", "title_en: TODO: fill").replace("summary_zh: 摘要\n", ""))
        text = " ".join(r["errors"])
        self.assertIn("title_en", text)
        self.assertIn("summary_zh", text)

    def test_bundle_round_trips(self):
        r = self.js("(t) => R.bundle.parseBundle(t)", GOOD)
        again = self.js("([m, md]) => R.bundle.parseBundle(R.bundle.buildBundle(m, md))", [r["meta"], r["md"]])
        self.assertEqual(again["errors"], [])
        self.assertEqual(again["meta"], r["meta"])
        self.assertEqual(again["md"], r["md"])

    def test_template_is_complete_and_the_same_in_the_three_languages(self):
        text = (ROOT / "templates" / "bundle" / "RFC.md").read_text(encoding="utf-8")
        r = self.js("(t) => R.bundle.parseBundle(t)", text)
        self.assertTrue(all("TODO:" in e for e in r["errors"]), r["errors"])        # only the placeholders are left to fill
        self.assertEqual(len(r["errors"]), 7)
        r = self.js("(t) => R.bundle.parseBundle(t)", text.replace("TODO: ", ""))
        self.assertEqual(r["errors"], [])
        parts = {lang: self.js("([t, l]) => { const o = R.markdown.renderBody(t, l, { html: false }); return { ids: o.ids, s: R.blocks.structure(o.body) }; }",
                               [r["md"][lang], lang]) for lang in ("pt", "en", "zh")}
        for other in ("en", "zh"):
            self.assertEqual(parts["pt"]["ids"], parts[other]["ids"])
            self.assertEqual(parts["pt"]["s"]["blocks"], parts[other]["s"]["blocks"])
            self.assertEqual(parts["pt"]["s"]["diagrams"], parts[other]["s"]["diagrams"])

    # -- the checks that gate an upload -------------------------------------
    def check(self, text):
        return self.js("(t) => { const r = R.check.checkBundle(t); return { ok: r.ok, errors: r.errors, meta: r.meta }; }", text)

    def test_a_complete_bundle_passes_every_check(self):
        r = self.check((ROOT / "tests" / "fixtures" / "valid_bundle.md").read_text(encoding="utf-8"))
        self.assertEqual(r["errors"], [])
        self.assertTrue(r["ok"])
        self.assertEqual(r["meta"]["title"]["en"], "Test integration")

    def test_the_raw_template_is_refused_because_of_its_placeholders(self):
        r = self.check((ROOT / "templates" / "bundle" / "RFC.md").read_text(encoding="utf-8"))
        self.assertFalse(r["ok"])
        self.assertTrue(any("TODO:" in e for e in r["errors"]))

    def test_each_kind_of_problem_is_reported(self):
        good = (ROOT / "tests" / "fixtures" / "valid_bundle.md").read_text(encoding="utf-8")
        cases = [
            ("a different section id", good.replace("## Summary {#summary}", "## Summary {#resume}"), "Section ids differ"),
            ("a missing paragraph", good.replace("The problem in one sentence.\n\n", "", 1), "different number of paragraphs"),
            ("a missing diagram", good.replace("```mermaid Current flow.\nflowchart LR\n  A[\"System A\"] --> B[\"System B\"]\n```\n\n", "", 1), "different number of"),
            ("a changed code sample", good.replace('curl -X GET "https://api.example.com/v1/items"', "curl https://other", 2).replace("curl https://other", "curl -X GET https://x", 1), "not identical"),
            ("a TODO", good.replace("Another sentence.", "TODO: fill"), "TODO:"),
            ("a broken link", good.replace("The problem in one sentence.", "See [x](#nowhere)."), "does not match any section id"),
            ("a code block without language", good.replace("```bash\ncurl -X GET", "```\ncurl -X GET", 1), "needs a language"),
            ("no metadata", good.replace("title_zh: 测试集成\n", ""), "title_zh"),
            ("too large", good + "x" * 600001, "too large"),
        ]
        for name, text, expect in cases:
            with self.subTest(name):
                r = self.check(text)
                self.assertFalse(r["ok"], name)
                self.assertTrue(any(expect in e for e in r["errors"]), r["errors"])

    def test_raw_html_in_an_upload_is_shown_as_text_never_run(self):
        good = (ROOT / "tests" / "fixtures" / "valid_bundle.md").read_text(encoding="utf-8")
        evil = good.replace("The problem in one sentence.", '<script>alert(1)</script> and <img src=x onerror=alert(2)>')
        out = self.js("(t) => { const r = R.check.checkBundle(t); return R.sanitize.sanitize(R.page.pageBody(r.bodies.en.body, 'en').html); }", evil)
        self.assertNotIn("<script", out)
        self.assertNotIn("<img", out)
        self.assertNotIn("onerror=\"", out)
        self.assertIn("&lt;script&gt;", out)

    # -- images attached to the RFC ------------------------------------------
    def with_image(self, pt="diagram.png", en="diagram.png", zh="diagram.png"):
        good = (ROOT / "tests" / "fixtures" / "valid_bundle.md").read_text(encoding="utf-8")
        out = good.replace("O problema em uma frase.", f"O problema em uma frase.\n\n![Arquitetura](asset:{pt})", 1)
        out = out.replace("The problem in one sentence.", f"The problem in one sentence.\n\n![Architecture](asset:{en})", 1)
        return out.replace("一句话说明问题。", f"一句话说明问题。\n\n![架构](asset:{zh})", 1)

    def test_images_must_be_attached_and_the_same_in_the_three_languages(self):
        js = "([t, a]) => { const r = R.check.checkBundle(t, { assets: a }); return { ok: r.ok, errors: r.errors, warnings: r.warnings, images: r.images }; }"
        r = self.js(js, [self.with_image(), ["diagram.png"]])
        self.assertTrue(r["ok"], r["errors"])
        self.assertEqual(r["images"], ["diagram.png"])
        r = self.js(js, [self.with_image(), []])
        self.assertFalse(r["ok"])
        self.assertTrue(any('uses the image "diagram.png" but it is not attached' in e for e in r["errors"]), r["errors"])
        r = self.js(js, [self.with_image(zh="other.png"), ["diagram.png", "other.png"]])
        self.assertTrue(any("same images" in e for e in r["errors"]), r["errors"])
        r = self.js(js, [self.with_image(), ["diagram.png", "unused.png"]])
        self.assertTrue(r["ok"])
        self.assertTrue(any("unused.png" in w for w in r["warnings"]), r["warnings"])

    def test_the_sanitizer_keeps_the_attachment_name_and_never_a_source(self):
        out = self.js("(h) => R.sanitize.sanitize(h)", '<p><img data-asset="a.png" alt="x" src="https://evil.example/t.png" onerror="alert(1)"></p>'
                      '<p><img data-asset="Bad Name.png" alt="y"></p><p><img data-asset="b.png" src="javascript:alert(1)"></p>')
        self.assertIn('data-asset="a.png"', out)
        self.assertIn('data-asset="b.png"', out)
        self.assertNotIn("Bad Name", out)
        self.assertNotIn("evil.example", out)
        self.assertNotIn("javascript:", out)
        self.assertNotIn("onerror", out)
        self.assertNotIn("src=", out)

    def test_renderer_reports_authoring_mistakes(self):
        for text, expect in [("No heading here\n", "before the first"), ("## No id\n", "needs a lowercase id"),
                             ("## A {#a}\n\n[x](#nope)\n", "does not match any section id"),
                             ("## A {#a}\n\n```\ncode\n```\n", "needs a language"),
                             ("## A {#a}\n\n## B {#a}\n", "duplicate section id")]:
            with self.subTest(expect=expect):
                err = self.js("([t]) => { try { R.markdown.renderBody(t, 'pt'); return ''; } catch (e) { return e.message; } }", [text])
                self.assertIn(expect, err)

    # -- what visitors submit ----------------------------------------------
    def test_raw_html_is_not_rendered_for_submitted_rfcs(self):
        for vector in XSS:
            with self.subTest(vector=vector):
                body = self.js("([t]) => R.markdown.renderBody(t, 'pt', { html: false }).body", [f"## A {{#a}}\n\n{vector}\n"])
                self.assertNotIn("<script", body)
                self.assertNotIn("<iframe", body)
                self.assertNotIn("<svg", body)
                self.assertNotIn("onerror=", body.replace("&lt;", "<").split("&gt;")[0] if "<img" in body else "")
                self.assertTrue("&lt;" in body or vector.startswith("<h2"), body)

    def test_sanitizer_strips_what_could_run_code(self):
        for vector in XSS:
            with self.subTest(vector=vector):
                out = self.js("(h) => R.sanitize.sanitize(h)", f'<section><h2 id="pt-a">A</h2>{vector}</section>')
                low = out.lower()
                for bad in ("<script", "onerror", "onclick", "onload", "javascript:", "<iframe", "<style", "<svg", "<form", "<input", 'id="phiz_site"', "http://insecure"):
                    self.assertNotIn(bad, low, f"{vector!r} -> {out!r}")
                self.assertNotIn("<button>", low)

    def test_sanitizer_keeps_what_the_renderer_produces(self):
        text = (ROOT / "tests" / "fixtures" / "syntax.md").read_text(encoding="utf-8")
        body = self.js("([t]) => R.markdown.renderBody(t, 'pt', { html: false }).body", [text])
        out = self.js("(h) => R.sanitize.sanitize(h)", body.replace('id="§', 'id="pt-').replace('href="#§', 'href="#pt-'))
        for keep in ('class="tbl map"', 'class="note-box decision"', 'class="stats"', 'class="phase first"', 'class="qs"', 'class="eps"',
                     'class="diagram"', 'class="cap"', 'class="t-k"', "data-copy", 'id="pt-basics"', 'href="#pt-lists"'):
            self.assertIn(keep, out)
        self.assertIn('target="_blank"', out)                       # external links open safely
        self.assertIn('rel="noopener noreferrer"', out)
        self.assertIn('src="https://example.com/i.png"', out)        # https images stay
        self.assertIn('referrerpolicy="no-referrer"', out)
        self.assertEqual(out.count("<section"), 6)


if __name__ == "__main__":
    unittest.main()
