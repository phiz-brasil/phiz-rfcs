#!/usr/bin/env python3
"""Publishes an RFC written as a single file (templates/bundle/RFC.md, docs/spec/rfc-bundle.md) to the database: the same thing the
page /nova/ does, from the terminal. The RFC then lives at <site>/rfc/?id=PHZ-NNNN.

  .venv/bin/python tools/publish_rfc.py rfc.md --by "Gleison"                         a new RFC (the next free PHZ-NNNN)
  .venv/bin/python tools/publish_rfc.py rfc.md --by "Gleison" --id PHZ-0003 --note "O que mudou"    a new version of one
  .venv/bin/python tools/publish_rfc.py rfc.md --check                                only check it (nothing is sent)

Images: `![descrição](asset:nome.png)` in the text; put the files (PNG, JPEG or WebP, at most 1 MB each) in --images (default: the
folder of the file). On a new version, images the RFC already has do not need to be sent again.
The checks are those of the page (B01–B10): metadata, the three languages, same sections, paragraphs, diagrams and code blocks, no
TODO: markers, no raw HTML. The public key of site.config.json is enough: the database applies its own limits (5 new RFCs an hour).
"""
import argparse
import base64
import json
import re
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rfc_md  # noqa: E402
from rfc_md import LANGS  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CFG = json.loads((ROOT / "site.config.json").read_text(encoding="utf-8"))
SITE_URL = "https://{}.github.io/{}/".format(*CFG["repo"].split("/"))
MAX_BUNDLE = 600000
MAX_IMAGE = 1048576
MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
MAGIC = {"image/png": lambda b: b[:8] == b"\x89PNG\r\n\x1a\n", "image/jpeg": lambda b: b[:3] == b"\xff\xd8\xff",
         "image/webp": lambda b: b[:4] == b"RIFF" and b[8:12] == b"WEBP"}
MARK = re.compile(r"^[ \t]*<!--\s*lang:\s*(pt|en|zh)\s*-->[ \t]*$")
ASSET = re.compile(r'data-asset="([^"]+)"')


class PublishError(Exception):
    pass


def parse_bundle(text):
    """→ (meta, {lang: markdown}, errors); the same reading as assets/js/render/bundle.js."""
    errors = []
    src = text.lstrip("﻿").replace("\r\n", "\n").replace("\r", "\n")
    src = re.sub(r"^(?:\s*<!--.*?-->)*\s*", "", src, flags=re.S)
    m = re.match(r"^---\n(.*?)\n---[ \t]*(?:\n|$)", src, re.S)
    kv = {}
    if not m:
        errors.append("The file must start with the metadata block between two '---' lines.")
    else:
        for line in m.group(1).split("\n"):
            if not line.strip() or line.strip().startswith("#"):
                continue
            k = re.match(r"^([a-z_]+):[ \t]*(.*)$", line)
            if not k:
                errors.append(f"Metadata line not understood: {line.strip()[:60]}")
            else:
                kv[k.group(1)] = k.group(2).strip()
    meta = {"title": {}, "summary": {}, "systems": [s.strip() for s in kv.get("systems", "").split(",") if s.strip()]}
    for lang in LANGS:
        for key in ("title", "summary"):
            v = kv.get(f"{key}_{lang}")
            if not v:
                errors.append(f"Metadata is missing {key}_{lang}.")
            meta[key][lang] = v or ""
    reviewers = []
    for s in (x.strip() for x in kv.get("reviewers", "").split(",")):
        if s:
            rm = re.match(r"^(.*?)\s*\((BR|CN)\)$", s)
            reviewers.append({"name": rm.group(1), "country": rm.group(2)} if rm else {"name": s})
    if reviewers:
        meta["reviewers"] = reviewers
    if kv.get("created"):
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", kv["created"]):
            meta["created"] = kv["created"]
        else:
            errors.append("Metadata created must look like 2026-10-15.")
    md, cur, seen, preamble = {}, None, [], []
    for line in (src[m.end():] if m else src).split("\n"):
        mm = MARK.match(line)
        if mm:
            cur = mm.group(1)
            if cur in seen:
                errors.append(f"The language marker <!-- lang:{cur} --> appears more than once.")
            seen.append(cur)
            md[cur] = []
        elif cur:
            md[cur].append(line)
        else:
            preamble.append(line)
    if re.sub(r"<!--.*?-->", "", "\n".join(preamble), flags=re.S).strip():
        errors.append("There is text before the first language marker.")
    for lang in LANGS:
        if lang not in md:
            errors.append(f"Missing the section <!-- lang:{lang} -->.")
        else:
            md[lang] = "\n".join(md[lang]).strip() + "\n"
    return meta, md, errors


def raw_html(markdown):
    """The HTML tags in running text (the site shows submitted RFCs without raw HTML; <br> is the one exception)."""
    s = re.sub(r"^(`{3,}|~{3,}).*?^\1[ \t]*$", "", markdown, flags=re.S | re.M)
    s = re.sub(r"``[^`\n]+``|`[^`\n]+`|<!--.*?-->", "", s, flags=re.S)
    s = re.sub(r"<br\s*/?>", "", s)
    return sorted({t for t in re.findall(r"</?[a-zA-Z][^>]*>", s) if not re.fullmatch(r"<(https?://|mailto:)[^>]*>", t)})


def check_bundle(text):
    """→ (errors, warnings, meta, md, image names)."""
    errors, warnings = [], []
    if len(text) > MAX_BUNDLE:
        errors.append(f"The file is too large ({len(text) // 1000} KB; the limit is {MAX_BUNDLE // 1000} KB).")
    meta, md, parse_errors = parse_bundle(text)
    errors += parse_errors
    bodies = {}
    if all(lang in md for lang in LANGS):
        for lang in LANGS:
            hits = [i + 1 for i, line in enumerate(md[lang].split("\n")) if "TODO:" in line]
            if hits:
                errors.append(f"The {lang.upper()} section still has {len(hits)} TODO: marker(s) (first at line {hits[0]}).")
            tags = raw_html(md[lang])
            if tags:
                errors.append(f"{lang.upper()}: raw HTML is not allowed ({', '.join(tags[:5])}). Use the Markdown of docs/spec/rfc-bundle.md.")
            try:
                bodies[lang] = rfc_md.render_body(md[lang], lang)
            except rfc_md.RfcError as e:
                errors.append(f"{lang.upper()}: {e}")
    images = []
    if len(bodies) == 3:
        ids = {lang: bodies[lang][1] for lang in LANGS}
        for lang in ("en", "zh"):
            if ids[lang] != ids["pt"]:
                errors.append(f"Section ids differ between PT and {lang.upper()}: PT has {', '.join(ids['pt'])}; {lang.upper()} has {', '.join(ids[lang])}.")
        if ids["en"] == ids["pt"] == ids["zh"]:
            st = {lang: rfc_md.structure(bodies[lang][0]) for lang in LANGS}
            for k, sid in enumerate(ids["pt"]):
                n = [st[lang]["blocks"][k] for lang in LANGS]
                if len(set(n)) > 1:
                    errors.append(f'Section "{sid}" has a different number of paragraphs, list items, tables, diagrams or code blocks: '
                                  f"PT {n[0]} · EN {n[1]} · ZH {n[2]} (comments on a paragraph use these numbers).")
            d = [st[lang]["diagrams"] for lang in LANGS]
            if len(set(d)) > 1:
                errors.append(f"Different number of diagrams: PT {d[0]} · EN {d[1]} · ZH {d[2]}.")
            squash = lambda blocks: ["".join(c.split()) for c in blocks]
            for lang in ("en", "zh"):
                if squash(st["pt"]["code"]) != squash(st[lang]["code"]):
                    errors.append(f"Code blocks in {lang.upper()} are not identical to PT (samples are shared across languages; comments in English).")
        images = sorted({n for lang in LANGS for n in ASSET.findall(bodies[lang][0])})
    return errors, warnings, meta, md, images


def read_images(names, folder):
    """{name: (mime, bytes)} of the files `names` in `folder`; missing ones are returned apart."""
    found, missing = {}, []
    for name in names:
        file = Path(folder) / name
        if not file.is_file():
            missing.append(name)
            continue
        mime = MIME.get(file.suffix.lower())
        data = file.read_bytes()
        if not mime or not MAGIC[mime](data):
            raise PublishError(f"{file}: not a real PNG, JPEG or WebP file.")
        if not 1 <= len(data) <= MAX_IMAGE:
            raise PublishError(f"{file}: {len(data)} bytes; the limit is {MAX_IMAGE} (1 MB). Export it smaller.")
        found[name] = (mime, data)
    return found, missing


def rpc(function, body):
    cfg = CFG["comments"]
    headers = {"apikey": cfg["supabaseKey"], "Content-Type": "application/json"}
    if cfg["supabaseKey"].startswith("eyJ"):
        headers["Authorization"] = "Bearer " + cfg["supabaseKey"]
    req = urllib.request.Request(cfg["supabaseUrl"].rstrip("/") + f"/rest/v1/rpc/{function}", data=json.dumps(body).encode(), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read()
    except urllib.error.HTTPError as e:
        try:
            detail = json.loads(e.read()).get("message", "")
        except Exception:
            detail = ""
        if e.code == 429:
            raise PublishError("Too many publications from this connection; wait a while and try again.")
        raise PublishError(f"The database refused it ({e.code}): {detail}")
    except OSError as e:
        raise PublishError(f"Could not reach the database: {e}")
    return json.loads(raw) if raw else None


def names_of(text):
    return [s.strip() for s in re.split(r"[\n,]", text) if s.strip()]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", help="the single-file RFC")
    ap.add_argument("--by", help="your name, recorded with the publication (required to publish)")
    ap.add_argument("--id", help="PHZ-NNNN: publish a new version of this RFC instead of a new RFC")
    ap.add_argument("--note", help="what changed (new versions; up to 300 characters)")
    ap.add_argument("--authors", help="comma-separated; default: --by")
    ap.add_argument("--collaborators", default="", help="comma-separated")
    ap.add_argument("--images", help="folder with the image files (default: the folder of the file)")
    ap.add_argument("--check", action="store_true", help="only check, send nothing")
    a = ap.parse_args()
    path = Path(a.file)
    errors, warnings, meta, md, images = check_bundle(path.read_text(encoding="utf-8"))
    folder = Path(a.images) if a.images else path.resolve().parent
    try:
        found, missing = ({}, []) if errors else read_images(images, folder)
    except PublishError as e:
        sys.exit(f"Not published: {e}")
    for w in warnings:
        print("warning:", w)
    if errors:
        sys.exit("Not published:\n  " + "\n  ".join(errors))
    if missing and not a.id:
        sys.exit(f"Not published: the text uses images that are not in {folder}: {', '.join(missing)}")
    if missing:
        print(f"note: not in {folder}, the RFC must already have: {', '.join(missing)}")
    print(f"checked: {len(images)} image(s), {sum(len(md[l]) for l in LANGS) // 1000} KB of text")
    if a.check:
        return
    if not a.by or not a.by.strip():
        sys.exit("--by \"Your name\" is required to publish.")
    by = a.by.strip()[:60]
    token = str(uuid.uuid4())
    try:
        for name, (mime, data) in found.items():
            rpc("stage_rfc_asset", {"p_token": token, "p_name": name, "p_mime": mime, "p_data": base64.b64encode(data).decode(), "p_by": by})
        common = {"p_meta": meta, "p_bundle": path.read_text(encoding="utf-8"), "p_authors": names_of(a.authors or by), "p_collaborators": names_of(a.collaborators),
                  "p_by": by, "p_token": token if found else None}
        if a.id:
            res = rpc("add_rfc_revision", {"p_rfc_id": a.id.upper(), "p_note": a.note, **common})
        else:
            res = rpc("create_rfc", common)
    except PublishError as e:
        sys.exit(str(e))
    print(f"published {res['rfc_id']} version {res['version']}: {SITE_URL}rfc/?id={res['rfc_id']}")


if __name__ == "__main__":
    main()
