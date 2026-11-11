#!/usr/bin/env python3
"""Regression tests for fail-closed 23-series release readiness.

Run: python -m unittest discover -s tests -p 'test_release_gate.py'
"""
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from verify_23_championship_release import verify

NOW = lambda: datetime.now(timezone.utc).isoformat()

def fixtures():
    names = [f"Series {n:02d}" for n in range(23)]
    detail = {"season": 2026, "generated_at": NOW(), "series": {}}
    summary = {"season": 2026, "generated_at": NOW(), "championships": {},
               "fully_verified_championships": 23, "complete": True}
    for name in names:
        detail["series"][name] = {
            "calendar_available": True, "points_table_available": True,
            "full_race_classifications_available": True,
            "review_record_complete": True, "officially_cross_checked": True,
            "commercial_reuse_cleared": True, "ready_for_release": True,
        }
        summary["championships"][name] = {
            "fully_verified": True,
            "calendar": {"events": 12},
            "championship_points": {"rows": 20},
            "points_freshness": {"status": "no_later_scheduled_round"},
            "individual_race_results": {
                "status": "candidate_classifications_require_round_and_official_review",
                "classified_events": 12, "completed_calendar_events": 12,
                "verification": {
                    "officially_cross_checked": True,
                    "season_scoring_and_adjustments_checked": True,
                    "source_reuse_cleared": True,
                },
            },
        }
    return detail, summary

class ReleaseGateTests(unittest.TestCase):
    def test_complete_evidence_passes_data_gate_only(self):
        self.assertEqual(verify(*fixtures()), [])

    def test_missing_series_fails(self):
        d, s = fixtures()
        d["series"].pop("Series 01")
        self.assertTrue(verify(d, s))

    def test_missing_permissions_fails(self):
        d, s = fixtures()
        d["series"]["Series 01"]["commercial_reuse_cleared"] = False
        self.assertTrue(any("commercial_reuse_cleared" in x for x in verify(d, s)))

    def test_winner_only_fails(self):
        d, s = fixtures()
        s["championships"]["Series 01"]["individual_race_results"]["status"] = "winner_summaries_available_not_full_classifications"
        self.assertTrue(verify(d, s))

    def test_classification_count_mismatch_fails(self):
        d, s = fixtures()
        s["championships"]["Series 01"]["individual_race_results"]["classified_events"] = 11
        self.assertTrue(verify(d, s))

    def test_missing_adjustment_review_fails(self):
        d, s = fixtures()
        s["championships"]["Series 01"]["individual_race_results"]["verification"]["season_scoring_and_adjustments_checked"] = False
        self.assertTrue(verify(d, s))

    def test_stale_standings_fails(self):
        d, s = fixtures()
        s["championships"]["Series 01"]["points_freshness"]["status"] = "potentially_stale_after_scheduled_round"
        self.assertTrue(verify(d, s))

    def test_mismatched_season_fails(self):
        d, s = fixtures()
        s["season"] = 2025
        self.assertTrue(verify(d, s))

    def test_stale_report_fails(self):
        d, s = fixtures()
        d["generated_at"] = "2026-10-01T00:00:00+00:00"
        self.assertTrue(verify(d, s))

if __name__ == "__main__":
    unittest.main()
