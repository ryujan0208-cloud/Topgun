from __future__ import annotations

import sys
import unittest
from pathlib import Path


TOOLS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS_DIR))

import damage_events as subject  # noqa: E402
import state_dataset  # noqa: E402


def point(time: float, north_m: float, yaw: float, health: float = 1.0):
    return state_dataset.TrackPoint(
        time,
        128.0,
        37.0 + north_m / state_dataset.EARTH_M_PER_DEG,
        1_000.0,
        0.0,
        0.0,
        yaw,
        health,
    )


class DamageEventsTest(unittest.TestCase):
    def test_groups_nearby_damage_ticks_and_splits_later_burst(self):
        track = [
            point(0.0, 0.0, 0.0, 1.00),
            point(0.1, 0.0, 0.0, 0.99),
            point(0.2, 0.0, 0.0, 0.98),
            point(0.8, 0.0, 0.0, 0.98),
            point(1.0, 0.0, 0.0, 0.97),
        ]

        events = subject.group_damage_events(track, 0, 0, len(track), "taken", 0.5)

        self.assertEqual(len(events), 2)
        self.assertEqual((events[0].start_index, events[0].end_index), (1, 2))
        self.assertEqual(events[0].damage_ticks, 2)
        self.assertAlmostEqual(events[0].damage, 0.02)
        self.assertEqual((events[1].start_index, events[1].end_index), (4, 4))

    def test_episode_boundary_health_reset_is_not_damage(self):
        track = [
            point(0.0, 0.0, 0.0, 1.0),
            point(1.0, 0.0, 0.0, 0.9),
            point(0.0, 10_000.0, 0.0, 0.5),
            point(1.0, 10_000.0, 0.0, 0.4),
        ]

        first = subject.group_damage_events(track, 0, 0, 2, "taken", 0.5)
        second = subject.group_damage_events(track, 1, 2, 4, "taken", 0.5)

        self.assertEqual(len(first), 1)
        self.assertEqual(len(second), 1)
        self.assertAlmostEqual(first[0].damage, 0.1)
        self.assertAlmostEqual(second[0].damage, 0.1)

    def test_extracts_exact_pre_event_indices_without_crossing_episode(self):
        own = [point(float(index), 0.0, 0.0) for index in range(14)]
        target_health = [1.0] * 12 + [0.9, 0.9]
        target = [
            point(float(index), 1_000.0, 180.0, target_health[index])
            for index in range(14)
        ]

        rows = list(
            subject.iter_event_rows(
                own,
                target,
                [2.0, 5.0, 10.0],
                derivative_window=1,
                jump_threshold_m=2_000.0,
                merge_gap_s=0.5,
                damage_epsilon=1e-9,
                stamp="synthetic",
                label="test",
            )
        )

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["kind"], "dealt")
        self.assertEqual(row["start_row_index"], 12)
        self.assertEqual(row["anchor_row_index"], 11)
        self.assertEqual(row["pre_2s_row_index"], 10)
        self.assertEqual(row["pre_5s_row_index"], 7)
        self.assertEqual(row["pre_10s_row_index"], 2)
        self.assertAlmostEqual(row["pre_10s_lead_time_s"], 10.0)

    def test_unavailable_history_is_blank(self):
        own = [point(0.0, 0.0, 0.0), point(1.0, 0.0, 0.0)]
        target = [
            point(0.0, 1_000.0, 180.0, 1.0),
            point(1.0, 1_000.0, 180.0, 0.9),
        ]

        row = next(
            iter(
                subject.iter_event_rows(
                    own,
                    target,
                    [2.0],
                    1,
                    2_000.0,
                    0.5,
                    1e-9,
                    "synthetic",
                    "test",
                )
            )
        )

        self.assertEqual(row["pre_2s_available"], 0)
        self.assertEqual(row["pre_2s_row_index"], "")


if __name__ == "__main__":
    unittest.main()
