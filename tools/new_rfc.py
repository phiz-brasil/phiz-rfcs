#!/usr/bin/env python3
"""Creates a new trilingual RFC from templates/rfc.

  python3 tools/new_rfc.py --pt "Título" --en "Title" --zh "标题" --author "Gleison"

Creates rfcs/<ID>/ (rfc.json, rfc.pt.md, rfc.en.md, rfc.zh.md) with the next free PHZ-NNNN id (or --id). The id comes from the
sequence in the database that RFCs created on the site use too (function reserve_rfc_id), so the two never collide; when the database
cannot be reached it falls back to the next id in the repository and says so.
Fill the three .md files (each pending spot is marked with TODO followed by a colon), then run
  python3 tools/check_rfc.py <ID>   and   python3 tools/build.py
Format and rules: docs/spec/rfc-format.md
"""
import argparse, datetime, json, re, shutil, sys, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TPL = ROOT / "templates" / "rfc"


def next_id():
    nums = [int(m.group(1)) for d in (ROOT / "rfcs").iterdir() for m in [re.fullmatch(r"PHZ-(\d{4})", d.name)] if m]
    return f"PHZ-{(max(nums) + 1 if nums else 1):04d}"


def reserve_id(author):
    """The next id of the shared sequence, reserved for the repository; None when the database cannot be reached."""
    cfg = json.loads((ROOT / "site.config.json").read_text(encoding="utf-8")).get("comments", {})
    if not (cfg.get("supabaseUrl") and cfg.get("supabaseKey")):
        return None
    headers = {"apikey": cfg["supabaseKey"], "Content-Type": "application/json"}
    if cfg["supabaseKey"].startswith("eyJ"):
        headers["Authorization"] = "Bearer " + cfg["supabaseKey"]
    req = urllib.request.Request(cfg["supabaseUrl"].rstrip("/") + "/rest/v1/rpc/reserve_rfc_id",
                                 data=json.dumps({"p_by": author[:60]}).encode(), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            rid = json.loads(r.read())
    except Exception:
        return None
    return rid if isinstance(rid, str) and re.fullmatch(r"PHZ-\d{4}", rid) else None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pt", required=True, help="title in Portuguese")
    ap.add_argument("--en", required=True, help="title in English")
    ap.add_argument("--zh", required=True, help="title in Simplified Chinese")
    ap.add_argument("--author", required=True)
    ap.add_argument("--id", help="RFC id, e.g. PHZ-0007 (default: next free)")
    a = ap.parse_args()

    rid = a.id
    if not rid:
        rid = reserve_id(a.author)
        if rid:
            print(f"{rid} reserved in the shared sequence")
        else:
            rid = next_id()
            print(f"warning: could not reserve an id in the database; using the next one in the repository ({rid}). It may collide with an RFC "
                  "created on the site: apply supabase/migrations/20261022000000_live_rfcs.sql, or pass --id", file=sys.stderr)
    if not re.fullmatch(r"PHZ-\d{4}", rid):
        sys.exit(f"invalid id {rid!r}; use PHZ-NNNN")
    out = ROOT / "rfcs" / rid
    if out.exists():
        sys.exit(f"{rid} already exists")

    values = {"{{ID}}": rid, "{{TITLE_PT}}": a.pt, "{{TITLE_EN}}": a.en, "{{TITLE_ZH}}": a.zh,
              "{{AUTHOR}}": a.author, "{{DATE_ISO}}": datetime.date.today().isoformat()}
    shutil.copytree(TPL, out)
    for f in out.iterdir():
        t = f.read_text(encoding="utf-8")
        for k, v in values.items():
            t = t.replace(k, v.replace("\\", "\\\\").replace('"', '\\"') if f.suffix == ".json" else v)
        f.write_text(t, encoding="utf-8")
    print(f"created rfcs/{rid}\n  fill: rfcs/{rid}/rfc.pt.md, then rfc.en.md and rfc.zh.md (same sections, paragraphs and diagrams)\n"
          f"  meta: rfcs/{rid}/rfc.json (summary, reviewers, systems)\n"
          f"  check: python3 tools/check_rfc.py {rid}   build: python3 tools/build.py")


if __name__ == "__main__":
    main()
