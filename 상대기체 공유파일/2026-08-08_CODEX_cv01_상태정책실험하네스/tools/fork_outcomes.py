# -*- coding: utf-8 -*-
"""Build state-action outcome rows from archived matched-prefix fork cases."""
from __future__ import annotations

import argparse
import bisect
import csv
import json
from pathlib import Path
from typing import Iterable, Sequence

import state_dataset


STATE_FIELDS = (
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


def _track_path(case_dir: Path, stamp: str, role: str) -> Path:
    suffix = "ownship_(F-16)[Blue].csv" if role == "ownship" else "target_(F-16)[Red].csv"
    return case_dir / f"{stamp}_{suffix}"


def _index_at_or_before(points: Sequence[state_dataset.TrackPoint], time_s: float) -> int:
    if not points:
        raise ValueError("empty track")
    times = [point.time for point in points]
    return max(0, bisect.bisect_right(times, time_s + 1e-9) - 1)


def local_damage(
    own: Sequence[state_dataset.TrackPoint],
    target: Sequence[state_dataset.TrackPoint],
    fork_start_s: float,
    horizon_s: float,
) -> dict[str, float]:
    """Health loss after the fork and up to a fixed horizon."""
    if horizon_s <= 0.0:
        raise ValueError("horizon must be positive")
    start = min(
        _index_at_or_before(own, fork_start_s),
        _index_at_or_before(target, fork_start_s),
    )
    end_time = fork_start_s + horizon_s
    own_end = _index_at_or_before(own, end_time)
    target_end = _index_at_or_before(target, end_time)
    taken = own[start].health - own[own_end].health
    dealt = target[start].health - target[target_end].health
    return {"dealt": dealt, "taken": taken, "net": dealt - taken}


def _load_case(case_dir: Path) -> tuple[dict[str, object], list[state_dataset.TrackPoint], list[state_dataset.TrackPoint]]:
    manifest = json.loads((case_dir / "case_manifest.json").read_text(encoding="utf-8"))
    stamp = str(manifest["replay_stamp"])
    own = state_dataset.load_track(_track_path(case_dir, stamp, "ownship"))
    target = state_dataset.load_track(_track_path(case_dir, stamp, "target"))
    return manifest, own, target


def iter_rows(campaign_dirs: Iterable[Path], horizons_s: Sequence[float]) -> Iterable[dict[str, object]]:
    for campaign_dir in campaign_dirs:
        baseline_dir = campaign_dir / "baseline"
        if not baseline_dir.is_dir():
            continue
        baseline_manifest, baseline_own, baseline_target = _load_case(baseline_dir)
        for case_dir in sorted(path for path in campaign_dir.iterdir() if path.is_dir()):
            if case_dir.name == "baseline" or not (case_dir / "case_manifest.json").is_file():
                continue
            manifest, own, target = _load_case(case_dir)
            config = manifest["configuration"]
            fork_start = float(config["fork_start_s"])
            state_index = min(
                _index_at_or_before(baseline_own, fork_start),
                _index_at_or_before(baseline_target, fork_start),
            )
            state = state_dataset._base_features(
                baseline_own, baseline_target, state_index, 6, 0
            )
            prefix = manifest.get("prefix_comparison") or {}
            row: dict[str, object] = {
                "campaign": manifest["campaign"],
                "case_id": manifest["case_id"],
                "candidate": config["candidate"],
                "seed": config["seed"],
                "opponent": config["opponent"],
                "randomized_start": config.get("randomized_start", False),
                "fork_start_s": fork_start,
                "fork_duration_s": config["fork_duration_s"],
                "lead_time_s": config["lead_time_s"],
                "vertical_offset_m": config["vertical_offset_m"],
                "prefix_ok": bool(prefix)
                and all(bool(report["pre_fork_equal"]) for report in prefix.values()),
                "dll_sha256": manifest["provenance"]["dll_sha256"],
                "rule_sha256": manifest["provenance"]["rule_sha256"],
                "replay_stamp": manifest["replay_stamp"],
            }
            row.update({field: state[field] for field in STATE_FIELDS})
            baseline_final = float(baseline_manifest["score"]["net_hp"])
            candidate_final = float(manifest["score"]["net_hp"])
            row["final_net_hp"] = candidate_final
            row["delta_final_net_hp"] = candidate_final - baseline_final
            for horizon in horizons_s:
                key = f"h{horizon:g}s".replace(".", "p")
                base_local = local_damage(
                    baseline_own, baseline_target, fork_start, horizon
                )
                candidate_local = local_damage(own, target, fork_start, horizon)
                for metric in ("dealt", "taken", "net"):
                    row[f"{key}_{metric}_hp"] = candidate_local[metric]
                    row[f"{key}_delta_{metric}_hp"] = (
                        candidate_local[metric] - base_local[metric]
                    )
            yield row


def _parse_horizons(text: str) -> list[float]:
    values = sorted({float(part.strip()) for part in text.split(",") if part.strip()})
    if not values or values[0] <= 0.0:
        raise argparse.ArgumentTypeError("horizons must be positive")
    return values


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--horizons", type=_parse_horizons, default=_parse_horizons("3,5,10,20"))
    args = parser.parse_args()
    rows = list(iter_rows(args.campaign, args.horizons))
    if not rows:
        raise RuntimeError("no candidate fork cases found")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    prefix_failures = sum(not bool(row["prefix_ok"]) for row in rows)
    print(f"wrote {len(rows)} fork outcomes, prefix_failures={prefix_failures}: {args.output}")
    return 1 if prefix_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
