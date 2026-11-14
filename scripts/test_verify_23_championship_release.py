#!/usr/bin/env python3
"""Regression tests for the 23-series fail-closed release gate."""
import copy
import unittest
from datetime import datetime, timezone
from verify_23_championship_release import verify

NOW = datetime.now(timezone.utc).isoformat()
def fixtures():
    series = {}
    summaries = {}
    for i in range(23):
        name = f"Test Series {i:02d}"
        series[name] = {
            "calendar_available": True, "points_table_available": True,
            "full_race_classifications_available": True,
            "review_record_complete": True, "officially_cross_checked": True,
            "commercial_reuse_cleared": True, "ready_for_release": True,
            "calendar_events": 3, "completed_calendar_events": 2,
        }
        summaries[name] = {
            "fully_verified": True,
            "calendar": {"events": 3},
            "championship_points": {"rows": 10},
            "individual_race_results": {
                "status": "candidate_classifications_require_round_and_official_review",
                "classified_events": 2, "completed_calendar_events": 2,
                "verification": {"officially_cross_checked": True,
                                 "season_scoring_and_adjustments_checked": True,
                                 "source_reuse_cleared": True}
            },
            "points_freshness": {"status": "no_later_scheduled_round"},
        }
    return ({"season": 2026, "generated_at": NOW, "series": series},
            {"season": 2026, "generated_at": NOW, "championships": summaries,
             "fully_verified_championships": 23, "complete": True})

class ReleaseGateTests(unittest.TestCase):
    def test_complete_fixture(self):
        self.assertEqual(verify(*fixtures()), [])
    def test_calendar_count_disagreement(self):
        detail, summary = fixtures()
        summary["championships"]["Test Series 00"]["calendar"]["events"] = 4
        self.assertTrue(any("calendar event counts disagree" in x for x in verify(detail, summary)))
    def test_completed_count_disagreement(self):
        detail, summary = fixtures()
        summary["championships"]["Test Series 00"]["individual_race_results"]["completed_calendar_events"] = 1
        self.assertTrue(any("completed-event counts disagree" in x for x in verify(detail, summary)))
    def test_missing_classifications(self):
        detail, summary = fixtures()
        summary["championships"]["Test Series 00"]["individual_race_results"]["status"] = "winner_summaries_available_not_full_classifications"
        self.assertTrue(verify(detail, summary))
    def test_mismatched_completed_rounds(self):
        detail, summary = fixtures()
        summary["championships"]["Test Series 00"]["individual_race_results"]["classified_events"] = 1
        self.assertTrue(verify(detail, summary))
    def test_missing_scoring_adjustments_review(self):
        detail, summary = fixtures()
        summary["championships"]["Test Series 00"]["individual_race_results"]["verification"]["season_scoring_and_adjustments_checked"] = False
        self.assertTrue(verify(detail, summary))
    def test_uncleared_rights(self):
        detail, summary = fixtures()
        detail["series"]["Test Series 00"]["commercial_reuse_cleared"] = False
        self.assertTrue(verify(detail, summary))
    def test_missing_championship(self):
        detail, summary = fixtures()
        del detail["series"]["Test Series 00"]
        self.assertTrue(verify(detail, summary))
    def test_stale_report(self):
        detail, summary = fixtures()
        detail["generated_at"] = "2026-01-01T00:00:00+00:00"
        self.assertTrue(verify(detail, summary))
    def test_unverified_standings_freshness(self):
        detail, summary = fixtures()
        summary["championships"]["Test Series 00"]["points_freshness"]["status"] = "potentially_stale_after_scheduled_round"
        self.assertTrue(verify(detail, summary))

if __name__ == "__main__":
    unittest.main()
