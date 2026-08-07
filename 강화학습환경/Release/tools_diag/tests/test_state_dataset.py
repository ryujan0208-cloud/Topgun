from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path


TOOLS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS_DIR))

import state_dataset as subject  # noqa: E402


def point(time: float, lon: float, lat: float, yaw: float, health: float = 1.0):
    return subject.TrackPoint(time, lon, lat, 1_000.0, 0.0, 0.0, yaw, health)


class StateDatasetTest(unittest.TestCase):
    def test_head_on_geometry(self):
        north_1km_deg = 1_000.0 / subject.EARTH_M_PER_DEG
        own = [point(0.0, 128.0, 37.0, 0.0)]
        target = [point(0.0, 128.0, 37.0 + north_1km_deg, 180.0)]

        features = subject._base_features(own, target, 0, 1)

        self.assertAlmostEqual(features["range_m"], 1_000.0, delta=0.5)
        self.assertAlmostEqual(features["own_ata_deg"], 0.0, delta=1e-6)
        self.assertAlmostEqual(features["target_ata_deg"], 0.0, delta=1e-6)
        self.assertAlmostEqual(features["relative_heading_deg"], 180.0, delta=1e-6)

    def test_future_damage_labels_do_not_cross_episode(self):
        own = [
            point(0.0, 128.0, 37.0, 0.0),
            point(1.0, 128.0, 37.0, 0.0, 0.9),
            point(0.0, 128.1, 37.1, 0.0),
            point(1.0, 128.1, 37.1, 0.0),
        ]
        target = [
            point(0.0, 128.0, 37.001, 180.0),
            point(1.0, 128.0, 37.001, 180.0, 0.8),
            point(0.0, 128.1, 37.101, 180.0),
            point(1.0, 128.1, 37.101, 180.0),
        ]

        rows = list(subject.iter_rows(own, target, [1.0], 1.0, 1, 2_000.0))

        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[0]["h1_available"], 1)
        self.assertAlmostEqual(rows[0]["h1_dealt"], 0.2)
        self.assertAlmostEqual(rows[0]["h1_taken"], 0.1)
        self.assertEqual(rows[1]["h1_available"], 0)
        self.assertEqual(rows[2]["episode"], 1)
        self.assertEqual(rows[2]["h1_available"], 1)

    def test_closure_is_positive_when_range_decreases(self):
        north_1km_deg = 1_000.0 / subject.EARTH_M_PER_DEG
        north_900m_deg = 900.0 / subject.EARTH_M_PER_DEG
        own = [point(0.0, 128.0, 37.0, 0.0), point(1.0, 128.0, 37.0, 0.0)]
        target = [
            point(0.0, 128.0, 37.0 + north_1km_deg, 180.0),
            point(1.0, 128.0, 37.0 + north_900m_deg, 180.0),
        ]

        features = subject._base_features(own, target, 1, 1)

        self.assertTrue(math.isfinite(features["closure_mps"]))
        self.assertAlmostEqual(features["closure_mps"], 100.0, delta=0.5)

    def test_derivative_does_not_cross_episode_boundary(self):
        own = [
            point(0.0, 128.0, 37.0, 0.0),
            point(1.0, 128.0, 37.0, 0.0),
            point(0.0, 129.0, 38.0, 0.0),
        ]
        target = [
            point(0.0, 128.0, 37.001, 180.0),
            point(1.0, 128.0, 37.001, 180.0),
            point(0.0, 129.0, 38.001, 180.0),
        ]

        features = subject._base_features(own, target, 2, 1, start_index=2)

        self.assertEqual(features["own_speed_mps"], 0.0)
        self.assertEqual(features["target_speed_mps"], 0.0)


if __name__ == "__main__":
    unittest.main()
