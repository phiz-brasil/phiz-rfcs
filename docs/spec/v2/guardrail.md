# Spec v2: guardrail (how every change is made)

Status: decided 2026-11-24 (request of the owner: *every request on this code base must come with tests, follow SDD and not break what already worked*).

## The three rules

Every change that touches **code** (`apps/web/`, `assets/`, `supabase/`, `templates/`, `tools/`, `site.config.json`) must, in the same pull request:

1. **Spec first (SDD).** Change or add a spec under `docs/spec/` (or the design notes in it) that says what the change does and how it will be checked. The
   spec commit comes before the code commit in the branch; the checker warns when the order is reversed. A bug fix names the rule it restores in the spec.
2. **Tests.** Add at least one test (`def test_…` in `tests/`) that fails without the change. The tests are written against the spec, not against the code.
3. **No regression.** The whole suite (`python -m unittest discover -s tests`, the compatibility suite of `docs/spec/v2/compatibility.md`) passes, the
   number of tests does not go down, and no test is skipped to make it pass. Removing or skipping a test needs an explicit reason (below).

Changes that touch only `docs/`, `tests/`, `.github/`, `.claude/` or `CLAUDE.md` are not code: rule 2 and 3 still apply to a change of tests (no test lost,
none skipped), rule 1 does not.

## How it is enforced (three layers)

| layer | what | where |
|---|---|---|
| the checker | `python3 tools/guardrail.py --base origin/main` compares the branch with its base and applies the three rules; exit code 1 and a list of what is missing | `tools/guardrail.py`, tested in `tests/test_guardrail.py` |
| CI | the job `guardrail` of `check.yml` runs the checker on every pull request (with the PR text, so a skip line is read); the existing jobs run the build, the type check and the whole suite | `.github/workflows/check.yml` |
| the assistant | `CLAUDE.md` tells Claude Code how to work (spec, tests, run the suite); a hook of `.claude/settings.json` runs the checker before `git push` and `gh pr create` and refuses when it fails | `CLAUDE.md`, `.claude/settings.json`, `.claude/hooks/guardrail.sh` |

To make CI binding, the jobs `guardrail`, `check` and `smoke-tests` must be *required* in the branch protection of `main` (a repository setting, not code).

## What the checker looks at

- the files of the branch against the merge base (`git diff --name-status <base>...HEAD`), sorted into code, tests, specs and other;
- rule 1: a file under `docs/spec/` changed; and, as a warning only, the first commit that touches the spec is not later than the first commit that touches code;
- rule 2: the diff of `tests/` has at least one added line `def test_`;
- rule 3: the tests removed (`def test_` lines removed) are not more than the tests added; no added `skip`, `skipTest`, `expectedFailure` or `@unittest.skipIf/Unless` in `tests/` — only real uses count (a decorator, or a `self.skipTest(` / `raise unittest.SkipTest` statement at the start of a line), not those words inside a string or a comment, and not `skipUnless(shutil.which(…))` / `skipUnless(pglast)`, which skip a test only where a tool is missing;
- the suite itself is not run by the checker (CI does it, and the hook leaves it to the assistant and to CI, which is where it is cheap).

## Skips (the only way out)

A rule can be skipped with a line in the pull request text or in any commit message of the branch, with a reason of at least ten characters:

```
Guardrail-Skip: spec — the change only renames a CSS class
Guardrail-Skip: tests — dependency bump, the suite covers it
Guardrail-Skip: regression — test X tested the old URL, replaced by Y (same behaviour)
```

A skip is visible in the history and in the pull request; a reviewer decides whether the reason is good enough. `Guardrail-Skip: all` is not accepted.

## Acceptance

- A branch that changes code and nothing else fails with the three rules listed.
- A branch with a spec change, a new test and no loss of tests passes; with only docs, or only tests that add tests, it passes.
- Removing a test, or adding a real skip, fails unless `Guardrail-Skip: regression — …` is present.
- The word `skip` inside a string or comment is not a skip; `@unittest.skip(...)` and `self.skipTest(...)` are.
- A skip line with a short reason, an unknown rule, or `all` is refused.
- The hook refuses `git push` and `gh pr create` when the checker fails and lets every other command through.
