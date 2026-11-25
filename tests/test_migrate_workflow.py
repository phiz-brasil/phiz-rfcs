"""Migrations are applied by the CI (docs/spec/v2/migrations.md): the workflow, the config and the helper that lists versions."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import migration_versions  # noqa: E402

WORKFLOW = (ROOT / ".github" / "workflows" / "migrate.yml").read_text(encoding="utf-8")


class WorkflowTest(unittest.TestCase):
    def test_runs_on_push_to_main_for_migrations_and_by_hand_with_a_baseline(self):
        self.assertIn("branches: [main]", WORKFLOW)
        self.assertIn('paths: ["supabase/migrations/**"]', WORKFLOW)
        self.assertIn("workflow_dispatch:", WORKFLOW)
        self.assertIn("baseline:", WORKFLOW)

    def test_pushes_the_migrations_with_the_cli(self):
        self.assertIn("supabase db push", WORKFLOW)
        self.assertIn("supabase link --project-ref", WORKFLOW)
        self.assertIn("migration_versions.py --through", WORKFLOW)

    def test_every_database_command_targets_the_linked_project(self):
        for cmd in ("migration repair --status applied --remote", "migration list --remote", "db push --remote"):
            self.assertIn("supabase " + cmd, WORKFLOW)

    def test_secrets_come_from_github_and_none_is_written_in_the_file(self):
        for name in ("SUPABASE_ACCESS_TOKEN", "SUPABASE_DB_PASSWORD", "SUPABASE_PROJECT_REF"):
            self.assertIn("${{ secrets.%s }}" % name, WORKFLOW)
        self.assertNotIn("zuwbjcwfqzucjmxrehad", WORKFLOW)

    def test_runs_are_serialised_and_never_cancelled_midway(self):
        self.assertIn("concurrency:", WORKFLOW)
        self.assertIn("cancel-in-progress: false", WORKFLOW)
        self.assertIn("contents: read", WORKFLOW)

    def test_the_cli_has_a_config_to_link_with(self):
        self.assertRegex((ROOT / "supabase" / "config.toml").read_text(encoding="utf-8"), r'(?m)^project_id = "[^"]+"')


class VersionsTest(unittest.TestCase):
    def test_every_real_migration_is_a_valid_unique_version(self):
        v = migration_versions.versions()
        self.assertGreaterEqual(len(v), 19)
        self.assertEqual(v, sorted(set(v)))

    def test_through_is_inclusive_and_ordered(self):
        with tempfile.TemporaryDirectory() as d:
            for n in ("20260102000000_b.sql", "20260101000000_a.sql", "20260103000000_c.sql"):
                (Path(d) / n).write_text("select 1;")
            self.assertEqual(migration_versions.through("20260102000000", d), ["20260101000000", "20260102000000"])

    def test_a_limit_that_is_not_a_migration_is_refused(self):
        r = subprocess.run([sys.executable, str(ROOT / "tools" / "migration_versions.py"), "--through", "20991231000000"], capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("not the version of a migration file", r.stderr)

    def test_a_badly_named_file_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "fup.sql").write_text("select 1;")
            with self.assertRaises(SystemExit):
                migration_versions.versions(d)


if __name__ == "__main__":
    unittest.main()
