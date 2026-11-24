#!/usr/bin/env python3
"""The guardrail of docs/spec/v2/guardrail.md: a branch that changes code must also change a spec, add a test and lose no test.

  python3 tools/guardrail.py --base origin/main            # human report, exit 1 when a rule fails
  python3 tools/guardrail.py --base origin/main --json     # the same as JSON

A rule can be skipped with a line `Guardrail-Skip: <spec|tests|regression> — <reason of 10+ characters>` in a commit message of the branch or in the
pull request text (the environment variable PR_BODY). The rules themselves are pure (evaluate), so they are tested without git."""
import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field

CODE_PREFIXES = ("apps/web/", "assets/", "supabase/", "templates/", "tools/")
CODE_FILES = ("site.config.json",)
SPEC_PREFIX = "docs/spec/"
TEST_PREFIX = "tests/"
RULES = ("spec", "tests", "regression")
MIN_REASON = 10
SKIP_LINE = re.compile(r"^[ \t>*-]*Guardrail-Skip:[ \t]*(\S+?)[ \t]*(?:[—–-]+[ \t]*(.*?))?[ \t]*$", re.M | re.I)
# a skip that only says "this environment may lack node / the SQL parser" is how the suite is already written: not a skipped test
ENV_SKIP = re.compile(r"skipUnless\((shutil\.which|pglast)")
# a real use at the start of a line: a decorator, or a skip statement (not the word inside a string or a comment)
SKIP_USE = re.compile(r"^\s*(@(unittest\.)?(skip|skipIf|skipUnless|expectedFailure)\b|@pytest\.mark\.(skip|xfail)\b|self\.skipTest\(|raise unittest\.SkipTest)")


@dataclass
class Branch:
    files: list                      # [(status, path)]
    added_tests: int = 0
    removed_tests: int = 0
    added_skips: list = field(default_factory=list)
    messages: str = ""
    spec_before_code: bool = True


@dataclass
class Finding:
    rule: str
    message: str


@dataclass
class Skip:
    rule: str
    reason: str


@dataclass
class Result:
    failures: list
    skipped: list
    warnings: list

    @property
    def ok(self):
        return not self.failures


def is_code(path):
    return path.startswith(CODE_PREFIXES) or path in CODE_FILES


def skips_in(text):
    """The valid skip lines of a text (a known rule and a reason of enough characters)."""
    out = []
    for m in SKIP_LINE.finditer(text or ""):
        rule, reason = m.group(1).lower(), (m.group(2) or "").strip()
        if rule in RULES and len(reason) >= MIN_REASON:
            out.append(Skip(rule, reason))
    return out


def evaluate(b):
    paths = [p for _, p in b.files]
    code = [p for p in paths if is_code(p)]
    found = []
    if code:
        if not any(p.startswith(SPEC_PREFIX) for p in paths):
            found.append(Finding("spec", f"code changed ({len(code)} file(s), e.g. {code[0]}) but no spec under {SPEC_PREFIX} did: write or update the spec first (SDD)"))
        if b.added_tests <= 0:
            found.append(Finding("tests", f"code changed ({len(code)} file(s), e.g. {code[0]}) but no test was added: add a `def test_…` in {TEST_PREFIX} that fails without the change"))
    if b.removed_tests > b.added_tests:
        found.append(Finding("regression", f"{b.removed_tests - b.added_tests} more test(s) removed than added ({b.removed_tests} removed, {b.added_tests} added): the suite must not shrink"))
    if b.added_skips:
        found.append(Finding("regression", f"{len(b.added_skips)} test(s) skipped or expected to fail (skip): a test that is skipped is a test that does not protect, e.g. {b.added_skips[0].strip()[:80]}"))
    valid = skips_in(b.messages)
    skipped = []
    failures = []
    for f in found:
        s = next((x for x in valid if x.rule == f.rule), None)
        if s:
            skipped.append(Skip(f.rule, s.reason))
        else:
            failures.append(f)
    # a Guardrail-Skip line that is not valid says why it was not accepted
    for m in SKIP_LINE.finditer(b.messages or ""):
        rule, reason = m.group(1).lower(), (m.group(2) or "").strip()
        if rule not in RULES:
            failures.append(Finding("skip", f"`Guardrail-Skip: {m.group(1)}` is not accepted: the rule must be one of {', '.join(RULES)} (never `all`)"))
        elif len(reason) < MIN_REASON:
            failures.append(Finding("skip", f"`Guardrail-Skip: {rule}` needs a reason of at least {MIN_REASON} characters"))
    warnings = []
    if code and any(p.startswith(SPEC_PREFIX) for p in paths) and not b.spec_before_code:
        warnings.append("the spec was committed after the code: write the spec before the code (SDD); put the commit that changes docs/spec/ before the one that changes code")
    return Result(failures, skipped, warnings)


# -- reading a git repository ----------------------------------------------------------------------------------------------
def _git(repo, *args):
    r = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout


def read_branch(repo, base):
    mb = _git(repo, "merge-base", base, "HEAD").strip()
    files = []
    for line in _git(repo, "diff", "--name-status", "--no-renames", mb, "HEAD").splitlines():
        status, _, path = line.partition("\t")
        files.append((status, path))
    diff = _git(repo, "diff", "-U0", "--no-renames", mb, "HEAD", "--", TEST_PREFIX)
    added = removed = 0
    skips = []
    for line in diff.splitlines():
        if line.startswith("+++") or line.startswith("---"):
            continue
        if re.match(r"^\+\s*(async\s+)?def test_", line):
            added += 1
        elif re.match(r"^-\s*(async\s+)?def test_", line):
            removed += 1
        elif line.startswith("+") and SKIP_USE.search(line) and not ENV_SKIP.search(line):
            skips.append(line[1:])
    first_spec = first_code = None
    for i, sha in enumerate(_git(repo, "log", "--reverse", "--format=%H", f"{mb}..HEAD").split()):
        names = _git(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", "--no-renames", "-m", "--first-parent", sha).split()
        if first_spec is None and any(n.startswith(SPEC_PREFIX) for n in names):
            first_spec = i
        if first_code is None and any(is_code(n) for n in names):
            first_code = i
    messages = _git(repo, "log", "--format=%B", f"{mb}..HEAD") + "\n" + os.environ.get("PR_BODY", "")
    ordered = first_spec is not None and (first_code is None or first_spec <= first_code)
    return Branch(files, added, removed, skips, messages, ordered)


def report(r, as_json):
    if as_json:
        return json.dumps({"ok": r.ok, "failures": [f.__dict__ for f in r.failures], "skipped": [s.__dict__ for s in r.skipped], "warnings": r.warnings}, ensure_ascii=False)
    lines = []
    for f in r.failures:
        lines.append(f"FAIL [{f.rule}] {f.message}")
    for s in r.skipped:
        lines.append(f"skip [{s.rule}] accepted: {s.reason}")
    for w in r.warnings:
        lines.append(f"warn {w}")
    if r.failures:
        lines.append("\nGuardrail: the branch breaks the rules of docs/spec/v2/guardrail.md. Fix it, or — only when a rule truly does not apply — add a line\n"
                     "  Guardrail-Skip: <spec|tests|regression> — <reason of 10+ characters>\nto a commit message or to the pull request text.")
    else:
        lines.append("Guardrail: ok")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base", default="origin/main")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    r = evaluate(read_branch(a.repo, a.base))
    print(report(r, a.json))
    return 0 if r.ok else 1


if __name__ == "__main__":
    sys.exit(main())
