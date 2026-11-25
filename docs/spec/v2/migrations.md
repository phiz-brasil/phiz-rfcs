# Migrations applied by the CI (no manual SQL)

Decision of the owner, 2026-11-25: stop pasting SQL in the Supabase editor. Asked for an ORM; decided on the **Supabase CLI in GitHub Actions** instead
(also 2026-11-25): the schema is RLS, `SECURITY DEFINER` functions and the `check_request` gate, which an ORM does not model, so it would still be raw SQL,
only in a new format. The numbered, idempotent files of `supabase/migrations/` stay exactly as they are.

## What changes

- A workflow `.github/workflows/migrate.yml` runs `supabase db push` on every push to `main` that touches `supabase/migrations/**`. The CLI keeps
  the list of what was applied in `supabase_migrations.schema_migrations` and applies only the files that are not there, in order, each in a transaction.
- `supabase/config.toml` (minimal, `project_id` only) so the CLI can link the project.
- A manual run (`workflow_dispatch`) with the input `baseline`: it marks every migration up to that version as **already applied** without running it.
  It is used once, because the 19 migrations up to `20261204000000` were applied by hand and the history table does not know them.
  `tools/migration_versions.py --through <version>` prints the versions to mark (the workflow does not compute them in shell).
- Runs are serialised (`concurrency`), never cancelled in the middle.

## Secrets (GitHub → Settings → Secrets and variables → Actions; the owner creates them, never in the repository)

| Secret | Where to read it |
|---|---|
| `SUPABASE_ACCESS_TOKEN` | Supabase → Account → Access Tokens → Generate new token |
| `SUPABASE_DB_PASSWORD` | Supabase → Project Settings → Database → Database password (reset if lost) |
| `SUPABASE_PROJECT_REF` | the id in the project URL: `zuwbjcwfqzucjmxrehad` |

## Rules for authors

1. A schema change is a new file `YYYYMMDDHHMMSS_name.sql` (name: lowercase letters and `_`); never edit one that was applied (unchanged rule).
2. Still idempotent (`if not exists`, `create or replace`, `drop policy if exists`), so a re-run is harmless.
3. Merging to `main` applies it. Nobody pastes it in the editor any more; a migration that fails stops the workflow (red run) and leaves
   the earlier ones applied (the failed one is rolled back).
4. Edge Functions are not part of this (deploying them stays as it is).

## How it is checked (`tests/test_migrate_workflow.py`)

- the workflow runs on push to `main` for `supabase/migrations/**` and on `workflow_dispatch` with `baseline`; uses the three secrets, none written in the file;
- it runs `supabase db push`, has a `concurrency` group without `cancel-in-progress`, and `permissions: contents: read`;
- `supabase/config.toml` has a `project_id`;
- `tools/migration_versions.py` lists the versions up to a limit (inclusive), in order, and refuses a limit that is not a version of a file;
- every migration name is a valid CLI version (14 digits, unique).
