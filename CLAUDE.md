# How to work in this repository

Read `docs/spec/v2/README.md` (the plan and the decisions) and `docs/spec/v2/guardrail.md` (the rules below, and how they are enforced) before changing anything.

## The three rules (every request, no exceptions without a written reason)

1. **Spec first (SDD).** Before the code, write or update the spec in `docs/spec/` — what changes, the rules, how it is checked — and commit it **before** the
   code. Ask the owner only about decisions that are really theirs; write the rest into the spec as a decision with its date.
2. **Tests.** Every change that touches code (`apps/web/`, `assets/`, `supabase/`, `templates/`, `tools/`) adds at least one `def test_…` in `tests/` that fails
   without the change. Write the tests from the spec. Rules of the database are mirrored in `tests/fake_themes.py` (the fake Supabase), so a new SQL rule
   needs the same rule there and a test of it.
3. **No regression.** Before opening or updating a pull request, run **the whole suite**, not only the new tests, and the type check:

   ```bash
   PW_CHANNEL=chrome .venv/bin/python tools/run_tests.py                 # the whole suite in parallel (~1 min); same tests as the line below
   PW_CHANNEL=chrome .venv/bin/python -m unittest discover -s tests     # one by one (~3 min), or add a module/test name to run just that; CI uses Playwright's Chromium
   npm run typecheck -w apps/web                                        # from the repository root
   ```

   Never delete, skip or weaken a test to make it pass. If a behaviour was changed on purpose, change the test **and** say so in the spec and in the pull request.

## The checker

`python3 tools/guardrail.py --base origin/main` applies the rules to your branch (it runs in CI on every pull request, and a hook of `.claude/settings.json`
runs it before `git push` and `gh pr create`). When a rule truly does not apply (a typo, a dependency bump) the only way out is a line in a commit message or
in the pull request text:

```
Guardrail-Skip: <spec|tests|regression> — <reason, at least 10 characters>
```

Use it rarely and say why; never to avoid writing a test.

## Working conventions

- Pull requests go to `main`; commits end with the Co-Authored-By line given by the environment. The owner writes in Portuguese: answer in Portuguese.
- Database changes are numbered, idempotent files in `supabase/migrations/` (never edit one that was applied); `tests/test_sql.py` parses them. Merging a pull request applies its migrations
  (`.github/workflows/migrate.yml`, `docs/spec/v2/migrations.md`): never paste SQL in the Supabase editor. Deploying an Edge Function and merging are done only when the owner asks.
- Texts of the interface exist in three languages (pt-BR, en, zh-Hans): `apps/web/lib/i18n.ts`.
- The design tokens are at the top of `apps/web/app/themes/themes.css` (`docs/spec/v2/design.md`); do not hard-code colours elsewhere.
- Do not commit secrets. Only the publishable Supabase key is in the repository.
