#!/usr/bin/env python3
"""Fail-closed data readiness gate. Does not certify preview accessibility."""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DETAIL = ROOT / "data/coverage.json"
SUMMARY = ROOT / "data/quality/championship-coverage.json"
EXPECTED = 23
REQUIRED = (
    "calendar_available", "points_table_available",
    "full_race_classifications_available", "review_record_complete",
    "officially_cross_checked", "commercial_reuse_cleared", "ready_for_release",
)

def verify(detail, summary):
    failures = []
    series = detail.get("series")
    championships = summary.get("championships")
    if not isinstance(series, dict):
        series = {}
        failures.append("Detailed coverage has no series mapping")
    if not isinstance(championships, dict):
        championships = {}
        failures.append("Summary has no championships mapping")
    if len(series) != EXPECTED or len(championships) != EXPECTED:
        failures.append(f"Expected {EXPECTED} entries in both reports; found {len(series)} detailed and {len(championships)} summary")
    if set(series) != set(championships):
        failures.append("Championship names differ between reports")
    if detail.get("season") != summary.get("season") or detail.get("season") != 2026:
        failures.append("Season mismatch between reports")
    for label, report in (("detailed", detail), ("summary", summary)):
        try:
            stamp = datetime.fromisoformat(report["generated_at"].replace("Z", "+00:00"))
            age = datetime.now(timezone.utc) - stamp
            if stamp.tzinfo is None or age.total_seconds() < 0 or age.total_seconds() > 172800:
                failures.append(f"{label} report timestamp is stale, future-dated or timezone-naive")
        except (KeyError, ValueError, TypeError):
            failures.append(f"{label} report has invalid generated_at")
    for name, record in sorted(series.items()):
        if not isinstance(record, dict):
            failures.append(f"{name}: invalid record")
            continue
        missing = [field for field in REQUIRED if record.get(field) is not True]
        if missing:
            failures.append(f"{name}: missing {', '.join(missing)}")
        if not isinstance(championships.get(name), dict):
            failures.append(f"{name}: invalid summary record")
            continue
        # Calendar counts must reconcile across the independently generated audits.
        calendar_count = record.get("calendar_events")
        summary_calendar = championships[name].get("calendar")
        summary_count = summary_calendar.get("events") if isinstance(summary_calendar, dict) else None
        if type(calendar_count) is not int or type(summary_count) is not int or calendar_count != summary_count:
            failures.append(f"{name}: calendar event counts disagree between audits")
        completed_count = record.get("completed_calendar_events")
        if (type(completed_count) is not int or type(calendar_count) is not int
                or completed_count < 0 or completed_count > calendar_count):
            failures.append(f"{name}: invalid completed calendar event count")
        if championships[name].get("fully_verified") is not True:
            failures.append(f"{name}: not fully verified in summary")
    # Cross-check the summary's underlying evidence, not only its readiness booleans.
    # These records must be populated by independently audited source checks.
    for name, record in sorted(championships.items()):
        if not isinstance(record, dict):
            continue
        calendar = record.get("calendar")
        points = record.get("championship_points")
        results = record.get("individual_race_results")
        if not isinstance(calendar, dict) or not isinstance(calendar.get("events"), int) or isinstance(calendar.get("events"), bool) or calendar["events"] < 1:
            failures.append(f"{name}: no valid calendar event count in summary")
        if not isinstance(points, dict) or not isinstance(points.get("rows"), int) or isinstance(points.get("rows"), bool) or points["rows"] < 1:
            failures.append(f"{name}: no valid standings rows in summary")
        if not isinstance(results, dict) or results.get("status") != "candidate_classifications_require_round_and_official_review":
            failures.append(f"{name}: no complete race-classification candidate evidenced in summary")
        else:
            classified = results.get("classified_events")
            completed = results.get("completed_calendar_events")
            if (type(classified) is not int or type(completed) is not int
                    or completed < 1 or classified != completed):
                failures.append(f"{name}: classified-event count does not exactly match completed calendar events")
        # A candidate feed is not an independently verified final classification. 
        # Require explicit review evidence and a rights decision before treating it as release-ready. 
        evidence = results.get("verification") if isinstance(results, dict) else None 
        if not isinstance(evidence, dict) or evidence.get("officially_cross_checked") is not True or evidence.get("season_scoring_and_adjustments_checked") is not True or evidence.get("source_reuse_cleared") is not True: 
            failures.append(f"{name}: race classification verification, scoring, or source rights evidence missing") 
        freshness = record.get("points_freshness")
        if not isinstance(freshness, dict) or freshness.get("status") != "no_later_scheduled_round":
            failures.append(f"{name}: standings freshness requires review")
    if summary.get("fully_verified_championships") != EXPECTED or summary.get("complete") is not True:
        failures.append("Summary does not certify 23 verified championships")
    return failures

def main():
    failures = verify(
        json.loads(DETAIL.read_text(encoding="utf-8")),
        json.loads(SUMMARY.read_text(encoding="utf-8")),
    )
    if failures:
        print("NOT RELEASE READY:")
        for failure in failures:
            print(" -", failure)
        return 1
    print("Data readiness flags pass; independently verify development preview accessibility.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
