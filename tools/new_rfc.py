#!/usr/bin/env python3
"""Creates a new trilingual RFC from sources/_template and builds it.

  python3 tools/new_rfc.py --pt "Título" --en "Title" --zh "标题" --short "Short title" --author "Gleison"

Creates sources/<ID>/ (content_pt/en/zh.html, code.json, shell.html, page.css, build_rfc.py)
and rfcs/<ID>/rfc.json, using the next free PHZ-NNNN id (or --id), then builds rfcs/<ID>/source.html.
"""
import argparse, datetime, json, re, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TPL = ROOT / "sources" / "_template"


def next_id():
    nums = [int(m.group(1)) for d in (ROOT / "rfcs").iterdir() for m in [re.fullmatch(r"PHZ-(\d{4})", d.name)] if m]
    return f"PHZ-{(max(nums) + 1 if nums else 1):04d}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pt", required=True, help="title in Portuguese")
    ap.add_argument("--en", required=True, help="title in English")
    ap.add_argument("--zh", required=True, help="title in Simplified Chinese")
    ap.add_argument("--short", help="short title for the browser tab (default: --en)")
    ap.add_argument("--author", required=True)
    ap.add_argument("--id", help="RFC id, e.g. PHZ-0007 (default: next free)")
    a = ap.parse_args()

    rid = a.id or next_id()
    if not re.fullmatch(r"PHZ-\d{4}", rid):
        sys.exit(f"invalid id {rid!r}; use PHZ-NNNN")
    src, out = ROOT / "sources" / rid, ROOT / "rfcs" / rid
    if src.exists() or out.exists():
        sys.exit(f"{rid} already exists")

    today = datetime.date.today()
    values = {"{{ID}}": rid, "{{TITLE_PT}}": a.pt, "{{TITLE_EN}}": a.en, "{{TITLE_ZH}}": a.zh,
              "{{SHORT_TITLE}}": a.short or a.en, "{{AUTHOR}}": a.author,
              "{{DATE_PT}}": today.strftime("%d/%m/%Y"), "{{DATE_ISO}}": today.isoformat()}
    shutil.copytree(TPL, src, ignore=shutil.ignore_patterns("__pycache__"))
    for f in src.iterdir():
        if f.suffix in (".html", ".py", ".json", ".css"):
            t = f.read_text(encoding="utf-8")
            for k, v in values.items():
                t = t.replace(k, v)
            f.write_text(t, encoding="utf-8")

    out.mkdir(parents=True)
    meta = {"id": rid, "title": {"pt": a.pt, "en": a.en, "zh": a.zh},
            "summary": {"pt": "Uma frase.", "en": "One sentence.", "zh": "一句话。"},
            "status": "draft", "authors": [a.author], "reviewers": [],
            "version": "1.0",
            "changelog": [{"version": "1.0", "date": today.isoformat(),
                           "note": {"pt": "Primeira versão.", "en": "First version.", "zh": "首个版本。"}}],
            "created": today.isoformat(), "updated": today.isoformat()}
    (out / "rfc.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    subprocess.run([sys.executable, "build_rfc.py"], cwd=src, check=True)
    print(f"created {rid}\n  edit:  sources/{rid}/content_pt.html (then _en, _zh) and code.json\n"
          f"  meta:  rfcs/{rid}/rfc.json (summary, reviewers)\n"
          f"  build: cd sources/{rid} && python3 build_rfc.py && cd ../.. && python3 tools/build.py")


if __name__ == "__main__":
    main()
