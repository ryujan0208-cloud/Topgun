from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path


TOOLS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS_DIR))

import prefix_compare as subject  # noqa: E402


class PrefixCompareTest(unittest.TestCase):
    def _write(self, path: Path, values: list[tuple[float, float]]) -> None:
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["Time", "Value"])
            writer.writeheader()
            for time_s, value in values:
                writer.writerow({"Time": time_s, "Value": value})

    def test_accepts_difference_after_fork(self):
        with tempfile.TemporaryDirectory() as directory:
            baseline = Path(directory) / "baseline.csv"
            candidate = Path(directory) / "candidate.csv"
            self._write(baseline, [(0.0, 1.0), (1.0, 1.0), (2.0, 1.0)])
            self._write(candidate, [(0.0, 1.0), (1.0, 1.0), (2.0, 2.0)])

            report = subject.compare_tracks(baseline, candidate, 1.5)

            self.assertTrue(report["pre_fork_equal"])
            self.assertEqual(report["first_difference_time_s"], 2.0)

    def test_rejects_difference_before_fork(self):
        with tempfile.TemporaryDirectory() as directory:
            baseline = Path(directory) / "baseline.csv"
            candidate = Path(directory) / "candidate.csv"
            self._write(baseline, [(0.0, 1.0), (1.0, 1.0)])
            self._write(candidate, [(0.0, 1.0), (1.0, 2.0)])

            report = subject.compare_tracks(baseline, candidate, 2.0)

            self.assertFalse(report["pre_fork_equal"])


if __name__ == "__main__":
    unittest.main()
