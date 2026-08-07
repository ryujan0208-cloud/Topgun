from __future__ import annotations

import sys
import unittest
from pathlib import Path


TOOLS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS_DIR))

import damage_event_report as subject  # noqa: E402


def event(kind: str, episode: int, damage: float, value: float) -> dict[str, str]:
    row = {
        "event_id": f"e{episode}-{damage}",
        "source_stamp": "synthetic",
        "opponent_label": "test",
        "kind": kind,
        "episode": str(episode),
        "damage": str(damage),
        "pre_2s_available": "1",
    }
    for feature in subject.FEATURES:
        row[f"pre_2s_{feature}"] = str(value)
    return row


class DamageEventReportTest(unittest.TestCase):
    def test_reports_largest_event_and_episode_contribution(self):
        rows = [
            event("dealt", 0, 1.0, 0.0),
            event("dealt", 0, 2.0, 10.0),
            event("dealt", 1, 1.0, 20.0),
        ]

        report = subject.summarize(rows, [2.0])
        dealt = report["kinds"]["dealt"]

        self.assertEqual(dealt["count"], 3)
        self.assertAlmostEqual(dealt["largest_event_share"], 0.5)
        self.assertAlmostEqual(dealt["largest_episode_share"], 0.75)
        self.assertEqual(dealt["horizons"]["2"]["features"]["range_m"]["p50"], 10.0)


if __name__ == "__main__":
    unittest.main()
