"""tools/guardrail.py against docs/spec/v2/guardrail.md: the rules are applied to a description of a branch (files, test lines, skips, messages);
a few tests also run it on real temporary git repositories."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import guardrail as G  # noqa: E402


def info(files=(), added=0, removed=0, skips=(), messages="", order_ok=True):
    return G.Branch(files=[("M", f) for f in files], added_tests=added, removed_tests=removed, added_skips=list(skips), messages=messages, spec_before_code=order_ok)


def rules(result):
    return sorted(f.rule for f in result.failures)


class RulesTest(unittest.TestCase):
    def test_a_change_of_code_alone_fails_all_three_rules(self):
        r = G.evaluate(info(["apps/web/lib/x.ts"]))
        self.assertEqual(rules(r), ["spec", "tests"])                  # nothing removed, no skips: regression holds
        self.assertFalse(r.ok)

    def test_code_with_a_spec_and_a_new_test_passes(self):
        r = G.evaluate(info(["apps/web/lib/x.ts", "docs/spec/v2/x.md", "tests/test_x.py"], added=2))
        self.assertTrue(r.ok, r.failures)

    def test_a_spec_without_a_test_still_fails_the_tests_rule(self):
        self.assertEqual(rules(G.evaluate(info(["supabase/migrations/1_x.sql", "docs/spec/v2/x.md"]))), ["tests"])

    def test_a_test_without_a_spec_fails_the_spec_rule(self):
        self.assertEqual(rules(G.evaluate(info(["assets/js/live.js", "tests/test_x.py"], added=1))), ["spec"])

    def test_every_kind_of_code_path_counts(self):
        for path in ("apps/web/components/A.tsx", "assets/rfc-site.css", "supabase/functions/a/index.ts", "templates/page.css", "tools/build.py", "site.config.json"):
            with self.subTest(path):
                self.assertFalse(G.evaluate(info([path])).ok)

    def test_changes_that_are_not_code_need_neither_spec_nor_tests(self):
        for path in ("docs/spec/v2/x.md", "README.md", ".github/workflows/x.yml", ".claude/settings.json", "CLAUDE.md", "tests/support.py"):
            with self.subTest(path):
                self.assertTrue(G.evaluate(info([path])).ok)

    def test_a_branch_with_no_changes_passes(self):
        self.assertTrue(G.evaluate(info([])).ok)

    # -- regression ------------------------------------------------------------------------------------------------
    def test_removing_more_tests_than_are_added_fails(self):
        r = G.evaluate(info(["tests/test_x.py"], added=1, removed=3))
        self.assertEqual(rules(r), ["regression"])
        self.assertIn("2", r.failures[0].message)

    def test_moving_or_renaming_tests_is_fine(self):
        self.assertTrue(G.evaluate(info(["tests/test_x.py"], added=4, removed=4)).ok)
        self.assertTrue(G.evaluate(info(["tests/test_x.py"], added=6, removed=2)).ok)

    def test_a_new_skip_fails(self):
        r = G.evaluate(info(["tests/test_x.py"], added=1, skips=["+    @unittest.skip('later')"]))
        self.assertEqual(rules(r), ["regression"])
        self.assertIn("skip", r.failures[0].message)

    # -- skips -----------------------------------------------------------------------------------------------------
    def test_a_skip_line_with_a_reason_lets_a_rule_through(self):
        msg = "Guardrail-Skip: spec — the change only renames a CSS class"
        r = G.evaluate(info(["assets/rfc-site.css", "tests/test_x.py"], added=1, messages=msg))
        self.assertTrue(r.ok, r.failures)
        self.assertEqual([s.rule for s in r.skipped], ["spec"])

    def test_each_rule_can_be_skipped_on_its_own(self):
        msg = "Guardrail-Skip: spec — typo in a label\nGuardrail-Skip: tests - dependency bump, the suite covers it"
        self.assertTrue(G.evaluate(info(["apps/web/lib/x.ts"], messages=msg)).ok)
        only_spec = G.evaluate(info(["apps/web/lib/x.ts"], messages="Guardrail-Skip: spec — typo in a label"))
        self.assertEqual(rules(only_spec), ["tests"])

    def test_a_removed_test_can_be_accepted_with_a_reason(self):
        msg = "Guardrail-Skip: regression — test X checked the old URL; test Y checks the same behaviour"
        self.assertTrue(G.evaluate(info(["tests/test_x.py"], removed=2, messages=msg)).ok)

    def test_a_skip_with_a_short_reason_an_unknown_rule_or_all_is_refused(self):
        for msg in ("Guardrail-Skip: spec — ok", "Guardrail-Skip: nothing — a long enough reason here", "Guardrail-Skip: all — a long enough reason here", "Guardrail-Skip: spec"):
            with self.subTest(msg):
                r = G.evaluate(info(["apps/web/lib/x.ts", "tests/test_x.py"], added=1, messages=msg))
                self.assertFalse(r.ok)
                self.assertIn("spec", rules(r))

    def test_the_skip_line_is_found_in_the_middle_of_a_pull_request_text(self):
        text = "## What\nthings\n\nGuardrail-Skip: spec — only a CSS class was renamed\n\n🤖 Generated with Claude"
        self.assertEqual([(s.rule, s.reason) for s in G.skips_in(text)], [("spec", "only a CSS class was renamed")])

    # -- the order of the spec and the code (a warning, never a failure) ----------------------------------------------------
    def test_a_spec_that_came_after_the_code_is_only_a_warning(self):
        r = G.evaluate(info(["apps/web/lib/x.ts", "docs/spec/v2/x.md", "tests/test_x.py"], added=1, order_ok=False))
        self.assertTrue(r.ok)
        self.assertEqual(len(r.warnings), 1)
        self.assertIn("before", r.warnings[0])


def git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True, env={**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"})


def write(repo, path, text):
    p = Path(repo) / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf8")


class GitTest(unittest.TestCase):
    """The checker on a real repository: a main branch with one test, then a feature branch."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = self.tmp.name
        git(self.repo, "init", "-q", "-b", "main")
        write(self.repo, "tests/test_a.py", "def test_one(): pass\ndef test_two(): pass\n")
        write(self.repo, "apps/web/lib/a.ts", "export const a = 1;\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "base")
        git(self.repo, "checkout", "-q", "-b", "feature")

    def tearDown(self):
        self.tmp.cleanup()

    def commit(self, msg, **files):
        for key, text in files.items():                      # tests__test_a_py -> tests/test_a.py
            path = key.replace("__", "/")
            stem, _, ext = path.rpartition("_")
            write(self.repo, f"{stem}.{ext}", text)
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", msg)

    def run_checker(self, *extra):
        return subprocess.run([sys.executable, str(ROOT / "tools" / "guardrail.py"), "--base", "main", "--repo", self.repo, "--json", *extra], capture_output=True, text=True)

    def test_code_only_fails_with_exit_code_1(self):
        self.commit("code", apps__web__lib__a_ts="export const a = 2;\n")
        out = self.run_checker()
        self.assertEqual(out.returncode, 1, out.stdout)
        self.assertEqual(sorted(f["rule"] for f in json.loads(out.stdout)["failures"]), ["spec", "tests"])

    def test_spec_then_code_with_a_test_passes_without_a_warning(self):
        self.commit("spec", docs__spec__v2__a_md="# a\n")
        self.commit("code and test", apps__web__lib__a_ts="export const a = 2;\n", tests__test_a_py="def test_one(): pass\ndef test_two(): pass\ndef test_three(): pass\n")
        out = self.run_checker()
        self.assertEqual(out.returncode, 0, out.stdout)
        self.assertEqual(json.loads(out.stdout)["warnings"], [])

    def test_code_then_spec_passes_with_a_warning(self):
        self.commit("code and test", apps__web__lib__a_ts="export const a = 2;\n", tests__test_a_py="def test_one(): pass\ndef test_two(): pass\ndef test_three(): pass\n")
        self.commit("spec", docs__spec__v2__a_md="# a\n")
        out = self.run_checker()
        self.assertEqual(out.returncode, 0, out.stdout)
        self.assertEqual(len(json.loads(out.stdout)["warnings"]), 1)

    def test_deleting_a_test_fails_and_a_reason_in_a_commit_message_accepts_it(self):
        self.commit("drop a test", tests__test_a_py="def test_one(): pass\n")
        self.assertEqual(self.run_checker().returncode, 1)
        git(self.repo, "commit", "-q", "--allow-empty", "-m", "why\n\nGuardrail-Skip: regression — test_two checked the old URL, test_one covers the same")
        self.assertEqual(self.run_checker().returncode, 0)

    def test_a_skip_in_the_pull_request_text_is_read_from_the_environment(self):
        self.commit("code", apps__web__lib__a_ts="export const a = 2;\n")
        out = subprocess.run([sys.executable, str(ROOT / "tools" / "guardrail.py"), "--base", "main", "--repo", self.repo, "--json"], capture_output=True, text=True,
                             env={**os.environ, "PR_BODY": "Guardrail-Skip: spec — only a constant changed\nGuardrail-Skip: tests — the suite covers this constant"})
        self.assertEqual(out.returncode, 0, out.stdout)

    def test_a_branch_equal_to_its_base_passes(self):
        self.assertEqual(self.run_checker().returncode, 0)


class HookTest(unittest.TestCase):
    """.claude/hooks/guardrail.sh: it refuses `git push` and `gh pr create` when the checker fails, and lets every other command through."""
    HOOK = ROOT / ".claude" / "hooks" / "guardrail.sh"

    def call(self, command, checker_exit):
        env = {**os.environ, "GUARDRAIL_CMD": f"exit {checker_exit}"}                # the hook runs this instead of the real checker
        return subprocess.run(["bash", str(self.HOOK)], input=json.dumps({"tool_input": {"command": command}}), capture_output=True, text=True, env=env)

    def test_it_blocks_a_push_and_a_pull_request_when_the_checker_fails(self):
        for cmd in ("git push -u origin x", "gh pr create --title t", "cd repo && git push", "git push origin HEAD:main"):
            with self.subTest(cmd):
                r = self.call(cmd, 1)
                self.assertEqual(r.returncode, 2)
                self.assertIn("guardrail", r.stderr.lower())

    def test_it_lets_them_through_when_the_checker_passes(self):
        for cmd in ("git push -u origin x", "gh pr create --title t"):
            self.assertEqual(self.call(cmd, 0).returncode, 0)

    def test_other_commands_are_never_checked(self):
        for cmd in ("ls -la", "git status", "git commit -m x", "gh pr merge 3", "npm test", "echo git push"):
            with self.subTest(cmd):
                self.assertEqual(self.call(cmd, 1).returncode, 0)


if __name__ == "__main__":
    unittest.main()
