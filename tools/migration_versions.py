#!/usr/bin/env python3
"""Print the versions (the 14 digits of the file names in supabase/migrations/) up to and including --through, one per line.
Used by the `baseline` run of .github/workflows/migrate.yml (docs/spec/v2/migrations.md)."""
import argparse
import re
import sys
from pathlib import Path

MIGRATIONS = Path(__file__).resolve().parent.parent / "supabase" / "migrations"


def versions(directory=MIGRATIONS):
    out = []
    for f in sorted(Path(directory).glob("*.sql")):
        m = re.match(r"^(\d{14})_[a-z_]+\.sql$", f.name)
        if not m:
            raise SystemExit(f"{f.name}: not a valid migration name (YYYYMMDDHHMMSS_name.sql)")
        out.append(m.group(1))
    if len(set(out)) != len(out):
        raise SystemExit("two migrations share a version")
    return out


def through(limit, directory=MIGRATIONS):
    all_versions = versions(directory)
    if limit not in all_versions:
        raise SystemExit(f"{limit} is not the version of a migration file")
    return [v for v in all_versions if v <= limit]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--through", required=True)
    print("\n".join(through(ap.parse_args().through)))
