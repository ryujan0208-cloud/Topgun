# -*- coding: utf-8 -*-
"""Select damage-event states with a checked, parameterized filter."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class FilterSpec:
    history_prefix: str = "pre_2s"
    min_damage: float = 0.01
    min_range_m: float = 800.0
    max_range_m: float = 1300.0
    min_ata_deg: float = 25.0
    max_ata_deg: float = 55.0
    max_abs_los_az_deg: float = 12.0
    min_los_el_deg: float = 25.0
    max_los_el_deg: float = 55.0
    min_vertical_speed_mps: float = 80.0

    def validate(self) -> None:
        if self.min_damage < 0.0:
            raise ValueError("minimum damage must be non-negative")
        if self.min_range_m > self.max_range_m:
            raise ValueError("range bounds are reversed")
        if self.min_ata_deg > self.max_ata_deg:
            raise ValueError("ATA bounds are reversed")
        if self.max_abs_los_az_deg < 0.0:
            raise ValueError("absolute LOS azimuth limit must be non-negative")
        if self.min_los_el_deg > self.max_los_el_deg:
            raise ValueError("LOS elevation bounds are reversed")


def required_columns(prefix: str) -> tuple[str, ...]:
    return (
        "event_id",
        "kind",
        "start_time_s",
        "damage",
        f"{prefix}_available",
        f"{prefix}_time_s",
        f"{prefix}_range_m",
        f"{prefix}_own_ata_deg",
        f"{prefix}_own_los_az_deg",
        f"{prefix}_own_los_el_deg",
        f"{prefix}_own_vertical_speed_mps",
    )


def check_schema(fieldnames: Iterable[str] | None, prefix: str) -> None:
    present = set(fieldnames or ())
    missing = [name for name in required_columns(prefix) if name not in present]
    if missing:
        raise ValueError(f"missing required event columns: {missing}")


def _number(row: dict[str, str], name: str) -> float:
    value = row[name]
    if value == "":
        event_id = row.get("event_id", "?")
        raise ValueError(f"empty numeric field {name} in {event_id}")
    return float(value)


def evaluate(row: dict[str, str], spec: FilterSpec) -> dict[str, object]:
    p = spec.history_prefix
    available = row[f"{p}_available"] == "1"
    result: dict[str, object] = {
        "event_id": row["event_id"],
        "event_time_s": _number(row, "start_time_s"),
        "fork_time_s": row[f"{p}_time_s"],
        "damage_hp": _number(row, "damage"),
        "history_available": available,
        "range_m": row[f"{p}_range_m"],
        "own_ata_deg": row[f"{p}_own_ata_deg"],
        "own_los_az_deg": row[f"{p}_own_los_az_deg"],
        "own_los_el_deg": row[f"{p}_own_los_el_deg"],
        "own_vertical_speed_mps": row[f"{p}_own_vertical_speed_mps"],
        "damage_ok": False,
        "range_ok": False,
        "ata_ok": False,
        "los_az_ok": False,
        "los_el_ok": False,
        "vertical_speed_ok": False,
    }
    if row["kind"] != "dealt" or not available:
        result["matches_filter"] = False
        return result
    damage = float(result["damage_hp"])
    distance = _number(row, f"{p}_range_m")
    ata = _number(row, f"{p}_own_ata_deg")
    los_az = _number(row, f"{p}_own_los_az_deg")
    los_el = _number(row, f"{p}_own_los_el_deg")
    vertical_speed = _number(row, f"{p}_own_vertical_speed_mps")
    predicates = {
        "damage_ok": damage >= spec.min_damage,
        "range_ok": spec.min_range_m <= distance <= spec.max_range_m,
        "ata_ok": spec.min_ata_deg <= ata <= spec.max_ata_deg,
        "los_az_ok": abs(los_az) <= spec.max_abs_los_az_deg,
        "los_el_ok": spec.min_los_el_deg <= los_el <= spec.max_los_el_deg,
        "vertical_speed_ok": vertical_speed >= spec.min_vertical_speed_mps,
    }
    result.update(predicates)
    result["matches_filter"] = all(predicates.values())
    return result


def _labelled_path(text: str) -> tuple[str, Path]:
    label, separator, raw_path = text.partition("=")
    if not separator or not label or not raw_path:
        raise argparse.ArgumentTypeError("input must be LABEL=PATH")
    return label, Path(raw_path)


def _bounds(text: str) -> tuple[float, float]:
    try:
        lower, upper = (float(part.strip()) for part in text.split(",", 1))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("bounds must be MIN,MAX") from exc
    if lower > upper:
        raise argparse.ArgumentTypeError("bounds are reversed")
    return lower, upper


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", action="append", type=_labelled_path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--history-prefix", default="pre_2s")
    parser.add_argument("--min-damage", type=float, default=0.01)
    parser.add_argument("--range-m", type=_bounds, default=(800.0, 1300.0))
    parser.add_argument("--ata-deg", type=_bounds, default=(25.0, 55.0))
    parser.add_argument("--max-abs-los-az-deg", type=float, default=12.0)
    parser.add_argument("--los-el-deg", type=_bounds, default=(25.0, 55.0))
    parser.add_argument("--min-own-vertical-speed-mps", type=float, default=80.0)
    args = parser.parse_args()
    spec = FilterSpec(
        history_prefix=args.history_prefix,
        min_damage=args.min_damage,
        min_range_m=args.range_m[0],
        max_range_m=args.range_m[1],
        min_ata_deg=args.ata_deg[0],
        max_ata_deg=args.ata_deg[1],
        max_abs_los_az_deg=args.max_abs_los_az_deg,
        min_los_el_deg=args.los_el_deg[0],
        max_los_el_deg=args.los_el_deg[1],
        min_vertical_speed_mps=args.min_own_vertical_speed_mps,
    )
    spec.validate()
    output_rows: list[dict[str, object]] = []
    selected = False
    for label, path in args.input:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            check_schema(reader.fieldnames, spec.history_prefix)
            source_rows = [row for row in reader if row["kind"] == "dealt"]
        source_rows.sort(key=lambda row: float(row["start_time_s"]))
        for row in source_rows:
            result = {"source_label": label, **evaluate(row, spec)}
            result["selected"] = bool(result["matches_filter"]) and not selected
            selected = selected or bool(result["selected"])
            output_rows.append(result)
    if not output_rows:
        raise RuntimeError("no dealt events found")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output_rows[0]))
        writer.writeheader()
        writer.writerows(output_rows)
    match_count = sum(bool(row["matches_filter"]) for row in output_rows)
    print(
        f"wrote {len(output_rows)} dealt events, matches={match_count}, "
        f"selected={int(selected)}: {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
