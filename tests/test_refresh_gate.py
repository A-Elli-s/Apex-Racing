"""The refresh gate must retry failures and must never loop on series a bot cannot fetch."""
import datetime as dt
import json
import pathlib
import tempfile
import unittest
from unittest import mock

from scripts import check_freshness, should_refresh_racing as gate

MONDAY = dt.date(2026, 11, 9)
TUESDAY = dt.date(2026, 11, 10)


def make_root(calendar, snapshots):
    tmp = tempfile.TemporaryDirectory()
    root = pathlib.Path(tmp.name)
    (root / "data/standings").mkdir(parents=True)
    (root / "data/races.json").write_text(json.dumps({"series": calendar}))
    series = {}
    for name, stamp in snapshots.items():
        rel = f"/data/standings/{name.lower().replace(' ', '-')}-2026.json"
        (root / rel.lstrip("/")).write_text(json.dumps({"retrieved_at": stamp}))
        series[name] = {"seasons": {"2026": rel}}
    (root / "data/standings/manifest.json").write_text(json.dumps({"series": series}))
    return tmp, root


def race(day):
    return {"date": day, "name": "GP", "venue": "V", "url": "https://example.com"}


class GateTests(unittest.TestCase):
    def decide(self, today, calendar, snapshots):
        tmp, root = make_root(calendar, snapshots)
        self.addCleanup(tmp.cleanup)
        return gate.decide(today, root)

    def test_monday_always_runs(self):
        self.assertTrue(self.decide(MONDAY, {}, {})["run"])

    def test_race_yesterday_and_two_days_ago_trigger_a_run(self):
        for race_day in ("2026-11-09", "2026-11-08"):
            result = self.decide(TUESDAY, {"Formula 1": [race(race_day)]},
                                 {"F1": "2026-11-10T00:00:00+00:00"})
            self.assertTrue(result["run"], race_day)

    def test_old_race_with_current_data_does_not_run(self):
        result = self.decide(TUESDAY, {"Formula 1": [race("2026-11-01")]},
                             {"F1": "2026-11-05T00:00:00+00:00"})
        self.assertFalse(result["run"])

    def test_failed_run_is_retried_next_day(self):
        # Race was 5 days ago and the snapshot is older: the earlier run failed.
        result = self.decide(TUESDAY, {"Formula 1": [race("2026-11-05")]},
                             {"F1": "2026-11-03T00:00:00+00:00"})
        self.assertTrue(result["run"])
        self.assertEqual(result["stale_automatic_series"], ["F1"])

    def test_series_a_bot_cannot_fetch_never_forces_a_run(self):
        calendar = {"NHRA": [race("2026-11-01")], check_freshness.NASCAR: [
            {**race("2026-11-01"), "name": "CUP — X"}]}
        result = self.decide(TUESDAY, calendar, {"NHRA": "2026-10-01T00:00:00+00:00",
                                                 "NASCAR Cup": "2026-10-01T00:00:00+00:00"})
        self.assertFalse(result["run"])
        self.assertEqual(result["needs_manual_update"], ["NASCAR Cup"])

    def test_output_keeps_keys_the_workflow_reads(self):
        result = self.decide(TUESDAY, {}, {})
        for key in ("run", "weekly", "race_yesterday", "checked_on"):
            self.assertIn(key, result)

    def test_broken_freshness_check_does_not_block_collection(self):
        tmp, root = make_root({"Formula 1": [race("2026-11-09")]}, {})
        self.addCleanup(tmp.cleanup)
        with mock.patch.object(check_freshness, "evaluate", side_effect=ValueError("boom")):
            result = gate.decide(TUESDAY, root)
        self.assertTrue(result["run"])  # race yesterday still triggers
        self.assertIn("freshness check failed", result["note"])


if __name__ == "__main__":
    unittest.main()
