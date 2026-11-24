"""tools/run_tests.py (docs/spec/v2/guardrail.md, "A faster suite, the same coverage"): the parallel runner must run everything the plain suite runs."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import run_tests as R  # noqa: E402


class ShardsTest(unittest.TestCase):
    def test_every_test_file_is_in_exactly_one_shard(self):
        files = R.test_files()
        self.assertGreater(len(files), 20)
        for workers in (1, 2, 3, 4, 7, 100):
            lists = R.shards(files, workers)
            flat = [f for l in lists for f in l]
            self.assertEqual(sorted(flat), files, f"{workers} workers")             # none lost, none twice
            self.assertEqual(len(flat), len(set(flat)))

    def test_the_runner_counts_the_same_tests_as_unittest_discover(self):
        discovered = unittest.TestLoader().discover(str(Path(__file__).resolve().parent), top_level_dir=str(Path(__file__).resolve().parent)).countTestCases()
        self.assertEqual(R.count_tests(R.test_files()), discovered)

    def test_the_load_is_balanced_by_weight(self):
        weight = {"a": 10, "b": 9, "c": 5, "d": 5, "e": 1}
        lists = R.shards(list(weight), 2, weight)
        loads = sorted(sum(weight[f] for f in l) for l in lists)
        self.assertLessEqual(loads[1] - loads[0], 2)

    def test_a_file_without_a_weight_still_runs(self):
        lists = R.shards(["new_file", "test_site"], 2)
        self.assertEqual(sorted(f for l in lists for f in l), ["new_file", "test_site"])

    def test_more_workers_than_files_gives_one_file_per_shard(self):
        self.assertEqual(sorted(map(len, R.shards(["a", "b", "c"], 10))), [1, 1, 1])


class RunShardsTest(unittest.TestCase):
    def tmp_suite(self, **modules):
        d = tempfile.mkdtemp()
        for name, body in modules.items():
            (Path(d) / f"{name}.py").write_text("import unittest\nclass T(unittest.TestCase):\n" + body, encoding="utf-8")
        return d

    def test_it_passes_when_every_shard_passes(self):
        d = self.tmp_suite(test_a="    def test_x(self): pass\n", test_b="    def test_y(self): pass\n")
        code, report = R.run_shards(d, [["test_a"], ["test_b"]], {})
        self.assertEqual(code, 0, report)

    def test_one_failing_shard_fails_the_run_and_shows_its_output(self):
        d = self.tmp_suite(test_a="    def test_x(self): pass\n", test_b="    def test_y(self): self.fail('boom')\n")
        code, report = R.run_shards(d, [["test_a"], ["test_b"]], {})
        self.assertEqual(code, 1)
        self.assertIn("shard failed: test_b", report)
        self.assertIn("boom", report)
        self.assertIn("shard ok: test_a", report)


class ServerPerWorkerTest(unittest.TestCase):
    """docs/spec/v2/guardrail.md: the runner builds once and does not hand one shared server (SITE_URL) to the workers: each one starts its own."""

    def test_the_runner_builds_once_and_gives_the_workers_no_shared_site_url(self):
        src = (Path(__file__).resolve().parent.parent / "tools" / "run_tests.py").read_text(encoding="utf-8")
        self.assertIn("_Site.build()", src)
        self.assertIn('env["SKIP_BUILD"] = "1"', src)
        self.assertNotIn('env["SITE_URL"] = _Site.start()', src)
