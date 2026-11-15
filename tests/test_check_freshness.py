"""Freshness is a currency check: a snapshot cannot contain a round that ran after it."""
import datetime as dt
import json
import pathlib
import tempfile
import unittest

from scripts import check_freshness, report_stale_series


def ev(day, name="Round"):
    return {"date": day, "name": name, "venue": "V", "url": "https://example.com"}


class Fixture:
    """A throwaway repo root with a calendar, manifest and snapshots."""

    def __init__(self, calendar, snapshots):
        self.dir = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.dir.name)
        (self.root / "data/standings").mkdir(parents=True)
        (self.root / "data/races.json").write_text(json.dumps({"series": calendar}))
        series = {}
        for name, stamp in snapshots.items():
            slug = name.lower().replace(" ", "-").replace("’", "")
            rel = f"/data/standings/{slug}-2026.json"
            (self.root / rel.lstrip("/")).write_text(json.dumps({"retrieved_at": stamp}))
            series[name] = {"official_url": "https://example.com/" + slug,
                            "seasons": {"2026": rel}}
        (self.root / "data/standings/manifest.json").write_text(json.dumps({"series": series}))

    def records(self, as_of):
        return {r["series"]: r for r in check_freshness.evaluate(as_of, self.root)}

    def close(self):
        self.dir.cleanup()


class FreshnessTests(unittest.TestCase):
    AS_OF = dt.date(2026, 11, 10)

    def fixture(self, calendar, snapshots):
        f = Fixture(calendar, snapshots)
        self.addCleanup(f.close)
        return f

    def test_snapshot_before_round_is_stale_and_automatic(self):
        f = self.fixture({"Formula 1": [ev("2026-11-01")]},
                         {"F1": "2026-10-30T10:00:00+00:00"})
        record = f.records(self.AS_OF)["F1"]
        self.assertTrue(record["stale"])
        self.assertEqual(record["refresh_path"], "automatic")

    def test_snapshot_after_round_is_current(self):
        f = self.fixture({"Formula 1": [ev("2026-11-01")]},
                         {"F1": "2026-11-02T10:00:00+00:00"})
        self.assertFalse(f.records(self.AS_OF)["F1"]["stale"])

    def test_same_day_snapshot_stale_only_after_that_day_has_passed(self):
        f = self.fixture({"Formula 1": [ev("2026-11-01")]},
                         {"F1": "2026-11-01T11:35:00+00:00"})
        self.assertTrue(f.records(self.AS_OF)["F1"]["stale"])
        self.assertFalse(f.records(dt.date(2026, 11, 1))["F1"]["stale"])

    def test_future_rounds_never_make_a_snapshot_stale(self):
        f = self.fixture({"Formula 1": [ev("2026-12-06")]},
                         {"F1": "2026-10-01T00:00:00+00:00"})
        self.assertFalse(f.records(self.AS_OF)["F1"]["stale"])

    def test_missing_snapshot_is_reported_not_stale(self):
        f = self.fixture({"Formula 1": [ev("2026-11-01")]}, {})
        record = f.records(self.AS_OF)["F1"]
        self.assertEqual(record["status"], "no_snapshot")
        self.assertFalse(record["stale"])

    def test_missing_timestamp_is_stale(self):
        f = self.fixture({"Formula 1": [ev("2026-11-01")]}, {"F1": ""})
        self.assertTrue(f.records(self.AS_OF)["F1"]["stale"])

    def test_nascar_classes_are_judged_on_their_own_rounds(self):
        calendar = {check_freshness.NASCAR: [ev("2026-11-01", "CUP — A"),
                                             ev("2026-11-08", "TRUCK — B")]}
        f = self.fixture(calendar, {"NASCAR Cup": "2026-11-05T00:00:00+00:00",
                                    "NASCAR Trucks": "2026-11-05T00:00:00+00:00"})
        records = f.records(self.AS_OF)
        self.assertFalse(records["NASCAR Cup"]["stale"])
        self.assertTrue(records["NASCAR Trucks"]["stale"])

    def test_every_calendar_series_has_a_refresh_path(self):
        self.assertEqual(set(check_freshness.CALENDAR), set(check_freshness.REFRESH_PATH))
        self.assertTrue(set(check_freshness.REFRESH_PATH.values())
                        <= {"automatic", "manual", "barred"})

    def test_rights_restricted_series_are_never_automatic(self):
        for series in ("NHRA", "Supercars", "WorldSBK"):
            self.assertEqual(check_freshness.REFRESH_PATH[series], "barred")

    def test_stale_series_can_filter_by_refresh_path(self):
        calendar = {"Formula 1": [ev("2026-11-01")], "NHRA": [ev("2026-11-01")]}
        f = self.fixture(calendar, {"F1": "2026-10-01T00:00:00+00:00",
                                    "NHRA": "2026-10-01T00:00:00+00:00"})
        self.assertEqual(check_freshness.stale_series(self.AS_OF, f.root, "automatic"), ["F1"])
        self.assertEqual(check_freshness.stale_series(self.AS_OF, f.root, "barred"), ["NHRA"])


class ReportTests(unittest.TestCase):
    def test_nothing_stale_produces_no_output(self):
        self.assertEqual(report_stale_series.build({"series": [
            {"series": "F1", "stale": False, "refresh_path": "automatic"}]}), "")

    def test_report_groups_by_refresh_path_and_links_official_page(self):
        freshness = {"as_of": "2026-11-10", "series": [
            {"series": "F1", "stale": True, "refresh_path": "automatic",
             "retrieved_utc_date": "2026-10-30", "latest_scheduled_round_date": "2026-11-01"},
            {"series": "NASCAR Cup", "stale": True, "refresh_path": "manual",
             "retrieved_utc_date": "2026-10-27", "latest_scheduled_round_date": "2026-11-08"}]}
        manifest = {"series": {"NASCAR Cup": {"official_url": "https://example.com/n"}}}
        body = report_stale_series.build(freshness, manifest)
        self.assertIn("Bots should have refreshed these", body)
        self.assertIn("Needs a manual update", body)
        self.assertIn("[official standings](https://example.com/n)", body)
        self.assertNotIn("Link only", body)


if __name__ == "__main__":
    unittest.main()
