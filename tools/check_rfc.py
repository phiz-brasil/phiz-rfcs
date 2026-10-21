#!/usr/bin/env python3
"""Checks Markdown RFCs against docs/spec/rfc-format.md (rules F01-F08).

  python3 tools/check_rfc.py              every Markdown RFC in rfcs/
  python3 tools/check_rfc.py PHZ-0003     only those

Prints one line per problem; exits 1 when there is at least one error (warnings do not fail).
Needs requirements.txt (markdown-it-py, mdit-py-plugins): .venv/bin/python tools/check_rfc.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rfc_md

ROOT = rfc_md.ROOT


def main(argv):
    rfcs = ROOT / "rfcs"
    if argv:
        folders = [rfcs / a for a in argv]
    else:
        folders = [d for d in sorted(rfcs.iterdir()) if d.is_dir() and not d.name.startswith("_") and rfc_md.is_markdown_rfc(d)]
    failed = 0
    for d in folders:
        if not d.is_dir():
            print(f"{d.name}: not found")
            failed += 1
            continue
        if not rfc_md.is_markdown_rfc(d):
            print(f"{d.name}: skipped (HTML RFC, checked by its own build_rfc.py)")
            continue
        try:
            errors, warnings = rfc_md.check(d)
        except rfc_md.RfcError as e:
            errors, warnings = [str(e)], []
        status = "ok" if not errors else f"{len(errors)} error{'s' if len(errors) != 1 else ''}"
        print(f"{d.name}: {status}" + (f", {len(warnings)} warning{'s' if len(warnings) != 1 else ''}" if warnings else ""))
        for m in errors:
            print(f"  ERROR {m}")
        for m in warnings:
            print(f"  WARN  {m}")
        failed += bool(errors)
    if not folders:
        print("no Markdown RFCs found")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
