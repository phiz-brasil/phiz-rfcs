#!/usr/bin/env python3
"""Imports the RFCs of rfcs/ into the database, so the site shows only what is stored there.

  SUPABASE_SERVICE_KEY=… .venv/bin/python tools/import_rfcs.py            import (or update) every RFC of rfcs/
  .venv/bin/python tools/import_rfcs.py --dry-run [--out /tmp/bundles]    convert and check only; --out writes the files
  .venv/bin/python tools/import_rfcs.py --only PHZ-0002                    one RFC

What it does for each rfcs/<ID>/ (the current version, written in the Markdown of docs/spec/rfc-format.md):
  - turns it into the single file of docs/spec/rfc-bundle.md: the three languages in one file, with the raw HTML of the repository
    format replaced by the Markdown of the site (::: gallery, ::: screens, ::: legend, ::: caption, [text]{eq});
  - turns the images it shows into attachments of the RFC (names like pt-whatsapp-b01-architecture.png: one file per language);
  - inserts it in rfc_revisions with its own revision number (1.7 is revision 8), so the next version made on the site is 1.8;
  - marks the id as a site RFC (the page edits those), and records the status of rfc.json when the log has none.
Older versions archived as HTML pages are not imported: the build keeps them as pages (dist/rfcs/<ID>/v<version>.html) and lists
them in the history of the RFC (dist/archive.json). The service key bypasses the row security: keep it out of the repository.
"""
import argparse
import base64
import hashlib
import html
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rfc_md  # noqa: E402
from rfc_md import LANGS  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CFG = json.loads((ROOT / "site.config.json").read_text(encoding="utf-8"))
SITE_URL = "https://{}.github.io/{}/".format(*CFG["repo"].split("/"))
MAX_IMAGE = 1048576
MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
MAGIC = {"image/png": lambda b: b[:8] == b"\x89PNG\r\n\x1a\n", "image/jpeg": lambda b: b[:3] == b"\xff\xd8\xff",
         "image/webp": lambda b: b[:4] == b"RIFF" and b[8:12] == b"WEBP"}
OPENAPI_TEXT = {      # the section {#openapi} of the RFC: the interactive reference lives on its own page (the build makes it)
    "pt": ("Referência OpenAPI", "A especificação OpenAPI 3.1 cobre todos os endpoints e webhooks desta RFC, com descrições neste idioma. [Abrir a referência interativa]({ref}) (o botão “Try it out” fica desligado porque a API ainda não existe) ou [baixar o YAML]({yaml}) para levar ao Apifox, Postman ou a um gerador de SDK."),
    "en": ("OpenAPI reference", "The OpenAPI 3.1 specification covers every endpoint and webhook in this RFC, with descriptions in this language. [Open the interactive reference]({ref}) (“Try it out” is turned off because the API does not exist yet) or [download the YAML]({yaml}) to take it into Apifox, Postman or an SDK generator."),
    "zh": ("OpenAPI 参考", "OpenAPI 3.1 规范涵盖本 RFC 中的所有端点和 Webhook，描述为当前语言。[打开交互式参考]({ref})（“Try it out”已关闭，因为该 API 尚不存在），或[下载 YAML]({yaml})并导入 Apifox、Postman 或 SDK 生成器。")}


class ImportError_(Exception):
    pass


# ------------------------------------------------------------------------------------------------ HTML → Markdown

def _escape_alt(text):
    return re.sub(r"\s+", " ", html.unescape(text)).replace("[", "\\[").replace("]", "\\]").strip()


def inline(fragment):
    """Inline HTML of the repository format → the Markdown of the site."""
    s = fragment
    s = re.sub(r"<code(?: class=\"p\")?>(.*?)</code>", lambda m: "`" + html.unescape(m.group(1)) + "`", s, flags=re.S)
    s = re.sub(r"<(b|strong)>(.*?)</\1>", r"**\2**", s, flags=re.S)
    s = re.sub(r"<(em|i)>(.*?)</\1>", r"*\2*", s, flags=re.S)
    s = re.sub(r'<span class="st (eq|ch|gap|new)">(.*?)</span>', r"[\2]{\1}", s, flags=re.S)
    s = re.sub(r'<span class="(yes|no|part)">(.*?)</span>', r"[\2]{\1}", s, flags=re.S)
    return re.sub(r"\s*\n\s*", " ", s).strip()


class Assets:
    """The images an RFC shows, named after their path and language so the same RFC can show a different file in each language."""

    def __init__(self, folder):
        self.folder, self.files, self.by_name = Path(folder), {}, {}

    def name_for(self, src):
        path = Path(src)
        if path.suffix.lower() not in MIME:
            raise ImportError_(f"image {src}: only PNG, JPEG and WebP can be attached")
        parts = [p for p in path.with_suffix("").parts if p != "mocks"]
        name = re.sub(r"[^a-z0-9._-]+", "-", "-".join(parts).lower()).strip("-") + path.suffix.lower().replace("jpeg", "jpg")
        if len(name) > 60:
            stem, ext = name.rsplit(".", 1)
            name = f"{stem[:50].rstrip('-')}-{hashlib.sha1(src.encode()).hexdigest()[:5]}.{ext}"
        if self.by_name.setdefault(name, src) != src:
            raise ImportError_(f"images {self.by_name[name]} and {src} would get the same name {name}")
        file = self.folder / src
        if not file.exists():
            raise ImportError_(f"image {src} does not exist")
        self.files[name] = file
        return name

    def read(self, name):
        data = self.files[name].read_bytes()
        mime = MIME[self.files[name].suffix.lower()]
        if not 1 <= len(data) <= MAX_IMAGE:
            raise ImportError_(f"{self.files[name]}: {len(data)} bytes; the limit is {MAX_IMAGE}")
        if not MAGIC[mime](data):
            raise ImportError_(f"{self.files[name]} is not a real {mime}")
        return mime, data


def convert(text, assets):
    """The Markdown of a repository RFC, with raw HTML → the Markdown of the site. Raises ImportError_ when HTML is left over."""
    keep = []

    def protect(m):
        keep.append(m.group(0))
        return f"\x00{len(keep) - 1}\x00"
    s = re.sub(r"^(`{3,}|~{3,}).*?^\1[ \t]*$", protect, text, flags=re.S | re.M)       # fenced code stays as it is
    s = re.sub(r"``[^`\n]+``|`[^`\n]+`", protect, s)                                 # and so do code spans

    def gallery(m):
        phones = " phones" if m.group(1) else ""
        items = []
        for sm in re.finditer(r'<div class="shot">\s*(?:<a [^>]*>)?\s*<img src="([^"]+)" alt="([^"]*)"[^>]*>\s*(?:</a>)?\s*(?:<p class="cap">(.*?)</p>)?\s*</div>', m.group(2), re.S):
            cap = inline(sm.group(3) or "")
            items.append(f"- ![{_escape_alt(sm.group(2))}](asset:{assets.name_for(sm.group(1))})" + (f" {cap}" if cap else ""))
        if not items or m.group(2).count('<div class="shot">') != len(items):
            raise ImportError_("a gallery has a shape the converter does not know:\n" + m.group(0)[:300])
        return f"::: gallery{phones}\n" + "\n".join(items) + "\n:::"
    s = re.sub(r'<div class="shots( phones)?">\s*(.*?)\n</div>', gallery, s, flags=re.S)

    def screens(m):
        cards = []
        for cm in re.finditer(r'<div class="screen"><h5>(.*?)</h5>(?:<span class="path">(.*?)</span>)?<ul>(.*?)</ul></div>', m.group(1), re.S):
            lis = [inline(x) for x in re.findall(r"<li>(.*?)</li>", cm.group(3), re.S)]
            head = inline(cm.group(1)) + (f" | {inline(cm.group(2))}" if cm.group(2) else "")
            cards.append(f"##### {head}\n\n" + "\n".join(f"- {x}" for x in lis))
        if not cards or m.group(1).count('<div class="screen">') != len(cards):
            raise ImportError_("a screens block has a shape the converter does not know:\n" + m.group(0)[:300])
        return "::: screens\n" + "\n\n".join(cards) + "\n:::"
    s = re.sub(r'<div class="screens">\s*(.*?)\n</div>', screens, s, flags=re.S)

    def endpoints(m):
        rows = []
        for em in re.finditer(r'<div class="ep"><span class="m m-(\w+)">(\w+)</span><code class="p">(.*?)</code><span class="d">(.*?)</span></div>', m.group(1), re.S):
            rows.append(f"- {em.group(2)} `{html.unescape(em.group(3))}` — {inline(em.group(4))}")
        if not rows or m.group(1).count('<div class="ep">') != len(rows):
            raise ImportError_("an endpoints block has a shape the converter does not know:\n" + m.group(0)[:300])
        return "::: endpoints\n" + "\n".join(rows) + "\n:::"
    s = re.sub(r'<div class="eps-wrap">\s*<div class="eps">(.*?)</div></div>', endpoints, s, flags=re.S)

    def legend(m):
        rows = []
        for lm in re.finditer(r"<span>(.*?)</span>(?=<span>|$)", m.group(1), re.S):
            rows.append("- " + inline(lm.group(1)))
        return "::: legend\n" + "\n".join(rows) + "\n:::"
    s = re.sub(r'<div class="legend">(.*?)</div>', legend, s, flags=re.S)

    s = re.sub(r'^<p class="cap">(.*?)</p>[ \t]*$', lambda m: "::: caption\n" + inline(m.group(1)) + "\n:::", s, flags=re.S | re.M)
    s = _inline_everywhere(s)
    left = sorted(set(re.findall(r"</?[a-zA-Z][^>]*>", re.sub(r"<br\s*/?>", "", re.sub(r"<!--.*?-->", "", s, flags=re.S)))))
    left = [t for t in left if not re.fullmatch(r"<(https?://|mailto:)[^>]*>", t)]
    if left:
        raise ImportError_("HTML left after the conversion: " + ", ".join(left[:12]))
    return re.sub(r"\x00(\d+)\x00", lambda m: keep[int(m.group(1))], s)


def _inline_everywhere(s):
    """The inline tags still in running text and table cells (a line at a time, so block structure is untouched)."""
    out = []
    for line in s.split("\n"):
        out.append(inline(line) if "<" in line and not line.startswith(":::") else line)
    return "\n".join(out)


# ------------------------------------------------------------------------------------------------ revisions

def person(p, lang="pt"):
    if isinstance(p, dict):
        return p.get(lang) or p.get("name") or next(iter(p.values()))
    return str(p)


def reviewer_line(r):
    return f"{r['name']} ({r['country']})" if isinstance(r, dict) and r.get("country") else person(r)


def short(text, n=300):
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= n:
        return text
    cut = text[:n - 1]
    return (cut[:cut.rfind(" ")] if " " in cut[n // 2:] else cut).rstrip(" ,;:") + "…"


def version_key(v):
    return tuple(int(x) for x in v.split("."))


def build_bundle(folder, meta, assets, rfc_dir):
    head = ["---", *[f"title_{l}: {meta['title'][l]}" for l in LANGS], *[f"summary_{l}: {meta['summary'][l]}" for l in LANGS],
            f"systems: {', '.join(meta.get('systems') or [])}"]
    if meta.get("reviewers"):
        head.append("reviewers: " + ", ".join(reviewer_line(r) for r in meta["reviewers"]))
    if meta.get("created"):
        head.append(f"created: {meta['created']}")
    head += ["---", ""]
    has_api = (Path(rfc_dir) / "openapi_gen.py").exists()
    parts = []
    for lang in LANGS:
        body = convert((Path(folder) / f"rfc.{lang}.md").read_text(encoding="utf-8"), assets).strip()
        if has_api:
            title, line = OPENAPI_TEXT[lang]
            base = f"{SITE_URL}rfcs/{meta['id']}/"
            para = line.format(ref=f"{base}openapi/", yaml=f"{base}openapi.{lang}.yaml")
            body, n = re.subn(r"(^## [^\n]*\{#openapi\}[ \t]*\n\n)[^\n]+", lambda m: m.group(1) + para, body, flags=re.M)
            if not n:
                body += f"\n\n## {title} {{#openapi}}\n\n{para}"
        parts.append(f"<!-- lang:{lang} -->\n\n{body}\n")
    return "\n".join(head) + "\n".join(parts)


def revisions_of(rfc_dir):
    """[{rev, version, meta, bundle, authors, collaborators, edited_by, note, created_at, assets}] of the versions written in Markdown."""
    rfc_dir = Path(rfc_dir)
    meta = json.loads((rfc_dir / "rfc.json").read_text(encoding="utf-8"))
    cur = str(meta["version"])
    out = []
    for ent in sorted(meta.get("changelog") or [], key=lambda e: version_key(str(e["version"]))):
        v = str(ent["version"])
        folder = rfc_dir if v == cur else rfc_dir / "versions" / v
        if not rfc_md.is_markdown_rfc(folder):
            continue                                # an HTML page: the build keeps it as a page
        m = meta if v == cur else json.loads((folder / "rfc.json").read_text(encoding="utf-8"))
        major, minor = (int(x) for x in v.split("."))
        if major != 1:
            raise ImportError_(f"{rfc_dir.name} v{v}: the site numbers versions 1.0, 1.1, 1.2…")
        assets = Assets(rfc_dir)
        bundle = build_bundle(folder, m, assets, rfc_dir)
        authors = [person(a) for a in m.get("authors") or []] or ["—"]
        out.append({"rev": minor + 1, "version": v, "bundle": bundle, "assets": assets,
                    "meta": {"title": m["title"], "summary": m["summary"], "systems": m.get("systems") or [],
                             **({"reviewers": [r if isinstance(r, dict) else {"name": r} for r in m["reviewers"]]} if m.get("reviewers") else {}),
                             **({"created": m["created"]} if m.get("created") else {})},
                    "authors": authors, "collaborators": [person(c) for c in m.get("collaborators") or []],
                    "edited_by": authors[0][:60], "note": short(person(ent.get("note") or {}, "pt") if ent.get("note") else ""),
                    "created_at": f"{ent.get('date') or m.get('created') or '2026-01-01'}T12:00:00Z", "status": m.get("status", "draft")})
    return out


def rfc_dirs(only=None):
    return [d for d in sorted((ROOT / "rfcs").iterdir()) if d.is_dir() and not d.name.startswith("_") and (not only or d.name == only)]


# ------------------------------------------------------------------------------------------------ the database

class Api:
    def __init__(self, url, key):
        self.base = url.rstrip("/") + "/rest/v1/"
        self.headers = {"apikey": key, "Authorization": "Bearer " + key, "Content-Type": "application/json"}

    def call(self, method, path, body=None, prefer=None):
        headers = dict(self.headers, **({"Prefer": prefer} if prefer else {}))
        req = urllib.request.Request(self.base + path, method=method, headers=headers, data=None if body is None else json.dumps(body).encode())
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                raw = r.read()
        except urllib.error.HTTPError as e:
            raise SystemExit(f"{method} {path}: HTTP {e.code} {e.read().decode()[:300]}")
        return json.loads(raw) if raw else None


def push(api, rfc_id, rev):
    ids = api.call("GET", f"rfc_ids?select=rfc_id,source&rfc_id=eq.{rfc_id}")
    if not ids:
        api.call("POST", "rfc_ids", {"rfc_id": rfc_id, "source": "site"}, "return=minimal")
    elif ids[0]["source"] != "site":
        api.call("PATCH", f"rfc_ids?rfc_id=eq.{rfc_id}", {"source": "site"}, "return=minimal")
    api.call("POST", "rfc_revisions?on_conflict=rfc_id,rev",
             {"rfc_id": rfc_id, "rev": rev["rev"], "version": rev["version"], "meta": rev["meta"], "bundle": rev["bundle"],
              "authors": rev["authors"], "collaborators": rev["collaborators"], "edited_by": rev["edited_by"],
              "note": rev["note"] or None, "created_at": rev["created_at"]},
             "resolution=ignore-duplicates,return=minimal")
    for name in sorted(rev["assets"].files):
        mime, data = rev["assets"].read(name)
        api.call("POST", "rfc_assets?on_conflict=rfc_id,name,rev",
                 {"rfc_id": rfc_id, "name": name, "rev": rev["rev"], "mime": mime, "size": len(data),
                  "data": base64.b64encode(data).decode(), "uploaded_by": rev["edited_by"], "created_at": rev["created_at"]},
                 "resolution=ignore-duplicates,return=minimal")
    if not api.call("GET", f"rfc_status_log?select=id&rfc_id=eq.{rfc_id}&limit=1"):
        api.call("POST", "rfc_status_log", {"rfc_id": rfc_id, "status": rev["status"], "author": "importação"}, "return=minimal")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="convert and check, change nothing")
    ap.add_argument("--out", help="write the converted files here (with --dry-run)")
    ap.add_argument("--only", help="one RFC id")
    args = ap.parse_args()
    api = None
    if not args.dry_run:
        key = os.environ.get("SUPABASE_SERVICE_KEY")
        if not key:
            sys.exit("Set SUPABASE_SERVICE_KEY (Supabase → Project Settings → API → service_role), or use --dry-run.")
        api = Api(CFG["comments"]["supabaseUrl"], key)
    for d in rfc_dirs(args.only):
        try:
            revs = revisions_of(d)
        except ImportError_ as e:
            sys.exit(f"{d.name}: {e}")
        for rev in revs:
            size = sum(len(rev["assets"].read(n)[1]) for n in rev["assets"].files)
            print(f"{d.name} v{rev['version']} (revision {rev['rev']}): {len(rev['bundle']) // 1000} KB of text, {len(rev['assets'].files)} images, {size // 1024} KB of images")
            if args.out:
                out = Path(args.out) / d.name
                out.mkdir(parents=True, exist_ok=True)
                (out / f"v{rev['version']}.md").write_text(rev["bundle"], encoding="utf-8")
            if api:
                push(api, d.name, rev)
    print("dry run: nothing was sent." if args.dry_run else "done.")


if __name__ == "__main__":
    main()
