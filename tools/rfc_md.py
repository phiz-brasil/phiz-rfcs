"""Markdown RFCs: renders rfcs/<ID>/rfc.{pt,en,zh}.md into the page the site expects, and checks the rules of
docs/spec/rfc-format.md.

Needs `markdown-it-py` and `mdit-py-plugins` (requirements.txt). RFCs written as HTML do not use this module,
so tools/build.py still runs without those packages when the repository has only HTML RFCs.
"""
import html
import json
import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "templates"
LANGS = ("pt", "en", "zh")
BCP = {"pt": "pt-BR", "en": "en-US", "zh": "zh-CN"}

STATUS = {
    "draft":       {"pt": "Rascunho",     "en": "Draft",       "zh": "草稿"},
    "in-review":   {"pt": "Em revisão",   "en": "In review",   "zh": "评审中"},
    "approved":    {"pt": "Aprovada",     "en": "Approved",    "zh": "已批准"},
    "implemented": {"pt": "Implementada", "en": "Implemented", "zh": "已实现"},
    "rejected":    {"pt": "Rejeitada",    "en": "Rejected",    "zh": "已拒绝"},
    "superseded":  {"pt": "Substituída",  "en": "Superseded",  "zh": "已被取代"},
}

HERO = {
    "pt": {"status": "Status", "author": "Autor", "date": "Data", "reviewers": "Revisores", "systems": "Sistemas", "tbd": "A definir"},
    "en": {"status": "Status", "author": "Author", "date": "Date", "reviewers": "Reviewers", "systems": "Systems", "tbd": "To be defined"},
    "zh": {"status": "状态", "author": "作者", "date": "日期", "reviewers": "评审人", "systems": "系统", "tbd": "待定"},
}
NOTE_LABELS = {
    "note": {"pt": "Nota", "en": "Note", "zh": "备注"},
    "decision": {"pt": "Decisão", "en": "Decision", "zh": "决定"},
    "risk": {"pt": "A confirmar", "en": "To confirm", "zh": "待确认"},
}
DIRECTIVES = ("note", "decision", "risk", "stats", "phases", "questions", "endpoints", "table")
TABLE_VARIANTS = ("changes", "num", "map")
METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE")
CODE_LANGS = ("json", "bash", "http", "python", "yaml", "java", "javascript", "typescript", "dart", "kotlin", "go", "sql", "text")
SLUG = re.compile(r"[a-z0-9][a-z0-9-]*")


class RfcError(Exception):
    """A problem in an RFC's Markdown, with a message meant to be read by its author."""


# ---------------------------------------------------------------- code highlighting (same look as the HTML RFCs)

def hl_json(src):
    out = []
    tok = re.compile(r'("(?:[^"\\]|\\.)*")(\s*:)?|(-?\b\d+(?:\.\d+)?\b)|\b(true|false|null)\b|([{}\[\],:])|(\s+)|(.)', re.S)
    for m in tok.finditer(src):
        s, colon, num, kw, punct, ws, other = m.groups()
        if s is not None:
            cls = "k" if colon else "s"
            out.append(f'<span class="t-{cls}">{html.escape(s)}</span>' + (html.escape(colon) if colon else ""))
        elif num is not None:
            out.append(f'<span class="t-n">{num}</span>')
        elif kw is not None:
            out.append(f'<span class="t-b">{kw}</span>')
        else:
            out.append(html.escape(punct or ws or other))
    return "".join(out)


def hl_generic(src, lang):
    esc = html.escape(src)
    if lang in ("bash", "http", "python", "yaml"):
        esc = re.sub(r'(&#x27;[^\n]*?&#x27;|&quot;[^&\n]*?&quot;)', r'<span class="t-s">\1</span>', esc)
        esc = re.sub(r'(?m)(#[^\n]*)$', r'<span class="t-c">\1</span>', esc)
    if lang == "http":
        esc = re.sub(r'(?m)^(GET|POST|PUT|PATCH|DELETE)( )', r'<span class="t-k">\1</span>\2', esc)
    if lang in ("java", "javascript", "typescript", "dart", "kotlin", "go"):
        esc = re.sub(r'(?m)(//[^\n]*)$', r'<span class="t-c">\1</span>', esc)
        esc = re.sub(r'\b(static|return|new|const|let|final|func|class|public|private)\b', r'<span class="t-k">\1</span>', esc)
    return esc


def code_figure(lang, src):
    src = src.rstrip("\n")
    body = hl_json(src) if lang == "json" else hl_generic(src, lang)
    return (f'<figure class="code"><figcaption><span>{html.escape(lang.upper())}</span>'
            f'<button type="button" class="copy" data-copy>COPY</button></figcaption>'
            f'<pre><code>{body}</code></pre></figure>\n')


# ---------------------------------------------------------------- Markdown → body HTML

def _parser():
    try:
        from markdown_it import MarkdownIt
        from mdit_py_plugins.container import container_plugin
    except ImportError:
        raise RfcError("Markdown RFCs need markdown-it-py and mdit-py-plugins: "
                       "python3 -m venv .venv && .venv/bin/pip install -r requirements.txt, then run with .venv/bin/python")
    md = MarkdownIt("commonmark", {"html": True}).enable("table")

    def container(name, render):
        container_plugin(md, name, validate=lambda params, markup, n=name: params.strip().split(" ", 1)[0] == n, render=render)

    def note_render(name):
        def render(self, tokens, idx, options, env):
            tok = tokens[idx]
            if tok.nesting == 1:
                label = tok.info.strip()[len(name):].strip() or NOTE_LABELS[name][env["lang"]]
                cls = "note-box" + ("" if name == "note" else " " + name)
                return f'<div class="{cls}"><span class="lbl">{html.escape(label)}</span>\n'
            return "</div>\n"
        return render

    def table_render(self, tokens, idx, options, env):
        tok = tokens[idx]
        if tok.nesting == 1:
            variant = tok.info.strip()[len("table"):].strip()
            if variant and variant not in TABLE_VARIANTS:
                raise RfcError(f"::: table {variant}: unknown variant (use {', '.join(TABLE_VARIANTS)})")
            env["tbl"] = (" " + variant) if variant else ""
        return ""

    for name in ("note", "decision", "risk"):
        container(name, note_render(name))
    container("table", table_render)
    for name in ("stats", "phases", "questions", "endpoints"):
        container(name, lambda self, tokens, idx, options, env: "")   # rewritten by the core rule below

    def table_open(self, tokens, idx, options, env):
        return f'<div class="tbl{env.pop("tbl", "")}"><table>\n'

    md.add_render_rule("table_open", table_open)
    md.add_render_rule("table_close", lambda self, tokens, idx, options, env: "</table></div>\n")

    def fence(self, tokens, idx, options, env):
        tok = tokens[idx]
        parts = tok.info.strip().split(None, 1)
        lang = parts[0].lower() if parts else ""
        if lang == "mermaid":
            cap = f'<p class="cap">{html.escape(parts[1])}</p>\n' if len(parts) > 1 else ""
            return f'<div class="diagram"><pre class="mermaid">\n{html.escape(tok.content)}</pre></div>\n{cap}'
        if lang not in CODE_LANGS:
            raise RfcError(f"line {tok.map[0] + 1}: code block needs a language ({', '.join(CODE_LANGS)} or mermaid), got {lang!r}")
        return code_figure(lang, tok.content)

    md.add_render_rule("fence", fence)
    md.core.ruler.push("rfc_blocks", _core_rule)
    return md


def _html_block(text):
    from markdown_it.token import Token
    t = Token("html_block", "", 0)
    t.content = text
    return t


def _render_inline(state, inline):
    return state.md.renderer.renderInline(inline.children or [], state.md.options, state.env)


def _list_items(inner):
    """The inline token of each list item found in `inner`."""
    return [t for i, t in enumerate(inner) if t.type == "inline" and i > 0 and inner[i - 1].type == "paragraph_open"
            and any(x.type == "list_item_open" for x in inner[max(0, i - 2):i])]


def _core_rule(state):
    if state.inlineMode:       # md.renderInline() (endpoint descriptions) runs the core rules too
        return
    toks, env = state.tokens, state.env
    env.setdefault("ids", [])
    out, i, n, in_section, number = [], 0, len(toks), False, 0
    while i < n:
        t = toks[i]
        if t.type == "heading_open" and t.tag == "h2":
            inline = toks[i + 1]
            m = re.search(r"\s*\{#([^}\s]*)\}\s*$", inline.content)
            line = (t.map[0] + 1) if t.map else "?"
            if not m or not SLUG.fullmatch(m.group(1)):
                raise RfcError(f"line {line}: a level-2 heading needs a lowercase id, e.g. '## Summary {{#summary}}'")
            sid = m.group(1)
            if sid in env["ids"]:
                raise RfcError(f"line {line}: duplicate section id {sid!r}")
            inline.content = inline.content[:m.start()]
            for child in reversed(inline.children or []):
                if child.type == "text":
                    child.content = re.sub(r"\s*\{#[^}\s]*\}\s*$", "", child.content)
                    break
            number += 1
            env["ids"].append(sid)
            out += [_html_block(("</section>\n" if in_section else "") + f'<section>\n<h2 id="§{sid}"><span class="n">{number:02d}</span>'),
                    inline, _html_block("</h2>\n")]
            in_section = True
            i += 3
            continue
        if not in_section:
            if t.type == "html_block" and t.content.strip().startswith("<!--"):
                i += 1
                continue
            raise RfcError(f"line {(t.map[0] + 1) if t.map else '?'}: content before the first '##' section heading")
        m = re.match(r"container_(stats|phases|questions|endpoints)_open$", t.type)
        if m:
            name = m.group(1)
            j = i + 1
            while j < n and toks[j].type != f"container_{name}_close":
                j += 1
            if j >= n:
                raise RfcError(f"line {(t.map[0] + 1) if t.map else '?'}: ':::' {name} block is not closed")
            out += _directive(state, name, toks[i + 1:j], (t.map[0] + 1) if t.map else "?")
            i = j + 1
            continue
        out.append(t)
        i += 1
    if in_section:
        out.append(_html_block("</section>\n"))
    state.tokens = out


def _directive(state, name, inner, line):
    if name == "questions":
        lists = [t for t in inner if t.type == "ordered_list_open"]
        if not lists:
            raise RfcError(f"line {line}: ::: questions needs a numbered list")
        lists[0].attrSet("class", "qs")
        return inner
    if name == "stats":
        items = _list_items(inner)
        if not items:
            raise RfcError(f"line {line}: ::: stats needs a list like '- **8** integrations today'")
        rows = []
        for it in items:
            m = re.match(r"^<strong>(.*?)</strong>\s*(.*)$", _render_inline(state, it), re.S)
            if not m:
                raise RfcError(f"line {line}: each stat starts with a bold number: '- **8** text'")
            rows.append(f'<div class="stat"><b>{m.group(1)}</b><span>{m.group(2)}</span></div>')
        return [_html_block('<div class="stats">\n' + "\n".join(rows) + "\n</div>\n")]
    if name == "endpoints":
        items = _list_items(inner)
        if not items:
            raise RfcError(f"line {line}: ::: endpoints needs a list like '- POST /v1/payment — what it does'")
        rows = []
        for it in items:
            m = re.match(r"^(%s)\s+`?([^\s`]+)`?\s+[—–-]+\s+(.+)$" % "|".join(METHODS), it.content.strip(), re.S)
            if not m:
                raise RfcError(f"line {line}: endpoint items look like 'POST /v1/payment — what it does', got {it.content.strip()[:50]!r}")
            desc = state.md.renderInline(m.group(3), state.env)
            rows.append(f'<div class="ep"><span class="m m-{m.group(1).lower()}">{m.group(1)}</span>'
                        f'<code class="p">{html.escape(m.group(2))}</code><span class="d">{desc}</span></div>')
        return [_html_block('<div class="eps">\n' + "\n".join(rows) + "\n</div>\n")]
    # phases: each '##### TAG: Name' heading opens a card that runs until the next one
    out, open_card, first = [], False, True
    k = 0
    while k < len(inner):
        t = inner[k]
        if t.type == "heading_open" and t.tag == "h5":
            text = inner[k + 1].content
            m = re.match(r"^(.*?)\s*[:：]\s*(.+)$", text)
            if not m:
                raise RfcError(f"line {line}: phase headings look like '##### PHASE 1: Name'")
            out.append(_html_block(("</div>\n" if open_card else "") +
                                   f'<div class="phase{" first" if first else ""}"><span class="tag">{html.escape(m.group(1))}</span>'
                                   f"<h5>{html.escape(m.group(2))}</h5>\n"))
            open_card, first = True, False
            k += 3
            continue
        if not open_card:
            raise RfcError(f"line {line}: ::: phases must start with a '##### PHASE 0: Name' heading")
        out.append(t)
        k += 1
    if not open_card:
        raise RfcError(f"line {line}: ::: phases needs at least one '##### PHASE N: Name' heading")
    return [_html_block('<div class="phases">\n')] + out + [_html_block("</div>\n</div>\n")]


def render_body(text, lang):
    """Markdown → (html with `§` ids, section ids)."""
    md = _parser()
    env = {"lang": lang, "ids": []}
    body = md.render(text, env)
    ids = env["ids"]
    if not ids:
        raise RfcError("no '##' sections found")

    def link(m):
        sid = m.group(1)
        if sid not in ids:
            raise RfcError(f"link to #{sid} does not match any section id ({', '.join(ids)})")
        return f'href="#§{sid}"'
    body = re.sub(r'href="#([a-z0-9-]+)"', link, body)
    return body, ids


# ---------------------------------------------------------------- structure checks (same numbering as the comments in the page)

class _Blocks(HTMLParser):
    """Counts, per section, the blocks that get a comment button in the page (assets/rfc-site.js, paraBlocks)."""
    VOID = {"br", "hr", "img", "input", "meta", "link", "wbr", "source"}

    def __init__(self):
        super().__init__()
        self.stack, self.counts, self.diagrams, self.code = [], [], 0, []
        self._code = None

    def handle_starttag(self, tag, attrs):
        cls = set((dict(attrs).get("class") or "").split())
        if tag == "section":
            self.counts.append(0)
        elif self.counts:
            excluded = any(t == "figure" or c & {"tbl", "diagram", "eps-wrap"} for t, c in self.stack)
            parent_li = bool(self.stack) and self.stack[-1][0] == "li"
            if not excluded and (
                    (tag == "p" and "cap" not in cls and not parent_li) or tag == "li"
                    or (tag == "div" and cls & {"tbl", "diagram"}) or (tag == "figure" and "code" in cls)):
                self.counts[-1] += 1
        if tag == "div" and "diagram" in cls:
            self.diagrams += 1
        if tag == "figure" and "code" in cls:
            self._code = []
        if tag not in self.VOID:
            self.stack.append((tag, cls))

    def handle_endtag(self, tag):
        if tag == "figure" and self._code is not None:
            self.code.append("".join(self._code))
            self._code = None
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        if self._code is not None:
            self._code.append(data)


def structure(body):
    p = _Blocks()
    p.feed(body)
    return {"blocks": p.counts, "diagrams": p.diagrams, "code": p.code}


def md_files(folder):
    return {l: Path(folder) / f"rfc.{l}.md" for l in LANGS}


def is_markdown_rfc(folder):
    return (Path(folder) / "rfc.pt.md").exists() or (Path(folder) / "rfc.en.md").exists()


def read_meta(folder):
    return json.loads((Path(folder) / "rfc.json").read_text(encoding="utf-8"))


def render_all(folder):
    """{lang: (body html, ids)} for the three languages; raises RfcError with the language in the message."""
    out = {}
    for lang, path in md_files(folder).items():
        if not path.exists():
            raise RfcError(f"{path.name} is missing")
        try:
            out[lang] = render_body(path.read_text(encoding="utf-8"), lang)
        except RfcError as e:
            raise RfcError(f"{path.name}: {e}")
    return out


def check(folder, meta=None):
    """(errors, warnings) for one Markdown RFC folder; rules F01-F08 of docs/spec/rfc-format.md."""
    folder = Path(folder)
    errors, warnings = [], []
    try:
        meta = meta or read_meta(folder)
    except (OSError, ValueError) as e:
        return [f"F01 rfc.json: {e}"], warnings
    for key in ("id", "title", "summary", "status", "version", "changelog"):
        if key not in meta:
            errors.append(f"F01 rfc.json: missing {key!r}")
    if meta.get("id") != folder.name:
        errors.append(f"F01 rfc.json: id {meta.get('id')!r} does not match the folder {folder.name!r}")
    if meta.get("status") not in STATUS:
        errors.append(f"F01 rfc.json: status {meta.get('status')!r} is not one of {', '.join(STATUS)}")
    ver = str(meta.get("version", ""))
    if not re.fullmatch(r"\d+\.\d+", ver):
        errors.append(f"F01 rfc.json: version {ver!r} must look like 1.0")
    elif ver not in [str(c.get("version")) for c in meta.get("changelog") or []]:
        errors.append(f"F01 rfc.json: version {ver} is not in the changelog")
    for lang in LANGS:
        if not isinstance(meta.get("title"), dict) or not meta["title"].get(lang):
            errors.append(f"F01 rfc.json: title.{lang} is missing")
    if (meta.get("summary") or {}).get("pt") in ("Uma frase.", "One sentence."):
        warnings.append("F08 rfc.json: summary still has the default text")

    missing = [p.name for p in md_files(folder).values() if not p.exists()]
    if missing:
        return errors + [f"F02 missing {', '.join(missing)}"], warnings
    for lang, path in md_files(folder).items():
        todo = [n for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1) if "TODO:" in line]
        if todo:
            more = f" (+{len(todo) - 1} more)" if len(todo) > 1 else ""
            errors.append(f"F08 {path.name}: {len(todo)} TODO marker{'s' if len(todo) > 1 else ''} left, first at line {todo[0]}{more}")

    try:
        rendered = render_all(folder)
    except RfcError as e:
        return errors + [f"F03 {e}"], warnings
    ids = {l: rendered[l][1] for l in LANGS}
    if not (ids["pt"] == ids["en"] == ids["zh"]):
        for l in ("en", "zh"):
            if ids[l] != ids["pt"]:
                errors.append(f"F04 section ids differ between pt and {l}: pt={ids['pt']} {l}={ids[l]}")
        return errors, warnings
    st = {l: structure(rendered[l][0]) for l in LANGS}
    for k, sid in enumerate(ids["pt"]):
        counts = {l: st[l]["blocks"][k] if k < len(st[l]["blocks"]) else 0 for l in LANGS}
        if len(set(counts.values())) > 1:
            errors.append(f"F05 section {sid!r} has a different number of paragraphs/list items/tables/diagrams/code blocks: "
                          f"pt {counts['pt']} · en {counts['en']} · zh {counts['zh']} (per-paragraph comments use these numbers)")
    d = {l: st[l]["diagrams"] for l in LANGS}
    if len(set(d.values())) > 1:
        errors.append(f"F06 different number of diagrams: pt {d['pt']} · en {d['en']} · zh {d['zh']}")
    for l in ("en", "zh"):
        if st[l]["code"] != st["pt"]["code"] and len(st[l]["code"]) == len(st["pt"]["code"]):
            errors.append(f"F06 code blocks in {l} are not identical to pt (samples are shared across languages; comments in English)")
        elif len(st[l]["code"]) != len(st["pt"]["code"]):
            errors.append(f"F06 different number of code blocks: pt {len(st['pt']['code'])} · {l} {len(st[l]['code'])}")
    return errors, warnings


# ---------------------------------------------------------------- page

def _date(iso, lang):
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", iso or "")
    return f"{m.group(3)}/{m.group(2)}/{m.group(1)}" if (m and lang == "pt") else (iso or "")


def hero_html(meta, lang, status=None):
    h, st = HERO[lang], status or meta["status"]
    label = html.escape(STATUS[st][lang])
    systems = meta.get("systems") or []
    rows = [
        f'<div><dt>{h["status"]}</dt><dd><span class="pill" data-st="{st}">{label}</span></dd></div>',
        f'<div><dt>{h["author"]}</dt><dd>{html.escape(", ".join(meta.get("authors") or []) or "—")}</dd></div>',
        f'<div><dt>{h["date"]}</dt><dd>{html.escape(_date(meta.get("created"), lang))}</dd></div>',
        f'<div><dt>{h["reviewers"]}</dt><dd>{"<br>".join(html.escape(r) for r in meta.get("reviewers") or []) or h["tbd"]}</dd></div>',
    ]
    if systems:
        rows.append(f'<div><dt>{h["systems"]}</dt><dd>{html.escape(" · ".join(systems))}</dd></div>')
    return (f'<header class="hero">\n  <div class="eyebrow">RFC {html.escape(meta["id"])} · {label}</div>\n'
            f'  <h1>{html.escape(meta["title"][lang])}</h1>\n'
            f'  <p class="lede">{html.escape(meta["summary"][lang])}</p>\n'
            f'  <dl class="meta">\n    ' + "\n    ".join(rows) + "\n  </dl>\n</header>\n")


def render_page(folder, meta, status=None):
    """The full page (what source.html holds for HTML RFCs) for the Markdown files in `folder`."""
    rendered = render_all(folder)
    blocks, tocs = [], []
    for lang in LANGS:
        body, ids = rendered[lang]
        body = body.replace('id="§', f'id="{lang}-').replace('href="#§', f'href="#{lang}-')
        toc = "".join(f'<li><a href="#{lang}-{m.group(1)}">{re.sub(r"<[^>]+>", "", re.sub(r"<span class=.n.>.*?</span>", "", m.group(2))).strip()}</a></li>'
                      for m in re.finditer(r'<h2 id="%s-([^"]+)">(.*?)</h2>' % lang, body, re.S))
        blocks.append(f'<div class="lang" data-lang="{lang}" lang="{BCP[lang]}">{hero_html(meta, lang, status)}{body}</div>')
        tocs.append(f'<ol class="toc-list" data-lang="{lang}" lang="{BCP[lang]}">{toc}</ol>')
    shell = (TEMPLATES / "shell.html").read_text(encoding="utf-8")
    css = (TEMPLATES / "page.css").read_text(encoding="utf-8")
    short = meta.get("short") or meta["title"]["en"]
    return (shell.replace("{{ID}}", html.escape(meta["id"])).replace("{{SHORT_TITLE}}", html.escape(short))
            .replace("/*CSS*/", css).replace("<!--CONTENT-->", "\n".join(blocks)).replace("<!--TOC-->", "\n".join(tocs)))
