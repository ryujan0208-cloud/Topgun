from __future__ import annotations

import sys
import unittest
from pathlib import Path


TOOLS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS_DIR))

import select_damage_events as subject  # noqa: E402


def event_row(**updates: str) -> dict[str, str]:
    row = {
        "event_id": "synthetic:e0:dealt:1",
        "kind": "dealt",
        "start_time_s": "12.0",
        "damage": "0.02",
        "pre_2s_available": "1",
        "pre_2s_time_s": "10.0",
        "pre_2s_range_m": "900.0",
        "pre_2s_own_ata_deg": "30.0",
        "pre_2s_own_los_az_deg": "-3.0",
        "pre_2s_own_los_el_deg": "35.0",
        "pre_2s_own_vertical_speed_mps": "90.0",
    }
    row.update(updates)
    return row


class SelectDamageEventsTest(unittest.TestCase):
    def test_matching_event_uses_signed_los_columns(self):
        row = event_row()
        subject.check_schema(row, "pre_2s")

        result = subject.evaluate(row, subject.FilterSpec())

        self.assertTrue(result["matches_filter"])
        self.assertEqual(result["fork_time_s"], "10.0")
        self.assertEqual(result["own_los_az_deg"], "-3.0")

    def test_missing_los_column_fails_instead_of_becoming_zero(self):
        row = event_row()
        del row["pre_2s_own_los_el_deg"]

        with self.assertRaisesRegex(ValueError, "own_los_el_deg"):
            subject.check_schema(row, "pre_2s")

    def test_each_bound_contributes_to_decision(self):
        result = subject.evaluate(
            event_row(pre_2s_own_vertical_speed_mps="79.99"),
            subject.FilterSpec(),
        )

        self.assertFalse(result["vertical_speed_ok"])
        self.assertFalse(result["matches_filter"])
