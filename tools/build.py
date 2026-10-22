#!/usr/bin/env python3
"""Builds the static site into dist/.

  rfcs/<ID>/rfc.json     metadata (status, authors, reviewers, titles, summaries)
  rfcs/<ID>/rfc.{pt,en,zh}.md   the RFC (Markdown, see docs/spec/rfc-format.md)
  rfcs/<ID>/openapi_gen.py      optional: builds the OpenAPI spec shown at the end of the page
  rfcs/<ID>/versions/<v>/       archived older versions (Markdown, or the HTML page of versions archived before Markdown)
  rfcs/<ID>/*            other files (images…) are copied as is
Folders that start with "_" (e.g. _template) are ignored.
"""
import html, json, re, shutil, sys
from pathlib import Path

import rfc_md
from rfc_md import LANGS, STATUS

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
CFG = json.loads((ROOT / "site.config.json").read_text(encoding="utf-8"))

e = html.escape


def spans(d, cls=""):
    return "".join(f'<span data-l="{l}"{f" class={chr(34)}{cls}{chr(34)}" if cls else ""}>{e(d[l])}</span>' for l in LANGS)


def load():
    out = []
    for d in sorted((ROOT / "rfcs").iterdir()):
        if not d.is_dir() or d.name.startswith("_"):
            continue
        meta = json.loads((d / "rfc.json").read_text(encoding="utf-8"))
        if meta["status"] not in STATUS:
            sys.exit(f"{d.name}: invalid status {meta['status']!r}; use one of {', '.join(STATUS)}")
        try:
            errors, warnings = rfc_md.check(d, meta)
        except rfc_md.RfcError as err:
            errors, warnings = [str(err)], []
        for w in warnings:
            print(f"warning: {d.name}: {w}")
        if errors:
            sys.exit(f"{d.name}: " + "\n  ".join(["cannot build, fix with tools/check_rfc.py:"] + errors))
        out.append((d, meta))
    return out


VER_RE = re.compile(r"\d+\.\d+")
T_VERSIONS = {"pt": "Histórico de versões", "en": "Version history", "zh": "版本历史"}
T_CURRENT = {"pt": "atual", "en": "current", "zh": "当前"}
T_NOFILE = {"pt": "sem arquivo", "en": "no archive", "zh": "无存档"}


def versions_of(d, meta):
    """(current version, changelog newest first). Older rfc.json without versioning counts as 1.0."""
    cur = str(meta.get("version", "1.0"))
    if not VER_RE.fullmatch(cur):
        sys.exit(f"{d.name}: invalid version {cur!r}; use MAJOR.MINOR, e.g. 1.0")
    log = meta.get("changelog") or [{"version": cur, "date": meta.get("created", ""), "note": {l: "" for l in LANGS}}]
    seen = [str(x["version"]) for x in log]
    if cur not in seen:
        sys.exit(f"{d.name}: version {cur} is missing from changelog")
    if len(set(seen)) != len(seen):
        sys.exit(f"{d.name}: duplicate versions in changelog")
    return cur, log


def snapshot(d, v):
    """The frozen copy of version v: the folder with the Markdown files, or source.html for versions archived as HTML."""
    folder = d / "versions" / v
    return folder if rfc_md.is_markdown_rfc(folder) else folder / "source.html"


_PAGES = {}


def page_text(d, meta):
    """The full RFC page of the current version."""
    if d.name not in _PAGES:
        _PAGES[d.name] = rfc_md.render_page(d, meta)
    return _PAGES[d.name]


def versions_html(d, meta, shown):
    cur, log = versions_of(d, meta)
    lis = []
    for ent in log:
        v = str(ent["version"])
        href = "./" if v == cur else (f"v{v}.html" if snapshot(d, v).exists() else None)
        tag = spans(T_CURRENT, "vtag") if v == cur else ("" if href else spans(T_NOFILE, "vtag"))
        head = f'<b>v{e(v)}</b>{tag}<time>{e(ent.get("date", ""))}</time>'
        head = f'<a href="{href}">{head}</a>' if href else f"<span>{head}</span>"
        note = spans({l: ent.get("note", {}).get(l, "") for l in LANGS}, "vnote")
        cur_attr = ' aria-current="true"' if v == shown else ""
        lis.append(f"<li{cur_attr}>{head}<div class=\"vnote-wrap\">{note}</div></li>")
    return (f'<details class="vers"><summary class="rfcno ver" aria-label="Version">v{e(shown)}</summary>'
            f'<div class="vers-pop"><h3>{spans(T_VERSIONS)}</h3><ul>{"".join(lis)}</ul></div></details>')


def banner_html(shown, cur):
    msg = {"pt": f"Você está lendo a versão {shown}, arquivada e somente leitura. A versão atual é a {cur}.",
           "en": f"You are reading version {shown}, archived and read-only. The current version is {cur}.",
           "zh": f"你正在阅读已存档的只读版本 {shown}。当前版本为 {cur}。"}
    go = {"pt": "Ver versão atual", "en": "View current version", "zh": "查看当前版本"}
    return (f'<div class="ver-banner" role="note">{spans(msg)} '
            f'<a href="./">{spans(go)}</a></div>')


def render_rfc(d, meta, text, out, shown, frozen, status, up):
    """Writes one RFC page. `up` is the path from the page to the site root ('../../')."""
    page = rfc_md.wrap_fragment(text)
    cur, _ = versions_of(d, meta)
    page = page.replace("{{UP}}", up)
    page = page.replace('<span class="rfcno">', f'<a class="back" href="{up}">← RFCs</a><span class="rfcno">', 1)
    badge = (f'<span class="rfcno st" data-st="{status}">'
             + "".join(f'<span class="lang-st" data-l="{l}">{e(STATUS[status][l])}</span>' for l in LANGS) + "</span>")
    extra = badge + versions_html(d, meta, shown)
    page = re.sub(r'(<span class="rfcno">[^<]*</span>)', lambda m: m.group(1) + extra, page, count=1)
    if frozen:
        page = page.replace("</header>", "</header>\n" + banner_html(shown, cur), 1)
        page = page.replace("</title>", f" · v{shown}</title>", 1)
    page = page.replace("</title>", f"</title>\n<link rel=\"stylesheet\" href=\"{up}assets/rfc-site.css\">", 1)
    cfg = {"repo": CFG["repo"], "giscus": CFG["giscus"], "comments": CFG.get("comments", {})}
    inject = (f'<script>window.PHIZ_SITE={json.dumps(cfg)};window.PHIZ_RFC_ID={json.dumps(meta["id"])};'
              f'window.PHIZ_FROZEN={json.dumps(frozen)};</script>\n'
              f'<script src="{up}assets/mermaid.min.js"></script>\n<script type="module" src="{up}assets/js/main.js"></script>\n<script src="{up}assets/status.js"></script>\n</body>')
    page = page.replace("</body>", inject, 1) if "</body>" in page else page + inject
    out.write_text(page, encoding="utf-8")


def build_rfc(d, meta):
    dest = DIST / "rfcs" / d.name
    shutil.copytree(d, dest, ignore=shutil.ignore_patterns("source.html", "versions", "rfc.*.md", "openapi_gen.py", "__pycache__"))
    specs = rfc_md.openapi_specs(d)
    if specs:       # the spec is generated from openapi_gen.py: published as files next to the page
        for lang, text in rfc_md.openapi_yaml(specs).items():
            (dest / f"openapi.{lang}.yaml").write_text(text, encoding="utf-8")
    cur, log = versions_of(d, meta)
    render_rfc(d, meta, page_text(d, meta), dest / "index.html", cur, False, meta["status"], "../../")
    for ent in log:
        v = str(ent["version"])
        if v == cur:
            continue
        if not snapshot(d, v).exists():
            print(f"warning: {d.name} v{v} is in the changelog but has no archive ({snapshot(d, v).relative_to(ROOT)})")
            continue
        st = ent.get("status", meta["status"])
        if st not in STATUS:
            sys.exit(f"{d.name} v{v}: invalid status {st!r}")
        snap = snapshot(d, v)
        if snap.is_dir():       # Markdown RFC: render the frozen files with the header data they had
            old = json.loads((snap / "rfc.json").read_text(encoding="utf-8")) if (snap / "rfc.json").exists() else meta
            text = rfc_md.render_page(snap, old, status=st, rfc_dir=d)
        else:
            text = snap.read_text(encoding="utf-8")
        render_rfc(d, meta, text, dest / f"v{v}.html", v, True, st, "../../")



INDEX_CSS = """
:root{--bg:#f6f5f3;--surface:#fff;--ink:#1c1a18;--muted:#6b645d;--line:#e4dfda;--accent:#25d366;--accent-ink:#12803d;--accent-soft:#dcf8e6;color-scheme:light dark}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#141312;--surface:#1c1a19;--ink:#ede8e3;--muted:#a39b93;--line:#302c29;--accent:#25d366;--accent-ink:#5be68f;--accent-soft:#12301f}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:400 1rem/1.6 "IBM Plex Sans",system-ui,sans-serif}
.wrap{max-width:980px;margin:0 auto;padding:0 16px}
header{border-bottom:1px solid var(--line)}header .wrap{display:flex;align-items:center;justify-content:space-between;gap:12px;padding-block:14px;flex-wrap:wrap}
.brand{display:flex;align-items:center;gap:10px;font-weight:700}.logo{width:26px;height:26px;border-radius:7px;background:var(--accent);color:#052e16;display:grid;place-items:center;font-size:.85rem}
.langs{display:inline-flex;border:1px solid var(--line);border-radius:9px;padding:3px;background:var(--surface);gap:2px}
.langs button{font-weight:600;font-size:.78rem;border:0;background:transparent;color:var(--muted);padding:6px 12px;border-radius:6px;cursor:pointer}
.langs button[aria-pressed=true]{background:var(--ink);color:var(--bg)}
h1{font:800 clamp(1.8rem,5vw,2.6rem)/1.1 "Schibsted Grotesk",system-ui,sans-serif;letter-spacing:-.02em;margin:40px 0 8px}
.lead{color:var(--muted);margin:0 0 24px;max-width:60ch}
.filters{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:18px}
.filters button{font-weight:500;font-size:.82rem;border:1px solid var(--line);background:var(--surface);color:var(--ink);border-radius:999px;padding:5px 13px;cursor:pointer}
.filters button[aria-pressed=true]{background:var(--accent);border-color:var(--accent);color:#052e16}
.list{display:grid;gap:12px;padding:0;margin:0 0 60px;list-style:none}
.card{display:block;border:1px solid var(--line);background:var(--surface);border-radius:14px;padding:16px 18px;color:inherit;text-decoration:none}
.card:hover{border-color:var(--accent)}.card:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.top{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:4px}
.id{font:600 .78rem "JetBrains Mono",ui-monospace,monospace;color:var(--muted)}
.ver{font:600 .72rem "JetBrains Mono",ui-monospace,monospace;color:var(--muted);border:1px solid var(--line);border-radius:999px;padding:1px 8px}
.navc.newrfc{background:var(--accent)!important;border-color:var(--accent)!important;color:#052e16!important;font-weight:600}
.badge{font-weight:600;font-size:.7rem;text-transform:uppercase;letter-spacing:.05em;border-radius:999px;padding:2px 10px;border:1px solid var(--line)}
[data-st=draft]{color:var(--muted)}[data-st=in-review]{background:var(--accent-soft);color:var(--accent-ink);border-color:transparent}
[data-st=approved]{background:#dff3e4;color:#17692f;border-color:transparent}[data-st=implemented]{background:#dbeafe;color:#1d4ed8;border-color:transparent}
[data-st=rejected]{background:#fde2e2;color:#a61b1b;border-color:transparent}[data-st=superseded]{color:var(--muted);text-decoration:line-through}
@media (prefers-color-scheme:dark){[data-st=approved]{background:#16341f;color:#7ddc97}[data-st=implemented]{background:#172a4d;color:#8ab4ff}[data-st=rejected]{background:#3d1818;color:#ff9a9a}}
.card h2{font:700 1.15rem/1.3 "Schibsted Grotesk",system-ui,sans-serif;margin:0 0 4px}.card p{margin:0 0 8px;color:var(--muted);font-size:.93rem}
.meta{display:flex;gap:6px 18px;flex-wrap:wrap;font-size:.8rem;color:var(--muted)}
[data-l]{display:none}html[data-lang=pt] [data-l=pt],html[data-lang=en] [data-l=en],html[data-lang=zh] [data-l=zh]{display:inline}
html[data-lang=pt] .card p [data-l=pt],html[data-lang=en] .card p [data-l=en],html[data-lang=zh] .card p [data-l=zh]{display:inline}
.empty{color:var(--muted)}
.hright{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.navc{display:inline-flex;align-items:center;gap:6px;font-weight:600;font-size:.82rem;color:var(--ink);text-decoration:none;border:1px solid var(--line);background:var(--surface);border-radius:999px;padding:5px 12px}
.navc:hover{border-color:var(--accent);color:var(--accent-ink)}
.ccount,.cc b{background:var(--accent-soft);color:var(--accent-ink);border-radius:999px;padding:0 7px;font-weight:600}
.cnewb,.cc .n{background:#c2410c;color:#fff;border-radius:999px;padding:0 7px;font-weight:700;font-size:.68rem;text-transform:uppercase;letter-spacing:.03em}
.cc{display:inline-flex;gap:6px;align-items:center}.cc .o{color:#b3540f;font-weight:600}
[hidden]{display:none!important}
"""

INDEX_JS = """
(function(){var L=["pt","en","zh"];function g(){try{var s=localStorage.getItem("phiz-rfc-lang");if(L.indexOf(s)>-1)return s}catch(e){}var n=(navigator.language||"pt").slice(0,2);return L.indexOf(n)>-1?n:"pt"}
function set(l){document.documentElement.dataset.lang=l;document.documentElement.lang={pt:"pt-BR",en:"en",zh:"zh-CN"}[l];try{localStorage.setItem("phiz-rfc-lang",l)}catch(e){}
document.querySelectorAll("[data-set-lang]").forEach(function(b){b.setAttribute("aria-pressed",String(b.dataset.setLang===l))})}
document.querySelectorAll("[data-set-lang]").forEach(function(b){b.onclick=function(){set(b.dataset.setLang)}});set(g());
var fl=document.querySelector(".filters");
if(fl)fl.addEventListener("click",function(e){var b=e.target.closest("[data-filter]");if(!b)return;
fl.querySelectorAll("[data-filter]").forEach(function(x){x.setAttribute("aria-pressed",String(x===b))});
document.querySelectorAll(".card-li").forEach(function(c){c.hidden=b.dataset.filter!=="all"&&c.dataset.status!==b.dataset.filter})})})();
"""


T_COMMENTS = {"pt": "Comentários", "en": "Comments", "zh": "评论"}
T_NEW = {"pt": "Nova RFC", "en": "New RFC", "zh": "新建 RFC"}

INDEX_COUNTS_JS = """
(function(){var c=window.PHIZ_CMT||{};if(!c.supabaseUrl||!c.supabaseKey)return;
var h={apikey:c.supabaseKey};if(/^eyJ/.test(c.supabaseKey))h.Authorization="Bearer "+c.supabaseKey;
var seen=0;try{seen=Date.parse(localStorage.getItem("phiz-rfc-seen:all")||"")||0}catch(e){}
var me="";try{me=localStorage.getItem("phiz-rfc-author")||""}catch(e){}
var W={pt:["comentários","sem resposta","novos"],en:["comments","unanswered","new"],zh:["条评论","条未回复","条新"]};
function lg(){return document.documentElement.dataset.lang||"pt"}
var data=null;
function paint(){if(!data)return;var w=W[lg()]||W.pt,tot=0,fresh=0;
document.querySelectorAll(".cc[data-rfc]").forEach(function(s){var id=s.dataset.rfc;
var rows=data.filter(function(x){return x.rfc_id===id});var tops=rows.filter(function(x){return!x.parent_id});
var withRep={};rows.forEach(function(x){if(x.parent_id)withRep[x.parent_id]=1});
var open=tops.filter(function(x){return!withRep[x.id]}).length;
var nw=rows.filter(function(x){return Date.parse(x.created_at)>seen&&x.author!==me}).length;
tot+=rows.length;fresh+=nw;
s.innerHTML="";if(!rows.length){s.hidden=true;return}s.hidden=false;
var b=document.createElement("b");b.textContent="💬 "+rows.length;s.appendChild(b);s.appendChild(document.createTextNode(w[0]));
if(open){var o=document.createElement("span");o.className="o";o.textContent="· "+open+" "+w[1];s.appendChild(o)}
if(nw){var n=document.createElement("span");n.className="n";n.textContent=nw+" "+w[2];s.appendChild(n)}});
var cc=document.querySelector(".ccount"),nb=document.querySelector(".cnewb");
if(cc){cc.textContent=String(tot);cc.hidden=!tot}if(nb){nb.textContent=fresh+" "+(W[lg()]||W.pt)[2];nb.hidden=!fresh}}
window.phizCountsRepaint=paint;
fetch(c.supabaseUrl.replace(/\\/+$/,"")+"/rest/v1/rfc_comments?select=id,rfc_id,parent_id,author,created_at&limit=5000",{headers:h})
.then(function(r){return r.ok?r.json():[]}).then(function(d){var tops={};d.forEach(function(x){if(!x.parent_id)tops[x.id]=1});
data=d.filter(function(x){return!x.parent_id||tops[x.parent_id]});paint()}).catch(function(){});
new MutationObserver(paint).observe(document.documentElement,{attributes:true,attributeFilter:["data-lang"]})})();
"""

SECTION_RE = re.compile(r'<h2 id="(pt|en|zh)-([a-z0-9-]+)"[^>]*>(.*?)</h2>', re.S)


def sections_of(d, meta):
    """{section key: {pt, en, zh}} titles from the RFC page, used by the comments page."""
    out = {}
    for lg, key, inner in SECTION_RE.findall(page_text(d, meta)):
        num = re.search(r'<span class="n">(.*?)</span>', inner)
        text = re.sub(r"<[^>]+>", "", re.sub(r'<span class="n">.*?</span>', "", inner))
        text = html.unescape(re.sub(r"\s+", " ", text)).strip()
        out.setdefault(key, {})[lg] = (f"{num.group(1)} · " if num else "") + text
    return out


COMMENTS_CSS = """
.cbar{display:grid;gap:10px;margin-bottom:10px}.cbar .filters{margin:0}
.filters button b{font-weight:700;margin-left:2px}
.filters .st-open[aria-pressed=true]{background:#b3540f;border-color:#b3540f;color:#fff}
.filters .st-new[aria-pressed=true]{background:#c2410c;border-color:#c2410c;color:#fff}
.csearch{width:100%;max-width:420px;font-weight:400;font-size:.9rem;color:var(--ink);background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:8px 12px}
.csearch:focus{outline:2px solid var(--accent);outline-offset:0}
.csum{color:var(--muted);font-size:.86rem;margin:4px 0 16px}
.clist{display:grid;gap:12px;padding:0;margin:0 0 60px;list-style:none}
.ccard{border:1px solid var(--line);background:var(--surface);border-radius:14px;padding:14px 16px}
.ccard.is-new{border-left:4px solid #c2410c}
.ctop{display:flex;flex-wrap:wrap;align-items:center;gap:6px 10px}
.csec{font-weight:600;font-size:.9rem}
.cnew{font-weight:700;font-size:.66rem;text-transform:uppercase;color:#fff;background:#c2410c;border-radius:4px;padding:1px 6px}
.copen{font-weight:600;font-size:.72rem;color:#b3540f;border:1px solid currentColor;border-radius:999px;padding:0 8px}
.ctitle{margin:2px 0 8px;color:var(--muted);font-size:.82rem}
.citem{margin:6px 0}.cmeta{display:flex;flex-wrap:wrap;gap:4px 10px;align-items:baseline;font-size:.84rem}
.cmeta time{color:var(--muted)}.clang{font:600 .66rem "JetBrains Mono",ui-monospace,monospace;color:var(--muted);border:1px solid var(--line);border-radius:4px;padding:0 4px}
.cquote{margin:6px 0;padding:4px 10px;border-left:3px solid var(--accent);color:var(--muted);font-style:italic;font-size:.86rem;background:var(--accent-soft);border-radius:0 6px 6px 0;overflow-wrap:anywhere}
.cbody{margin:4px 0;white-space:pre-wrap;overflow-wrap:anywhere;font-size:.94rem}
.creps{margin:8px 0 0 14px;padding-left:12px;border-left:3px solid var(--accent)}
.crepn{margin:0;font-size:.78rem;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.05em}
.crep .cbody{font-size:.9rem}
.cgo{display:inline-block;margin-top:8px;font-weight:600;font-size:.86rem;color:var(--accent-ink)}
.back{color:var(--muted);text-decoration:none;font-size:.82rem;margin-left:6px}.back:hover{color:var(--accent-ink)}
.err{color:#b3261e}
.ctr{margin:2px 0 4px;font-size:.78rem;color:var(--muted)}.clink{background:none;border:0;padding:0;color:var(--accent-ink);font:inherit;font-weight:600;cursor:pointer}.clink:hover{text-decoration:underline}
"""


def build_comments(items):
    """dist/comments/index.html: every comment of every RFC, with filters (data loaded in the browser)."""
    meta = {"cfg": CFG.get("comments", {}),
            "rfcs": [{"id": m["id"], "title": m["title"], "sections": sections_of(d, m)} for d, m in items]}
    data = json.dumps(meta, ensure_ascii=False).replace("</", "<\\/")
    title = e(CFG["title"])
    lead = {"pt": "Todos os comentários das RFCs em um só lugar. Filtre por RFC, veja o que está sem resposta ou o que chegou desde sua última visita, e abra o comentário na RFC para responder.",
            "en": "Every RFC comment in one place. Filter by RFC, see what is unanswered or new since your last visit, and open a comment in its RFC to reply.",
            "zh": "所有 RFC 评论集中在一处。可按 RFC 筛选，查看未回复或自上次访问以来的新评论，并在 RFC 中打开评论进行回复。"}
    return f'''<!doctype html><html lang="pt-BR" data-lang="pt"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{spans_plain(T_COMMENTS)} · {title}</title><meta name="robots" content="noindex">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Schibsted+Grotesk:wght@700;800&family=IBM+Plex+Sans:wght@400;500;600&family=JetBrains+Mono:wght@600&display=swap">
<style>{INDEX_CSS}{COMMENTS_CSS}</style></head><body>
<header><div class="wrap"><div class="brand"><span class="logo" aria-hidden="true">P</span><span>PHIZCHAT</span><a class="back" href="../">← RFCs</a></div>
<div class="langs" role="group" aria-label="Language"><button type="button" data-set-lang="pt">PT-BR</button><button type="button" data-set-lang="en">EN-US</button><button type="button" data-set-lang="zh">中文</button></div></div></header>
<main class="wrap"><h1>{spans(T_COMMENTS)}</h1><p class="lead">{spans(lead)}</p><div id="cmt-root"></div></main>
<script>window.PHIZ_COMMENTS={data};{INDEX_JS}</script>
<script src="../assets/comments-page.js"></script></body></html>'''


def spans_plain(d):
    return e(d["pt"])


def build_index(items):
    items = sorted(items, key=lambda x: x[1]["id"], reverse=True)
    lis = []
    for d, m in items:
        st = m["status"]
        authors = ", ".join(rfc_md.person_name(a) for a in m.get("authors", [])) or "—"
        revs = ", ".join(rfc_md.person_name(r) for r in m.get("reviewers", [])) or "—"
        lis.append(f'''<li class="card-li" data-status="{st}" data-rfc="{e(m["id"])}"><a class="card" href="rfcs/{e(d.name)}/">
<div class="top"><span class="id">{e(m["id"])}</span><span class="ver">v{e(versions_of(d, m)[0])}</span><span class="badge" data-st="{st}">{spans(STATUS[st])}</span></div>
<h2>{spans(m["title"])}</h2><p>{spans(m["summary"])}</p>
<div class="meta"><span>{e(authors)}</span><span>Reviewers: {e(revs)}</span><span>{e(m.get("updated", ""))}</span><span class="cc" data-rfc="{e(m["id"])}" hidden></span></div></a></li>''')
    used = sorted({m["status"] for _, m in items}, key=list(STATUS).index)
    fl = '<button type="button" data-filter="all" aria-pressed="true">' + spans({"pt": "Todas", "en": "All", "zh": "全部"}) + "</button>"
    fl += "".join(f'<button type="button" data-filter="{s}" aria-pressed="false">{spans(STATUS[s])}</button>' for s in used)
    title = e(CFG["title"])
    return f'''<!doctype html><html lang="pt-BR" data-lang="pt"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><meta name="robots" content="noindex">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Schibsted+Grotesk:wght@700;800&family=IBM+Plex+Sans:wght@400;500;600&family=JetBrains+Mono:wght@600&display=swap">
<style>{INDEX_CSS}</style></head><body>
<header><div class="wrap"><div class="brand"><span class="logo" aria-hidden="true">P</span><span>PHIZCHAT</span></div>
<div class="hright"><a class="navc newrfc" href="nova/">＋ {spans(T_NEW)}</a><a class="navc" href="comments/">💬 {spans(T_COMMENTS)}<span class="ccount" hidden></span><span class="cnewb" hidden></span></a>
<div class="langs" role="group" aria-label="Language"><button type="button" data-set-lang="pt">PT-BR</button><button type="button" data-set-lang="en">EN-US</button><button type="button" data-set-lang="zh">中文</button></div></div></div></header>
<main class="wrap"><h1>RFCs</h1>
<p class="lead">{spans({"pt": "Propostas técnicas da plataforma, com status e comentários por seção.", "en": "Platform technical proposals, with status and per-section comments.", "zh": "平台技术提案，含状态与分节评论。"})}</p>
<div class="filters" role="group">{fl}</div>
<ul class="list">{"".join(lis)}</ul></main><script>window.PHIZ_CMT={json.dumps(CFG.get("comments", {}))};window.PHIZ_SITE={json.dumps({"comments": CFG.get("comments", {})})};{INDEX_JS}{INDEX_COUNTS_JS}window.PHIZ_STATUS_INDEX=true;</script>
<script src="assets/status.js"></script>
<script type="module" src="assets/js/index-live.js"></script></body></html>'''


def live_config():
    return {"repo": CFG["repo"], "giscus": CFG["giscus"], "comments": CFG.get("comments", {})}


def build_viewer():
    """dist/rfc/index.html: the page that shows an RFC created on the site (/rfc/?id=PHZ-1001); assets/js/live.js fills it in."""
    shell = (ROOT / "templates" / "shell.html").read_text(encoding="utf-8")
    css = (ROOT / "templates" / "page.css").read_text(encoding="utf-8")
    loading = {"pt": "Carregando a RFC…", "en": "Loading the RFC…", "zh": "正在加载 RFC…"}
    page = re.sub(r"<title>.*?</title>", "<title>RFC</title>", shell, count=1, flags=re.S)
    page = (page.replace("RFC {{ID}}", "RFC").replace("/*CSS*/", css)
            .replace("<!--CONTENT-->", f'<p class="live-state">{spans(loading)}</p>').replace("<!--TOC-->", ""))
    page = rfc_md.wrap_fragment(page)
    page = page.replace('<span class="rfcno">', '<a class="back" href="../">← RFCs</a><span class="rfcno">', 1)
    page = page.replace("</title>", '</title>\n<link rel="stylesheet" href="../assets/rfc-site.css">', 1)
    inject = (f'<script>window.PHIZ_SITE={json.dumps(live_config())};</script>\n<script src="../assets/mermaid.min.js"></script>\n'
              '<script src="../assets/vendor/markdown-it.min.js"></script>\n<script src="../assets/vendor/markdown-it-container.min.js"></script>\n'
              '<script src="../assets/vendor/purify.min.js"></script>\n<script type="module" src="../assets/js/live.js"></script>\n</body>')
    return page.replace("</body>", inject, 1)


def build_new_rfc_page():
    """dist/nova/index.html: the page where anyone creates (or edits) an RFC from the single-file template."""
    def S(pt, en, zh):
        return spans({"pt": pt, "en": en, "zh": zh})
    return f'''<!doctype html><html lang="pt-BR" data-lang="pt"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(CFG["title"])} · Nova RFC</title><meta name="robots" content="noindex">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Schibsted+Grotesk:wght@700;800&family=IBM+Plex+Sans:wght@400;500;600&family=JetBrains+Mono:wght@600&display=swap">
<style>{INDEX_CSS}</style><link rel="stylesheet" href="../assets/nova.css"></head><body>
<header><div class="wrap"><div class="brand"><span class="logo" aria-hidden="true">P</span><span>PHIZCHAT</span></div>
<div class="hright"><a class="navc" href="../">← RFCs</a>
<div class="langs" role="group" aria-label="Language"><button type="button" data-set-lang="pt">PT-BR</button><button type="button" data-set-lang="en">EN-US</button><button type="button" data-set-lang="zh">中文</button></div></div></div></header>
<main class="wrap nova">
<h1 id="nova-title"><span class="only-new">{S("Nova RFC", "New RFC", "新建 RFC")}</span><span class="only-edit" hidden>{S("Nova versão de", "New version of", "新版本：")} <span id="edit-id"></span></span></h1>
<p class="lead">{S("Monte a sua RFC em quatro passos. Não precisa de conta nem de código: o arquivo que você enviar vira uma página do site, com comentários, status e histórico de versões.",
                    "Build your RFC in four steps. No account and no code needed: the file you upload becomes a page of the site, with comments, status and version history.",
                    "四步完成你的 RFC。无需账号，也无需代码：你上传的文件会变成站点上的一个页面，带有评论、状态和版本历史。")}</p>
<ol class="steps">
<li><h2>1. {S("Baixe o modelo", "Download the template", "下载模板")}</h2>
<p class="only-new">{S("É um arquivo só, com português, inglês e chinês. Cada ponto a preencher está marcado com TODO:.", "It is a single file with Portuguese, English and Chinese. Every spot to fill is marked TODO:.", "这是一个同时包含葡萄牙语、英语和中文的单一文件。每个待填写处都标有 TODO:。")}</p>
<p class="only-edit" hidden>{S("O arquivo da versão atual já está abaixo, no passo 3. Você também pode baixá-lo para editar no seu computador.", "The current version's file is already in step 3. You can also download it to edit on your computer.", "当前版本的文件已在第 3 步中。你也可以下载后在自己的电脑上编辑。")}</p>
<p><a class="btn" id="dl-template" href="../assets/templates/RFC.md" download="RFC.md">{S("Baixar o modelo (RFC.md)", "Download the template (RFC.md)", "下载模板 (RFC.md)")}</a>
<a class="btn" id="dl-current" href="#" download="RFC.md" hidden>{S("Baixar a versão atual", "Download the current version", "下载当前版本")}</a></p></li>
<li><h2>2. {S("Peça a uma IA para preencher", "Ask an AI to fill it in", "请 AI 帮忙填写")}</h2>
<p>{S("Abra a IA de sua preferência (Claude, ChatGPT…), cole o texto abaixo, anexe o modelo e os seus documentos. Com o Claude Code, a skill phiz-rfc faz isso direto no repositório.",
      "Open the AI you prefer (Claude, ChatGPT…), paste the text below and attach the template and your documents. With Claude Code, the phiz-rfc skill does this in the repository.",
      "打开你喜欢的 AI（Claude、ChatGPT 等），粘贴下面的文字，并附上模板和你的文档。使用 Claude Code 时，phiz-rfc skill 可直接在仓库中完成。")}</p>
<textarea id="prompt" rows="8" readonly aria-label="Prompt"></textarea>
<p><button type="button" class="btn" id="copy-prompt">{S("Copiar o texto", "Copy the text", "复制文字")}</button> <span id="copied" class="note" aria-live="polite"></span></p></li>
<li><h2>3. {S("Envie o arquivo preenchido", "Upload the filled file", "上传填写好的文件")}</h2>
<p><label class="btn" for="file">{S("Escolher arquivo (.md)", "Choose a file (.md)", "选择文件 (.md)")}</label><input type="file" id="file" accept=".md,.markdown,.txt,text/markdown,text/plain" hidden>
 <span class="note">{S("ou cole o conteúdo abaixo", "or paste the content below", "或在下方粘贴内容")}</span></p>
<textarea id="text" rows="10" spellcheck="false" aria-label="RFC.md"></textarea>
<div id="result" aria-live="polite"></div>
<p id="preview-bar" hidden><button type="button" class="btn" id="preview-toggle">{S("Ver prévia", "Preview", "预览")}</button>
<span class="langs" role="group" id="preview-langs" hidden><button type="button" data-pl="pt" aria-pressed="true">PT-BR</button><button type="button" data-pl="en" aria-pressed="false">EN-US</button><button type="button" data-pl="zh" aria-pressed="false">中文</button></span></p>
<iframe id="preview" title="Preview" sandbox="allow-scripts" hidden></iframe></li>
<li><h2>4. {S("Quem escreveu", "Who wrote it", "作者")}</h2>
<div class="fields">
<label><span>{S("Seu nome", "Your name", "你的名字")} <span class="req">*</span></span><input id="by" maxlength="60" autocomplete="name"></label>
<label class="only-edit" hidden>{S("Autores (um por linha)", "Authors (one per line)", "作者（每行一位）")}<textarea id="authors" rows="2"></textarea></label>
<label>{S("Colaboradores (um por linha ou separados por vírgula)", "Collaborators (one per line or comma separated)", "协作者（每行一位或用逗号分隔）")}<textarea id="collabs" rows="2"></textarea></label>
<label class="only-edit" hidden>{S("O que mudou (opcional)", "What changed (optional)", "改动说明（可选）")}<input id="note" maxlength="300"></label>
</div>
<p class="note">{S("Ao publicar, a RFC aparece no índice como Rascunho. Qualquer pessoa com o link pode ler, comentar e enviar novas versões; o histórico fica guardado e nada é sobrescrito.",
                   "When you publish, the RFC shows in the index as a Draft. Anyone with the link can read it, comment and upload new versions; the history is kept and nothing is overwritten.",
                   "发布后，RFC 会以草稿状态出现在索引中。任何持有链接的人都可以阅读、评论并上传新版本；历史会被保留，不会覆盖任何内容。")}</p>
<p><button type="button" class="btn primary" id="publish" disabled><span class="only-new">{S("Publicar RFC", "Publish RFC", "发布 RFC")}</span><span class="only-edit" hidden>{S("Publicar nova versão", "Publish new version", "发布新版本")}</span></button>
<span id="publish-note" class="note" aria-live="polite"></span></p></li>
</ol></main>
<script>window.PHIZ_SITE={json.dumps(live_config())};</script>
<script src="../assets/vendor/markdown-it.min.js"></script><script src="../assets/vendor/markdown-it-container.min.js"></script><script src="../assets/vendor/purify.min.js"></script>
<script type="module" src="../assets/js/nova.js"></script></body></html>'''


def build_live_pages():
    shutil.copytree(ROOT / "templates" / "bundle", DIST / "assets" / "templates")
    shutil.copy(ROOT / "templates" / "page.css", DIST / "assets" / "page.css")     # the preview frame of the new-RFC page
    (DIST / "rfc").mkdir()
    (DIST / "rfc" / "index.html").write_text(build_viewer(), encoding="utf-8")
    (DIST / "nova").mkdir()
    (DIST / "nova" / "index.html").write_text(build_new_rfc_page(), encoding="utf-8")


def main():
    if DIST.exists():
        shutil.rmtree(DIST)
    shutil.copytree(ROOT / "assets", DIST / "assets")
    (DIST / ".nojekyll").write_text("")
    items = load()
    for d, m in items:
        build_rfc(d, m)
    (DIST / "index.html").write_text(build_index(items), encoding="utf-8")
    build_live_pages()
    (DIST / "comments").mkdir()
    (DIST / "comments" / "index.html").write_text(build_comments(items), encoding="utf-8")
    print(f"built {len(items)} RFC(s) -> {DIST}")


main()
