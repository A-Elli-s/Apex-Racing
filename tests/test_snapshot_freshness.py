"""Snapshot currency must never be confused with official results verification."""
import datetime as dt
import unittest
from scripts.snapshot_freshness import snapshot_freshness


class SnapshotFreshnessTests(unittest.TestCase):
    TODAY = dt.date(2026, 11, 2)
    EVENTS = [{"date": "2026-10-25"}, {"date": "2026-11-01"},
              {"date": "2026-11-08"}]

    def check(self, timestamp, events=None):
        return snapshot_freshness(
            {"retrieved_at": timestamp}, self.EVENTS if events is None else events,
            as_of=self.TODAY)["status"]

    def test_prior_snapshot_flagged_not_assumed_invalid(self):
        self.assertEqual(self.check("2026-10-31T15:14:58+00:00"),
                         "potentially_stale_after_scheduled_round")

    def test_future_event_does_not_make_snapshot_stale(self):
        self.assertEqual(self.check("2026-11-02T14:00:00Z"),
                         "no_later_scheduled_round")

    def test_same_day_requires_review(self):
        self.assertEqual(self.check("2026-11-01T10:00:00+00:00"),
                         "same_day_timing_requires_review")

    def test_naive_and_missing_timestamp_rejected(self):
        self.assertEqual(self.check("2026-11-02T10:00:00"),
                         "invalid_retrieval_timestamp")
        self.assertEqual(snapshot_freshness({}, self.EVENTS, self.TODAY)["status"],
                         "retrieval_timestamp_missing")

    def test_no_elapsed_rounds_is_unknown(self):
        self.assertEqual(self.check("2026-10-20T10:00:00Z",
                                    [{"date": "2026-11-08"}]),
                         "no_elapsed_calendar_round_to_compare")

    def test_timezone_normalized_to_utc(self):
        self.assertEqual(self.check("2026-11-01T23:30:00-05:00"),
                         "no_later_scheduled_round")

    def test_missing_snapshot(self):
        self.assertEqual(snapshot_freshness(None, self.EVENTS, self.TODAY)["status"],
                         "missing_snapshot")


if __name__ == "__main__":
    unittest.main()
