from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np


RELEASE_DIR = Path(__file__).resolve().parents[2]
EXPERIMENT_DIR = RELEASE_DIR / "experiments" / "state_policy"
sys.path.insert(0, str(EXPERIMENT_DIR))

import prefix_fork as subject  # noqa: E402


class PrefixForkTest(unittest.TestCase):
    def test_ned_position_is_converted_to_neu(self):
        state = np.zeros(51)
        state[0:3] = [100.0, 200.0, -3_000.0]

        np.testing.assert_allclose(
            subject.neu_position(state), [100.0, 200.0, 3_000.0]
        )

    def test_candidate_vp_has_interpretable_offsets(self):
        position = np.array([100.0, 200.0, 3_000.0])
        velocity = np.array([10.0, -5.0, 2.0])

        np.testing.assert_allclose(
            subject.candidate_vp("lead", position, velocity, 2.0, 500.0),
            [120.0, 190.0, 3_004.0],
        )
        np.testing.assert_allclose(
            subject.candidate_vp("up", position, velocity, 2.0, 500.0),
            [100.0, 200.0, 3_500.0],
        )
        np.testing.assert_allclose(
            subject.candidate_vp("down", position, velocity, 2.0, 500.0),
            [100.0, 200.0, 2_500.0],
        )


if __name__ == "__main__":
    unittest.main()
