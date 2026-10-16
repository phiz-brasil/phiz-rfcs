"""Builds rfcs/<ID>/source.html from this folder: a trilingual RFC page (PT-BR, EN-US, 中文)
with a contents rail, shared code samples and Mermaid diagrams.

Run from this folder:  python3 build_rfc.py

Inputs (all in this folder):
  content_pt.html, content_en.html, content_zh.html   one per language, same <h2 id="§..."> ids
  code.json      {"name": ["lang", "source"]}  shared by the three languages, used as {CODE:name}
  shell.html     page frame (header, language switch, contents rail)
  page.css       styles
The RFC id is this folder's name (e.g. PHZ-0003).
"""
import html
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
RFC_ID = os.path.basename(HERE)
OUT = os.path.join(HERE, "..", "..", "rfcs", RFC_ID, "source.html")
LANGS = [("pt", "pt-BR"), ("en", "en-US"), ("zh", "zh-CN")]


def load_code():
    p = os.path.join(HERE, "code.json")
    if not os.path.exists(p):
        return {}
    raw = json.load(open(p, encoding="utf-8"))
    out = {}
    for name, (lang, src) in raw.items():
        # JSON samples may be given as objects; they are pretty-printed for display
        out[name] = (lang, src if isinstance(src, str) else json.dumps(src, ensure_ascii=False, indent=2))
    return out


CODE = load_code()


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


def code_block(name):
    if name not in CODE:
        raise SystemExit(f"{{CODE:{name}}} is used but missing from code.json")
    lang, src = CODE[name]
    body = hl_json(src) if lang == "json" else hl_generic(src, lang)
    return (f'<figure class="code"><figcaption><span>{lang.upper()}</span>'
            f'<button type="button" class="copy" data-copy>COPY</button></figcaption>'
            f'<pre><code>{body}</code></pre></figure>')


def render_lang(lang):
    src = open(os.path.join(HERE, f"content_{lang}.html"), encoding="utf-8").read()
    src = src.replace('id="§', f'id="{lang}-').replace('href="#§', f'href="#{lang}-')
    src = re.sub(r"\{CODE:(\w+)\}", lambda m: code_block(m.group(1)), src)
    toc = []
    for m in re.finditer(r'<h2 id="([^"]+)"[^>]*>(.*?)</h2>', src):
        label = re.sub("<[^>]+>", "", re.sub(r'<span class="n">.*?</span>', "", m.group(2)))
        toc.append(f'<li><a href="#{m.group(1)}">{label}</a></li>')
    return src, "".join(toc)


def main():
    css = open(os.path.join(HERE, "page.css"), encoding="utf-8").read()
    shell = open(os.path.join(HERE, "shell.html"), encoding="utf-8").read()
    blocks, tocs, ids, mermaids = [], [], [], []
    for l, bcp in LANGS:
        body, toc = render_lang(l)
        ids.append([re.sub(rf"^{l}-", "", i) for i in re.findall(r'<h2 id="([^"]+)"', body)])
        mermaids.append(body.count('class="mermaid"'))
        blocks.append(f'<div class="lang" data-lang="{l}" lang="{bcp}">{body}</div>')
        tocs.append(f'<ol class="toc-list" data-lang="{l}" lang="{bcp}">{toc}</ol>')
    if not (ids[0] == ids[1] == ids[2]):
        raise SystemExit(f"section ids differ between languages: {ids}")
    if len(set(mermaids)) != 1:
        raise SystemExit(f"diagram count differs between languages (pt, en, zh): {mermaids}")
    page = shell.replace("/*CSS*/", css).replace("<!--CONTENT-->", "\n".join(blocks)).replace("<!--TOC-->", "\n".join(tocs))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"{RFC_ID}: sections {len(ids[0])}, diagrams per language {mermaids[0]}, bytes {len(page.encode())}")


if __name__ == "__main__":
    main()
