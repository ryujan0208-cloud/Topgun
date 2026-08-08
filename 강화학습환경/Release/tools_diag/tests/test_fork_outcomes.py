from __future__ import annotations

import sys
import unittest
from pathlib import Path


TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

import fork_outcomes as subject  # noqa: E402
import state_dataset  # noqa: E402


def point(time_s: float, health: float) -> state_dataset.TrackPoint:
    return state_dataset.TrackPoint(time_s, 128.0, 37.0, 1000.0, 0.0, 0.0, 0.0, health)


class ForkOutcomesTest(unittest.TestCase):
    def test_local_damage_uses_fork_health_and_horizon(self):
        own = [point(0.0, 1.0), point(1.0, 0.9), point(2.0, 0.8), point(3.0, 0.7)]
        target = [point(0.0, 1.0), point(1.0, 0.95), point(2.0, 0.7), point(3.0, 0.6)]
        result = subject.local_damage(own, target, 1.0, 1.1)
        self.assertAlmostEqual(result["dealt"], 0.25)
        self.assertAlmostEqual(result["taken"], 0.1)
        self.assertAlmostEqual(result["net"], 0.15)

    def test_horizon_must_be_positive(self):
        points = [point(0.0, 1.0)]
        with self.assertRaises(ValueError):
            subject.local_damage(points, points, 0.0, 0.0)


if __name__ == "__main__":
    unittest.main()
