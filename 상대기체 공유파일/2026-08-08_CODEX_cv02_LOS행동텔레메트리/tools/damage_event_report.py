# -*- coding: utf-8 -*-
"""Summarize independent damage-event CSVs with contribution checks."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Iterable, Sequence

import state_dataset
import state_report


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
)


def _horizon_key(horizon_s: float) -> str:
    return f"pre_{horizon_s:g}s".replace(".", "p")


def summarize(
    rows: Iterable[dict[str, str]], horizons_s: Sequence[float]
) -> dict[str, object]:
    materialized = list(rows)
    output: dict[str, object] = {"events": len(materialized), "kinds": {}}
    kinds = output["kinds"]
    assert isinstance(kinds, dict)
    for kind in ("dealt", "taken"):
        selected = [row for row in materialized if row["kind"] == kind]
        total_damage = sum(float(row["damage"]) for row in selected)
        episode_damage: dict[int, float] = defaultdict(float)
        for row in selected:
            episode_damage[int(row["episode"])] += float(row["damage"])
        largest_event = max(
            selected, key=lambda row: float(row["damage"]), default=None
        )
        largest_episode = max(
            episode_damage.items(), key=lambda item: item[1], default=None
        )
        horizon_reports: dict[str, object] = {}
        for horizon in horizons_s:
            prefix = _horizon_key(horizon)
            available = [
                row for row in selected if int(row[f"{prefix}_available"]) == 1
            ]
            horizon_reports[f"{horizon:g}"] = {
                "available": len(available),
                "features": {
                    feature: {
                        "p10": state_report.quantile(
                            [float(row[f"{prefix}_{feature}"]) for row in available],
                            0.10,
                        ),
                        "p50": state_report.quantile(
                            [float(row[f"{prefix}_{feature}"]) for row in available],
                            0.50,
                        ),
                        "p90": state_report.quantile(
                            [float(row[f"{prefix}_{feature}"]) for row in available],
                            0.90,
                        ),
                    }
                    for feature in FEATURES
                },
            }
        kinds[kind] = {
            "count": len(selected),
            "total_damage": total_damage,
            "episodes_with_events": len(episode_damage),
            "largest_event_id": None
            if largest_event is None
            else largest_event["event_id"],
            "largest_event_damage": None
            if largest_event is None
            else float(largest_event["damage"]),
            "largest_event_share": (
                None
                if largest_event is None or total_damage <= 0.0
                else float(largest_event["damage"]) / total_damage
            ),
            "largest_episode": None if largest_episode is None else largest_episode[0],
            "largest_episode_damage": None
            if largest_episode is None
            else largest_episode[1],
            "largest_episode_share": (
                None
                if largest_episode is None or total_damage <= 0.0
                else largest_episode[1] / total_damage
            ),
            "horizons": horizon_reports,
        }
    if materialized:
        output["source_stamp"] = materialized[0]["source_stamp"]
        output["opponent_label"] = materialized[0]["opponent_label"]
    return output


def _format(value: float | None) -> str:
    return "-" if value is None else f"{value:.2f}"


def print_report(report: dict[str, object]) -> None:
    print(
        f"[{report.get('opponent_label', 'empty')}] stamp={report.get('source_stamp', '-')} "
        f"events={report['events']}"
    )
    kinds = report["kinds"]
    assert isinstance(kinds, dict)
    for kind in ("dealt", "taken"):
        item = kinds[kind]
        print(
            f"  {kind}: n={item['count']} damage={item['total_damage']:.6g} "
            f"episodes={item['episodes_with_events']} "
            f"max_event_share={_format(item['largest_event_share'])} "
            f"max_episode_share={_format(item['largest_episode_share'])}"
        )
        for horizon, horizon_report in item["horizons"].items():
            print(f"    pre_{horizon}s available={horizon_report['available']}")
            if int(horizon_report["available"]) == 0:
                continue
            for feature in FEATURES:
                stats = horizon_report["features"][feature]
                print(
                    f"      {feature:24s} p10={_format(stats['p10']):>9s} "
                    f"p50={_format(stats['p50']):>9s} p90={_format(stats['p90']):>9s}"
                )


def _parse_horizons(text: str) -> list[float]:
    try:
        values = sorted(
            {float(value.strip()) for value in text.split(",") if value.strip()}
        )
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "horizons must be comma-separated numbers"
        ) from exc
    if not values or values[0] <= 0.0:
        raise argparse.ArgumentTypeError("horizons must be positive")
    return values


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument(
        "--horizons", type=_parse_horizons, default=_parse_horizons("2,5,10")
    )
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    with args.input.open(newline="", encoding="utf-8-sig") as handle:
        report = summarize(csv.DictReader(handle), args.horizons)
    print_report(report)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"  json={args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
