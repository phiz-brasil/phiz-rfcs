#!/usr/bin/env python3
"""The whole test suite, in parallel (docs/spec/v2/guardrail.md, "A faster suite, the same coverage").

    python tools/run_tests.py [--workers N]

Same tests as `python -m unittest discover -s tests`, but the site is built once and the test FILES are spread over N processes, each with its own `next start`
(each file runs whole in one process, in the same order as before). A file that is in no shard would silently not run, so `shards()` is tested to cover every
tests/test_*.py exactly once, and the count of tests is compared with `unittest discover`."""
import argparse
import os
import subprocess
import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TESTS = ROOT / "tests"

# measured seconds per file (2026-11-24, one process); only decides how the files are spread, never what runs. A file without a weight counts as DEFAULT.
WEIGHT = {"test_site": 14.4, "test_login": 13.3, "test_board": 11.4, "test_live": 9.8, "test_attachments": 9.5, "test_images": 9.1, "test_themes": 8.6,
          "test_weekly": 7.7, "test_images_on_demand": 6.9, "test_summary": 6.5, "test_metrics_page": 4.6, "test_suggest": 4.3, "test_member_lock": 4.0,
          "test_metrics": 3.9, "test_slides": 3.8, "test_roadmap": 2.9, "test_overview": 2.8, "test_guardrail": 2.1, "test_render_js": 2.0}
DEFAULT = 3.0


def test_files(tests_dir=TESTS):
    return sorted(p.stem for p in Path(tests_dir).glob("test_*.py"))


def shards(files, workers, weight=WEIGHT):
    """The files spread over `workers` lists: heaviest first, each to the lightest list so far. Every file appears exactly once."""
    workers = max(1, min(workers, len(files) or 1))
    lists = [[] for _ in range(workers)]
    load = [0.0] * workers
    for f in sorted(files, key=lambda f: (-weight.get(f, DEFAULT), f)):
        i = load.index(min(load))
        lists[i].append(f)
        load[i] += weight.get(f, DEFAULT)
    return [sorted(l) for l in lists if l]


def count_tests(modules, tests_dir=TESTS):
    sys.path.insert(0, str(tests_dir))
    try:
        loader = unittest.TestLoader()
        return sum(loader.loadTestsFromName(m).countTestCases() for m in modules)
    finally:
        sys.path.remove(str(tests_dir))


def run_shards(tests_dir, lists, env):
    """One `python -m unittest` per list, all at once; (exit code, text) with the output of every shard that failed. 0 only if every shard passed."""
    procs = [(l, subprocess.Popen([sys.executable, "-m", "unittest", "-q", *l], cwd=tests_dir, env=env, text=True,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT)) for l in lists]
    code, report = 0, []
    for l, p in procs:
        out, _ = p.communicate()
        if p.returncode != 0:
            code = 1
            report.append("=== shard failed: %s\n%s" % (" ".join(l), out))
        else:
            report.append("--- shard ok: %s  %s" % (" ".join(l), out.strip().splitlines()[-1] if out.strip() else ""))
    return code, "\n".join(report)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--workers", type=int, default=min(os.cpu_count() or 1, 4))
    args = ap.parse_args(argv)
    t0 = time.time()
    files = test_files()
    lists = shards(files, args.workers)
    expected = count_tests(files)
    env = dict(os.environ)
    sys.path.insert(0, str(TESTS))
    from support import _Site  # builds once (unless SKIP_BUILD / SITE_URL); every shard then starts its own `next start` from that build
    if not env.get("SITE_URL"):
        _Site.build()
        env["SKIP_BUILD"] = "1"
    code, report = run_shards(TESTS, lists, env)
    print(report)
    print("\n%d test files, %d tests, %d workers, %.1fs" % (len(files), expected, len(lists), time.time() - t0))
    return code


if __name__ == "__main__":
    sys.exit(main())
