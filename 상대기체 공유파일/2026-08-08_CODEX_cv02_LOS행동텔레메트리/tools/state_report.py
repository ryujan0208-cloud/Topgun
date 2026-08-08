# -*- coding: utf-8 -*-
"""Summarize combat-state distributions before future health changes.

The report is observational: a state appearing before damage does not prove
that the recorded action caused the damage. Its purpose is to locate supported
state regions for later counterfactual replay.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Iterable, Sequence

import state_dataset


FEATURES = (
    *state_dataset.LOS_FEATURES,
    "range_m",
    "own_ata_deg",
    "target_ata_deg",
    "relative_heading_deg",
    "closure_mps",
    "altitude_delta_m",
    "own_speed_mps",
    "target_speed_mps",
    "energy_height_delta_m",
    "own_turn_rate_dps",
    "target_turn_rate_dps",
)


def quantile(values: Sequence[float], probability: float) -> float | None:
    if not values:
        return None
    if not 0.0 <= probability <= 1.0:
        raise ValueError("probability must be between zero and one")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * probability
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _empty_bucket() -> dict[str, object]:
    return {"count": 0, "features": {name: [] for name in FEATURES}}


def _append(bucket: dict[str, object], row: dict[str, object]) -> None:
    bucket["count"] = int(bucket["count"]) + 1
    feature_values = bucket["features"]
    assert isinstance(feature_values, dict)
    for name in FEATURES:
        value = float(row[name])
        if math.isfinite(value):
            feature_values[name].append(value)


def summarize_rows(
    rows: Iterable[dict[str, object]], horizon_s: float, epsilon: float = 1e-9
) -> dict[str, object]:
    label = f"h{horizon_s:g}"
    buckets = {
        "all_available": _empty_bucket(),
        "future_dealt": _empty_bucket(),
        "future_taken": _empty_bucket(),
        "future_positive_net": _empty_bucket(),
        "future_negative_net": _empty_bucket(),
    }
    total_rows = 0
    episodes: set[int] = set()
    for row in rows:
        total_rows += 1
        episodes.add(int(row["episode"]))
        if int(row[f"{label}_available"]) != 1:
            continue
        _append(buckets["all_available"], row)
        dealt = float(row[f"{label}_dealt"])
        taken = float(row[f"{label}_taken"])
        net = float(row[f"{label}_net"])
        if dealt > epsilon:
            _append(buckets["future_dealt"], row)
        if taken > epsilon:
            _append(buckets["future_taken"], row)
        if net > epsilon:
            _append(buckets["future_positive_net"], row)
        if net < -epsilon:
            _append(buckets["future_negative_net"], row)

    output_buckets: dict[str, object] = {}
    for name, bucket in buckets.items():
        feature_values = bucket["features"]
        assert isinstance(feature_values, dict)
        output_buckets[name] = {
            "count": bucket["count"],
            "features": {
                feature: {
                    "p10": quantile(values, 0.10),
                    "p50": quantile(values, 0.50),
                    "p90": quantile(values, 0.90),
                }
                for feature, values in feature_values.items()
            },
        }
    return {
        "total_rows": total_rows,
        "episodes": len(episodes),
        "horizon_s": horizon_s,
        "buckets": output_buckets,
    }


def _format_number(value: float | None) -> str:
    return "-" if value is None else f"{value:.2f}"


def print_report(label: str, stamp: str, report: dict[str, object]) -> None:
    print(
        f"[{label}] stamp={stamp} rows={report['total_rows']} episodes={report['episodes']} horizon={report['horizon_s']}s"
    )
    buckets = report["buckets"]
    assert isinstance(buckets, dict)
    for name in (
        "all_available",
        "future_dealt",
        "future_taken",
        "future_positive_net",
        "future_negative_net",
    ):
        bucket = buckets[name]
        print(f"  {name}: n={bucket['count']}")
        if name not in ("future_dealt", "future_taken") or int(bucket["count"]) == 0:
            continue
        for feature in FEATURES:
            stats = bucket["features"][feature]
            print(
                f"    {feature:24s} "
                f"p10={_format_number(stats['p10']):>9s} "
                f"p50={_format_number(stats['p50']):>9s} "
                f"p90={_format_number(stats['p90']):>9s}"
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--logdir", type=Path, required=True)
    parser.add_argument("--stamp", required=True)
    parser.add_argument("--label", default="run")
    parser.add_argument("--horizon", type=float, default=10.0)
    parser.add_argument("--sample-hz", type=float, default=10.0)
    parser.add_argument("--derivative-window", type=int, default=6)
    parser.add_argument("--jump-threshold-m", type=float, default=2_000.0)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    if args.horizon <= 0.0:
        parser.error("--horizon must be positive")
    own = state_dataset.load_track(
        args.logdir / f"{args.stamp}_ownship_(F-16)[Blue].csv"
    )
    target = state_dataset.load_track(
        args.logdir / f"{args.stamp}_target_(F-16)[Red].csv"
    )
    rows = state_dataset.iter_rows(
        own,
        target,
        [args.horizon],
        args.sample_hz,
        args.derivative_window,
        args.jump_threshold_m,
    )
    report = summarize_rows(rows, args.horizon)
    report["label"] = args.label
    report["stamp"] = args.stamp
    print_report(args.label, args.stamp, report)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"  json={args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
