# -*- coding: utf-8 -*-
"""Extract independent health-loss bursts and their preceding combat states.

Damage ticks close in time are grouped into one event.  Each output row keeps
the exact episode and source-row indices needed to inspect or replay the scene.
The extracted states are observational evidence, not counterfactual action
values.
"""
from __future__ import annotations

import argparse
import bisect
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import state_dataset


STATE_FEATURES = (
    "phase",
    "range_m",
    "own_ata_deg",
    "target_ata_deg",
    "relative_heading_deg",
    "closure_mps",
    "altitude_delta_m",
    "own_altitude_m",
    "target_altitude_m",
    "own_floor_margin_m",
    "target_floor_margin_m",
    "own_speed_mps",
    "target_speed_mps",
    "speed_delta_mps",
    "own_vertical_speed_mps",
    "target_vertical_speed_mps",
    "own_turn_rate_dps",
    "target_turn_rate_dps",
    "energy_height_delta_m",
    "own_roll_deg",
    "own_pitch_deg",
    "target_roll_deg",
    "target_pitch_deg",
    "own_health",
    "target_health",
    "health_advantage",
)


@dataclass(frozen=True)
class DamageEvent:
    episode: int
    kind: str
    start_index: int
    end_index: int
    start_time_s: float
    end_time_s: float
    damage: float
    damage_ticks: int


def group_damage_events(
    points: Sequence[state_dataset.TrackPoint],
    episode: int,
    start: int,
    end: int,
    kind: str,
    merge_gap_s: float,
    epsilon: float = 1e-9,
) -> list[DamageEvent]:
    """Group positive health drops inside one episode into damage bursts."""
    if merge_gap_s < 0.0:
        raise ValueError("merge_gap_s must be non-negative")
    if epsilon < 0.0:
        raise ValueError("epsilon must be non-negative")
    if not 0 <= start <= end <= len(points):
        raise ValueError("invalid episode range")

    events: list[DamageEvent] = []
    first_index: int | None = None
    last_index: int | None = None
    total_damage = 0.0
    tick_count = 0

    def finish() -> None:
        nonlocal first_index, last_index, total_damage, tick_count
        if first_index is None or last_index is None:
            return
        events.append(
            DamageEvent(
                episode=episode,
                kind=kind,
                start_index=first_index,
                end_index=last_index,
                start_time_s=points[first_index].time,
                end_time_s=points[last_index].time,
                damage=total_damage,
                damage_ticks=tick_count,
            )
        )
        first_index = None
        last_index = None
        total_damage = 0.0
        tick_count = 0

    for index in range(start + 1, end):
        loss = points[index - 1].health - points[index].health
        if loss <= epsilon:
            continue
        if last_index is not None and points[index].time - points[last_index].time > merge_gap_s:
            finish()
        if first_index is None:
            first_index = index
        last_index = index
        total_damage += loss
        tick_count += 1
    finish()
    return events


def _horizon_key(horizon_s: float) -> str:
    return f"pre_{horizon_s:g}s".replace(".", "p")


def _history_index(
    times: Sequence[float],
    episode_start: int,
    anchor_index: int,
    target_time: float,
) -> int | None:
    if target_time < times[episode_start] - 1e-9:
        return None
    index = bisect.bisect_right(
        times, target_time + 1e-9, lo=episode_start, hi=anchor_index + 1
    ) - 1
    return index if index >= episode_start else None


def _add_state(
    row: dict[str, object],
    prefix: str,
    features: dict[str, float | str] | None,
    row_index: int | None,
    event_time_s: float,
) -> None:
    row[f"{prefix}_available"] = int(features is not None)
    row[f"{prefix}_row_index"] = "" if row_index is None else row_index
    row[f"{prefix}_time_s"] = "" if features is None else features["time_s"]
    row[f"{prefix}_lead_time_s"] = (
        "" if features is None else event_time_s - float(features["time_s"])
    )
    for name in STATE_FEATURES:
        row[f"{prefix}_{name}"] = "" if features is None else features[name]


def iter_event_rows(
    own: Sequence[state_dataset.TrackPoint],
    target: Sequence[state_dataset.TrackPoint],
    horizons_s: Sequence[float],
    derivative_window: int,
    jump_threshold_m: float,
    merge_gap_s: float,
    damage_epsilon: float,
    stamp: str,
    label: str,
) -> Iterable[dict[str, object]]:
    """Yield one row per dealt or taken damage event."""
    if derivative_window < 1:
        raise ValueError("derivative_window must be >= 1")
    horizons = sorted({float(value) for value in horizons_s})
    if not horizons or horizons[0] <= 0.0:
        raise ValueError("horizons must be positive")

    count = min(len(own), len(target))
    own_times = [point.time for point in own[:count]]
    ranges = state_dataset.episode_ranges(own, target, jump_threshold_m)
    serial = 0
    for episode, (start, end) in enumerate(ranges):
        events = group_damage_events(
            target, episode, start, end, "dealt", merge_gap_s, damage_epsilon
        )
        events.extend(
            group_damage_events(
                own, episode, start, end, "taken", merge_gap_s, damage_epsilon
            )
        )
        events.sort(key=lambda event: (event.start_index, event.kind))
        for event in events:
            serial += 1
            anchor_index = max(start, event.start_index - 1)
            row: dict[str, object] = {
                "event_id": f"{stamp}:e{episode}:{event.kind}:{event.start_index}",
                "event_serial": serial,
                "source_stamp": stamp,
                "opponent_label": label,
                "episode": episode,
                "kind": event.kind,
                "start_row_index": event.start_index,
                "end_row_index": event.end_index,
                "start_time_s": event.start_time_s,
                "end_time_s": event.end_time_s,
                "duration_s": event.end_time_s - event.start_time_s,
                "damage": event.damage,
                "damage_ticks": event.damage_ticks,
            }
            anchor_features = state_dataset._base_features(
                own, target, anchor_index, derivative_window, start
            )
            _add_state(row, "anchor", anchor_features, anchor_index, event.start_time_s)
            for horizon in horizons:
                prefix = _horizon_key(horizon)
                history_index = _history_index(
                    own_times,
                    start,
                    anchor_index,
                    event.start_time_s - horizon,
                )
                features = (
                    None
                    if history_index is None
                    else state_dataset._base_features(
                        own, target, history_index, derivative_window, start
                    )
                )
                _add_state(row, prefix, features, history_index, event.start_time_s)
            yield row


def _parse_horizons(text: str) -> list[float]:
    try:
        horizons = sorted({float(value.strip()) for value in text.split(",") if value.strip()})
    except ValueError as exc:
        raise argparse.ArgumentTypeError("horizons must be comma-separated numbers") from exc
    if not horizons or horizons[0] <= 0.0:
        raise argparse.ArgumentTypeError("horizons must be positive")
    return horizons


def _fieldnames(horizons_s: Sequence[float]) -> list[str]:
    fixed = [
        "event_id",
        "event_serial",
        "source_stamp",
        "opponent_label",
        "episode",
        "kind",
        "start_row_index",
        "end_row_index",
        "start_time_s",
        "end_time_s",
        "duration_s",
        "damage",
        "damage_ticks",
    ]
    state_fields: list[str] = []
    for prefix in ["anchor", *(_horizon_key(value) for value in horizons_s)]:
        state_fields.extend(
            [
                f"{prefix}_available",
                f"{prefix}_row_index",
                f"{prefix}_time_s",
                f"{prefix}_lead_time_s",
                *(f"{prefix}_{name}" for name in STATE_FEATURES),
            ]
        )
    return fixed + state_fields


def write_events(
    path: Path, rows: Iterable[dict[str, object]], horizons_s: Sequence[float]
) -> tuple[int, dict[str, int], dict[str, float]]:
    path.parent.mkdir(parents=True, exist_ok=True)
    counts = {"dealt": 0, "taken": 0}
    damage = {"dealt": 0.0, "taken": 0.0}
    total = 0
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=_fieldnames(horizons_s), extrasaction="raise")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
            kind = str(row["kind"])
            counts[kind] += 1
            damage[kind] += float(row["damage"])
            total += 1
    return total, counts, damage


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--logdir", type=Path, required=True)
    parser.add_argument("--stamp", required=True)
    parser.add_argument("--label", default="run")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--horizons", type=_parse_horizons, default=_parse_horizons("2,5,10"))
    parser.add_argument("--derivative-window", type=int, default=6)
    parser.add_argument("--jump-threshold-m", type=float, default=2_000.0)
    parser.add_argument("--merge-gap-s", type=float, default=0.5)
    parser.add_argument("--damage-epsilon", type=float, default=1e-9)
    args = parser.parse_args()

    own = state_dataset.load_track(
        args.logdir / f"{args.stamp}_ownship_(F-16)[Blue].csv"
    )
    target = state_dataset.load_track(
        args.logdir / f"{args.stamp}_target_(F-16)[Red].csv"
    )
    rows = iter_event_rows(
        own,
        target,
        args.horizons,
        args.derivative_window,
        args.jump_threshold_m,
        args.merge_gap_s,
        args.damage_epsilon,
        args.stamp,
        args.label,
    )
    total, counts, damage = write_events(args.output, rows, args.horizons)
    print(
        f"wrote {total} events: dealt={counts['dealt']} ({damage['dealt']:.6g} HP), "
        f"taken={counts['taken']} ({damage['taken']:.6g} HP): {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
