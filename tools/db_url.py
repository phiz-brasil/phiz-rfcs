#!/usr/bin/env python3
"""Print the Postgres URL the migrations workflow connects with (docs/spec/v2/migrations.md): the session pooler of the project, which has IPv4.
Reads PROJECT_REF, POOLER_HOST and SUPABASE_DB_PASSWORD from the environment; the password is percent-encoded so any character works."""
import os
import sys
from urllib.parse import quote


def build(env=os.environ):
    missing = [k for k in ("PROJECT_REF", "POOLER_HOST", "SUPABASE_DB_PASSWORD") if not env.get(k)]
    if missing:
        raise SystemExit("missing: " + ", ".join(missing))
    return "postgresql://postgres.%s:%s@%s:5432/postgres" % (quote(env["PROJECT_REF"], safe=""), quote(env["SUPABASE_DB_PASSWORD"], safe=""), env["POOLER_HOST"])


if __name__ == "__main__":
    sys.stdout.write(build())
