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
