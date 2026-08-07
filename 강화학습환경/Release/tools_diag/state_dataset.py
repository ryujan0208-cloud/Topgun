# -*- coding: utf-8 -*-
"""Create relative-state snapshots and future labels from paired fight logs.

This is an observational data tool. It deliberately does not infer that the
recorded action caused a future result. Counterfactual action value requires a
reproducible replay/fork of simulator and native policy state.
"""
from __future__ import annotations

import argparse
import bisect
import csv
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import wez_rule


EARTH_M_PER_DEG = 111_320.0
G = 9.80665


@dataclass(frozen=True)
class TrackPoint:
    time: float
    lon: float
    lat: float
    alt: float
    roll: float
    pitch: float
    yaw: float
    health: float


def _finite(value: str, name: str, path: Path, row_number: int) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"non-finite {name} in {path}:{row_number}")
    return number


def load_track(path: Path) -> list[TrackPoint]:
    points: list[TrackPoint] = []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        required = {
            "Time",
            "Longitude",
            "Latitude",
            "Altitude",
            "Roll (deg)",
            "Pitch (deg)",
            "Yaw (deg)",
            "Health",
        }
        missing = required.difference(reader.fieldnames or ())
        if missing:
            raise ValueError(f"missing columns in {path}: {sorted(missing)}")
        for row_number, row in enumerate(reader, start=2):
            points.append(
                TrackPoint(
                    time=_finite(row["Time"], "Time", path, row_number),
                    lon=_finite(row["Longitude"], "Longitude", path, row_number),
                    lat=_finite(row["Latitude"], "Latitude", path, row_number),
                    alt=_finite(row["Altitude"], "Altitude", path, row_number),
                    roll=_finite(row["Roll (deg)"], "Roll", path, row_number),
                    pitch=_finite(row["Pitch (deg)"], "Pitch", path, row_number),
                    yaw=_finite(row["Yaw (deg)"], "Yaw", path, row_number),
                    health=_finite(row["Health"], "Health", path, row_number),
                )
            )
    if not points:
        raise ValueError(f"empty track: {path}")
    return points


def _forward(point: TrackPoint) -> tuple[float, float, float]:
    yaw = math.radians(point.yaw)
    pitch = math.radians(point.pitch)
    cp = math.cos(pitch)
    return math.sin(yaw) * cp, math.cos(yaw) * cp, math.sin(pitch)


def _relative_enu(
    origin: TrackPoint, target: TrackPoint
) -> tuple[float, float, float]:
    mean_lat = math.radians((origin.lat + target.lat) * 0.5)
    east = (target.lon - origin.lon) * EARTH_M_PER_DEG * math.cos(mean_lat)
    north = (target.lat - origin.lat) * EARTH_M_PER_DEG
    up = target.alt - origin.alt
    return east, north, up


def _norm(vector: Sequence[float]) -> float:
    return math.sqrt(sum(value * value for value in vector))


def _dot(a: Sequence[float], b: Sequence[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _angle_deg(a: Sequence[float], b: Sequence[float]) -> float:
    denom = _norm(a) * _norm(b)
    if denom <= 1e-9:
        return 0.0
    cosine = max(-1.0, min(1.0, _dot(a, b) / denom))
    return math.degrees(math.acos(cosine))


def _wrap_delta_deg(new: float, old: float) -> float:
    return (new - old + 180.0) % 360.0 - 180.0


def _velocity(
    points: Sequence[TrackPoint], index: int, window: int, start_index: int = 0
) -> tuple[float, float, float]:
    previous = max(start_index, index - window)
    dt = points[index].time - points[previous].time
    if dt <= 1e-6:
        return 0.0, 0.0, 0.0
    displacement = _relative_enu(points[previous], points[index])
    return tuple(component / dt for component in displacement)


def _turn_rate(
    points: Sequence[TrackPoint], index: int, window: int, start_index: int = 0
) -> float:
    previous = max(start_index, index - window)
    dt = points[index].time - points[previous].time
    if dt <= 1e-6:
        return 0.0
    return _wrap_delta_deg(points[index].yaw, points[previous].yaw) / dt


def _position_jump(a: TrackPoint, b: TrackPoint) -> float:
    return _norm(_relative_enu(a, b))


def episode_ranges(
    own: Sequence[TrackPoint],
    target: Sequence[TrackPoint],
    jump_threshold_m: float,
) -> list[tuple[int, int]]:
    count = min(len(own), len(target))
    starts = [0]
    for index in range(1, count):
        time_rewound = own[index].time <= own[index - 1].time or target[index].time <= target[index - 1].time
        jumped = (
            _position_jump(own[index - 1], own[index]) > jump_threshold_m
            or _position_jump(target[index - 1], target[index]) > jump_threshold_m
        )
        if time_rewound or jumped:
            starts.append(index)
    return list(zip(starts, starts[1:] + [count]))


def _phase_name(time_s: float) -> str:
    active = wez_rule.active(time_s)
    return active[-1]["name"] if active else "NONE"


def _base_features(
    own: Sequence[TrackPoint],
    target: Sequence[TrackPoint],
    index: int,
    derivative_window: int,
    start_index: int = 0,
) -> dict[str, float | str]:
    my = own[index]
    opponent = target[index]
    los = _relative_enu(my, opponent)
    reverse_los = tuple(-value for value in los)
    distance = _norm(los)
    my_forward = _forward(my)
    opponent_forward = _forward(opponent)
    my_velocity = _velocity(own, index, derivative_window, start_index)
    opponent_velocity = _velocity(target, index, derivative_window, start_index)
    relative_velocity = tuple(t - o for o, t in zip(my_velocity, opponent_velocity))
    range_rate = _dot(los, relative_velocity) / max(distance, 1e-9)
    my_speed = _norm(my_velocity)
    opponent_speed = _norm(opponent_velocity)

    return {
        "time_s": my.time,
        "phase": _phase_name(my.time),
        "range_m": distance,
        "own_ata_deg": _angle_deg(my_forward, los),
        "target_ata_deg": _angle_deg(opponent_forward, reverse_los),
        "relative_heading_deg": _angle_deg(my_forward, opponent_forward),
        "closure_mps": -range_rate,
        "altitude_delta_m": opponent.alt - my.alt,
        "own_altitude_m": my.alt,
        "target_altitude_m": opponent.alt,
        "own_floor_margin_m": my.alt - 300.0,
        "target_floor_margin_m": opponent.alt - 300.0,
        "own_speed_mps": my_speed,
        "target_speed_mps": opponent_speed,
        "speed_delta_mps": opponent_speed - my_speed,
        "own_vertical_speed_mps": my_velocity[2],
        "target_vertical_speed_mps": opponent_velocity[2],
        "own_turn_rate_dps": _turn_rate(own, index, derivative_window, start_index),
        "target_turn_rate_dps": _turn_rate(target, index, derivative_window, start_index),
        "energy_height_delta_m": (
            opponent.alt + opponent_speed * opponent_speed / (2.0 * G)
            - my.alt
            - my_speed * my_speed / (2.0 * G)
        ),
        "own_roll_deg": my.roll,
        "own_pitch_deg": my.pitch,
        "target_roll_deg": opponent.roll,
        "target_pitch_deg": opponent.pitch,
        "own_health": my.health,
        "target_health": opponent.health,
        "health_advantage": my.health - opponent.health,
    }


def _future_index(times: Sequence[float], index: int, horizon_s: float, end: int) -> int | None:
    future = bisect.bisect_left(times, times[index] + horizon_s, lo=index + 1, hi=end)
    return future if future < end else None


def iter_rows(
    own: Sequence[TrackPoint],
    target: Sequence[TrackPoint],
    horizons_s: Sequence[float],
    sample_hz: float,
    derivative_window: int,
    jump_threshold_m: float,
) -> Iterable[dict[str, float | int | str]]:
    if sample_hz <= 0.0:
        raise ValueError("sample_hz must be positive")
    times = [point.time for point in own[: min(len(own), len(target))]]
    for episode, (start, end) in enumerate(episode_ranges(own, target, jump_threshold_m)):
        next_sample_time = own[start].time
        for index in range(start, end):
            if own[index].time + 1e-9 < next_sample_time:
                continue
            row: dict[str, float | int | str] = {"episode": episode, "row_index": index}
            row.update(_base_features(own, target, index, derivative_window, start))
            for horizon in horizons_s:
                label = f"h{horizon:g}"
                future = _future_index(times, index, horizon, end)
                if future is None:
                    row[f"{label}_available"] = 0
                    row[f"{label}_dealt"] = ""
                    row[f"{label}_taken"] = ""
                    row[f"{label}_net"] = ""
                    row[f"{label}_range_m"] = ""
                    row[f"{label}_own_ata_deg"] = ""
                    row[f"{label}_target_ata_deg"] = ""
                    row[f"{label}_health_advantage"] = ""
                    continue
                future_features = _base_features(own, target, future, derivative_window, start)
                dealt = target[index].health - target[future].health
                taken = own[index].health - own[future].health
                row[f"{label}_available"] = 1
                row[f"{label}_dealt"] = dealt
                row[f"{label}_taken"] = taken
                row[f"{label}_net"] = dealt - taken
                row[f"{label}_range_m"] = future_features["range_m"]
                row[f"{label}_own_ata_deg"] = future_features["own_ata_deg"]
                row[f"{label}_target_ata_deg"] = future_features["target_ata_deg"]
                row[f"{label}_health_advantage"] = future_features["health_advantage"]
            yield row
            next_sample_time = own[index].time + 1.0 / sample_hz


def _parse_horizons(text: str) -> list[float]:
    horizons = sorted({float(value.strip()) for value in text.split(",") if value.strip()})
    if not horizons or horizons[0] <= 0.0:
        raise argparse.ArgumentTypeError("horizons must be positive comma-separated seconds")
    return horizons


def _write_rows(path: Path, rows: Iterable[dict[str, object]]) -> int:
    iterator = iter(rows)
    try:
        first = next(iterator)
    except StopIteration as exc:
        raise ValueError("no dataset rows were produced") from exc
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(first)
    count = 0
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="raise")
        writer.writeheader()
        writer.writerow(first)
        count += 1
        for row in iterator:
            writer.writerow(row)
            count += 1
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--logdir", type=Path, required=True)
    parser.add_argument("--stamp", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--horizons", type=_parse_horizons, default=_parse_horizons("2,5,10,20"))
    parser.add_argument("--sample-hz", type=float, default=10.0)
    parser.add_argument("--derivative-window", type=int, default=6)
    parser.add_argument("--jump-threshold-m", type=float, default=2_000.0)
    args = parser.parse_args()

    own_path = args.logdir / f"{args.stamp}_ownship_(F-16)[Blue].csv"
    target_path = args.logdir / f"{args.stamp}_target_(F-16)[Red].csv"
    own = load_track(own_path)
    target = load_track(target_path)
    if args.derivative_window < 1:
        parser.error("--derivative-window must be >= 1")
    count = _write_rows(
        args.output,
        iter_rows(
            own,
            target,
            args.horizons,
            args.sample_hz,
            args.derivative_window,
            args.jump_threshold_m,
        ),
    )
    episodes = len(episode_ranges(own, target, args.jump_threshold_m))
    print(f"wrote {count} rows from {episodes} episode(s): {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
