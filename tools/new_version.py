#!/usr/bin/env python3
"""Starts a new version of an RFC; the version that was last published is kept as a read-only archive.

  python3 tools/new_version.py PHZ-0001 --note-pt "O que mudou" --note-en "What changed" --note-zh "变更内容"
  python3 tools/new_version.py PHZ-0001 --major ...        # 1.2 -> 2.0 instead of 1.3
  python3 tools/new_version.py PHZ-0001 --set 2.0 ...      # explicit number

Run it BEFORE editing the RFC, with the last published version committed. It
  1. archives the RFC as it is in git HEAD (rfc.{pt,en,zh}.md and rfc.json) -> rfcs/<ID>/versions/<current>/
     (served at /rfcs/<ID>/v<current>.html, read-only, no new comments),
  2. bumps "version" in rfcs/<ID>/rfc.json and adds a changelog entry with the three notes.
Then edit rfcs/<ID>/rfc.*.md, check, rebuild and commit.
"""
import argparse, datetime, json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VER = re.compile(r"\d+\.\d+")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("id", help="RFC id, e.g. PHZ-0001")
    ap.add_argument("--note-pt", required=True)
    ap.add_argument("--note-en", required=True)
    ap.add_argument("--note-zh", required=True)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--major", action="store_true", help="bump the major number (default bumps the minor)")
    g.add_argument("--set", dest="explicit", metavar="X.Y", help="use this exact version number")
    a = ap.parse_args()

    rdir = ROOT / "rfcs" / a.id
    meta_path = rdir / "rfc.json"
    if not meta_path.exists():
        sys.exit(f"{a.id}: {meta_path.relative_to(ROOT)} not found")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    cur = str(meta.get("version", "1.0"))
    log = meta.get("changelog") or [{"version": cur, "date": meta.get("created", ""), "note": {"pt": "", "en": "", "zh": ""}}]

    if a.explicit:
        new = a.explicit
    else:
        major, minor = map(int, cur.split("."))
        new = f"{major + 1}.0" if a.major else f"{major}.{minor + 1}"
    if not VER.fullmatch(new):
        sys.exit(f"invalid version {new!r}; use MAJOR.MINOR, e.g. 2.0")
    if new in [str(x["version"]) for x in log]:
        sys.exit(f"{a.id} already has version {new}")

    names = ["rfc.pt.md", "rfc.en.md", "rfc.zh.md", "rfc.json"]
    folder = rdir / "versions" / cur
    if folder.exists() and any(folder.iterdir()):
        sys.exit(f"{folder.relative_to(ROOT)} already exists; v{cur} is already archived")
    folder.mkdir(parents=True, exist_ok=True)
    origin = "git HEAD"
    for name in names:
        r = subprocess.run(["git", "show", f"HEAD:rfcs/{a.id}/{name}"], cwd=ROOT, capture_output=True)
        if r.returncode == 0:
            data = r.stdout.decode("utf-8")
        else:
            data, origin = (rdir / name).read_text(encoding="utf-8"), "working tree (not committed yet)"
        (folder / name).write_text(data, encoding="utf-8")
    snap = folder

    for ent in log:                      # remember the status v<cur> had when it was frozen
        if str(ent["version"]) == cur:
            ent.setdefault("status", meta["status"])
    today = datetime.date.today().isoformat()
    log.insert(0, {"version": new, "date": today, "note": {"pt": a.note_pt, "en": a.note_en, "zh": a.note_zh}})
    meta.update({"version": new, "changelog": log, "updated": today})
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    nxt = (f"next: edit rfcs/{a.id}/rfc.pt.md, rfc.en.md and rfc.zh.md, then\n"
           f"  python3 tools/check_rfc.py {a.id} && python3 tools/build.py\n"
           f"  git add rfcs/{a.id} && git commit && git push")
    print(f"{a.id}: v{cur} archived from {origin} -> {snap.relative_to(ROOT)}/\n"
          f"{a.id}: now v{new} (changelog updated in rfcs/{a.id}/rfc.json)\n" + nxt)

if __name__ == "__main__":
    main()
