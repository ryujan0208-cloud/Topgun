# -*- coding: utf-8 -*-
"""Verify that matched replay tracks are identical before a fork boundary."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path


def compare_tracks(
    baseline_path: Path, candidate_path: Path, fork_start_s: float
) -> dict[str, object]:
    with baseline_path.open(newline="", encoding="utf-8-sig") as handle:
        baseline_reader = csv.DictReader(handle)
        baseline_fields = baseline_reader.fieldnames
        baseline = list(baseline_reader)
    with candidate_path.open(newline="", encoding="utf-8-sig") as handle:
        candidate_reader = csv.DictReader(handle)
        candidate_fields = candidate_reader.fieldnames
        candidate = list(candidate_reader)
    if baseline_fields != candidate_fields:
        raise ValueError("track schemas differ")

    first_difference_index: int | None = None
    first_difference_time_s: float | None = None
    differing_columns: list[str] = []
    pre_fork_rows = 0
    pre_fork_equal = True
    for index, (base_row, candidate_row) in enumerate(zip(baseline, candidate)):
        base_time = float(base_row["Time"])
        candidate_time = float(candidate_row["Time"])
        before_fork = min(base_time, candidate_time) < fork_start_s
        if before_fork:
            pre_fork_rows += 1
        if base_row == candidate_row:
            continue
        columns = [
            name for name in (baseline_fields or ()) if base_row[name] != candidate_row[name]
        ]
        if before_fork:
            pre_fork_equal = False
        if first_difference_index is None:
            first_difference_index = index
            first_difference_time_s = min(base_time, candidate_time)
            differing_columns = columns

    if len(baseline) != len(candidate):
        shorter = min(len(baseline), len(candidate))
        if first_difference_index is None:
            first_difference_index = shorter
            remaining = baseline[shorter:] or candidate[shorter:]
            first_difference_time_s = float(remaining[0]["Time"])
            differing_columns = ["<row_count>"]
        if first_difference_time_s is not None and first_difference_time_s < fork_start_s:
            pre_fork_equal = False

    return {
        "baseline_rows": len(baseline),
        "candidate_rows": len(candidate),
        "pre_fork_rows": pre_fork_rows,
        "pre_fork_equal": pre_fork_equal,
        "first_difference_index": first_difference_index,
        "first_difference_time_s": first_difference_time_s,
        "differing_columns": differing_columns,
    }


def _track_path(logdir: Path, stamp: str, role: str) -> Path:
    suffix = "ownship_(F-16)[Blue].csv" if role == "ownship" else "target_(F-16)[Red].csv"
    return logdir / f"{stamp}_{suffix}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--logdir", type=Path, required=True)
    parser.add_argument("--baseline-stamp", required=True)
    parser.add_argument("--candidate-stamp", required=True)
    parser.add_argument("--fork-start", type=float, required=True)
    args = parser.parse_args()
    failed = False
    for role in ("ownship", "target"):
        report = compare_tracks(
            _track_path(args.logdir, args.baseline_stamp, role),
            _track_path(args.logdir, args.candidate_stamp, role),
            args.fork_start,
        )
        print(
            f"[{role}] pre_fork_equal={report['pre_fork_equal']} "
            f"pre_fork_rows={report['pre_fork_rows']} "
            f"first_difference_time_s={report['first_difference_time_s']} "
            f"columns={','.join(report['differing_columns']) or '-'}"
        )
        failed = failed or not bool(report["pre_fork_equal"])
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
