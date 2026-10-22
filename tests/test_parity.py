"""The Python renderer (tools/rfc_md.py, used by the build) and the JavaScript one (assets/js/render/, used in the browser for RFCs
created on the site) must produce the same page. Both render the repository's RFCs, the template and tests/fixtures/syntax.md;
the HTML is compared after normalising whitespace, entities and attribute order."""
import json
import sys
import unittest
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import rfc_md  # noqa: E402
from support import ROOT, SiteCase  # noqa: E402

HOST = """<!doctype html><meta charset="utf-8"><title>render host</title>
<script src="/assets/vendor/markdown-it.min.js"></script>
<script src="/assets/vendor/markdown-it-container.min.js"></script>
<script src="/assets/vendor/purify.min.js"></script>
<script type="module">
import * as markdown from "/assets/js/render/markdown.js";
import * as page from "/assets/js/render/page.js";
import * as blocks from "/assets/js/render/blocks.js";
import * as sanitize from "/assets/js/render/sanitize.js";
import * as bundle from "/assets/js/render/bundle.js";
import * as check from "/assets/js/render/check.js";
window.R = { markdown, page, blocks, sanitize, bundle, check };
window.ready = true;
</script>"""


class Canon(HTMLParser):
    """HTML → a list that ignores formatting: lower-case tags, sorted attributes, collapsed whitespace, decoded entities."""
    VOID = {"br", "hr", "img", "input", "meta", "link", "wbr", "source"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []

    def handle_starttag(self, tag, attrs):
        self.out.append(("<", tag, tuple(sorted((k, v or "") for k, v in attrs))))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag not in self.VOID:
            self.out.append((">", tag))

    def handle_data(self, data):
        if self.out and self.out[-1][0] == "t":
            self.out[-1] = ("t", self.out[-1][1] + data)
        else:
            self.out.append(("t", data))


def canon(html):
    c = Canon()
    c.feed(html)
    c.close()
    out = []
    for item in c.out:
        if item[0] == "t":
            text = " ".join(item[1].split())
            if text:
                out.append(("t", text))
        else:
            out.append(item)
    return out


class ParityTest(SiteCase):
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

    def assertSameBody(self, name, text, lang, html=True):
        py_body, py_ids = rfc_md.render_body(text, lang)
        js = self.js("([t, l, h]) => R.markdown.renderBody(t, l, { html: h })", [text, lang, html])
        self.assertEqual(js["ids"], py_ids, f"{name} [{lang}]: section ids")
        a, b = canon(py_body), canon(js["body"])
        if a != b:
            i = next((k for k in range(min(len(a), len(b))) if a[k] != b[k]), min(len(a), len(b)))
            self.fail(f"{name} [{lang}]: HTML differs at item {i}\n  python: {a[max(0, i - 1):i + 3]}\n  js:     {b[max(0, i - 1):i + 3]}")
        py_s = rfc_md.structure(py_body)
        js_s = self.js("(b) => R.blocks.structure(b)", js["body"])
        self.assertEqual(js_s["blocks"], py_s["blocks"], f"{name} [{lang}]: commentable blocks per section")
        self.assertEqual(js_s["diagrams"], py_s["diagrams"], f"{name} [{lang}]: diagrams")
        self.assertEqual(["".join(c.split()) for c in js_s["code"]], ["".join(c.split()) for c in py_s["code"]], f"{name} [{lang}]: code figures")

    def test_repository_rfcs_render_the_same(self):
        files = sorted(ROOT.glob("rfcs/*/rfc.*.md"))
        self.assertGreaterEqual(len(files), 6)
        for f in files:
            lang = f.name.split(".")[1]
            with self.subTest(f=str(f.relative_to(ROOT))):
                self.assertSameBody(f.parent.name, f.read_text(encoding="utf-8"), lang)

    def test_template_renders_the_same(self):
        for lang in rfc_md.LANGS:
            with self.subTest(lang=lang):
                self.assertSameBody("template", (ROOT / "templates" / "rfc" / f"rfc.{lang}.md").read_text(encoding="utf-8"), lang)

    def test_syntax_fixture_renders_the_same(self):
        text = (ROOT / "tests" / "fixtures" / "syntax.md").read_text(encoding="utf-8")
        for lang in ("pt", "en", "zh"):
            with self.subTest(lang=lang):
                self.assertSameBody("syntax.md", text, lang)

    def test_header_and_contents_list_are_the_same(self):
        metas = [
            {"id": "PHZ-9001", "title": {"pt": "Título <b>", "en": "Title", "zh": "标题"}, "summary": {"pt": "a & b", "en": "s", "zh": "摘要"},
             "status": "in-review", "authors": [{"pt": "Ana - Produto", "en": "Ana - Product", "zh": "Ana - 产品"}],
             "collaborators": ["Bo", "Cy"], "created": "2026-10-22",
             "reviewers": [{"name": "Dee", "country": "BR"}, {"name": "Eli", "country": "CN"}, "Fay"],
             "details": [{"label": {"pt": "Versão da API", "en": "API version", "zh": "API 版本"},
                          "value": {"pt": "<code>v1</code> (proposta)", "en": "<code>v1</code> (proposed)", "zh": "<code>v1</code>（拟）"}}],
             "systems": ["channel", "vault"]},
            {"id": "PHZ-9002", "title": {"pt": "T", "en": "T", "zh": "T"}, "summary": {"pt": "s", "en": "s", "zh": "s"}, "status": "draft",
             "authors": [], "reviewers": [], "created": "2026-01-02"},
        ]
        for meta in metas:
            for lang in rfc_md.LANGS:
                for status in (None, "approved"):
                    with self.subTest(id=meta["id"], lang=lang, status=status):
                        js = self.js("([m, l, s]) => R.page.heroHtml(m, l, s)", [meta, lang, status])
                        self.assertEqual(canon(js), canon(rfc_md.hero_html(meta, lang, status)))

    def test_contents_list_matches_the_built_page(self):
        folder = ROOT / "rfcs" / "PHZ-0002"
        meta = rfc_md.read_meta(folder)
        built = rfc_md.render_page(folder, meta)
        import re
        for lang in rfc_md.LANGS:
            text = (folder / f"rfc.{lang}.md").read_text(encoding="utf-8")
            body = self.js("([t, l]) => R.markdown.renderBody(t, l, { html: true }).body", [text, lang])
            toc = self.js("([b, l]) => R.page.pageBody(b, l).toc", [body, lang])
            expected = re.search(rf'<ol class="toc-list" data-lang="{lang}"[^>]*>(.*?)</ol>', built, re.S).group(1)
            self.assertEqual(canon(toc), canon(expected), lang)


if __name__ == "__main__":
    unittest.main()
