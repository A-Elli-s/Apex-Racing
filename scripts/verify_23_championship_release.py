#!/usr/bin/env python3
"""Fail-closed release gate for Apex Racing World 2026 data.

This is an independent check; it does not change public site content.
Run: python3 scripts/verify_23_championship_release.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COVERAGE = ROOT / "data/quality/championship-coverage.json"
DETAIL = ROOT / "data/coverage.json"
EXPECTED = 23

def main():
    detailed = json.loads(COVERAGE.read_text(encoding="utf-8"))
    summary = json.loads(DETAIL.read_text(encoding="utf-8"))
    series = detailed.get("series", {})
    failures = []
    if len(series) != EXPECTED:
        failures.append(f"Expected {EXPECTED} championships; found {len(series)}")
    for name, record in sorted(series.items()):
        missing = [field for field in (
            "calendar_available", "points_table_available",
            "full_race_classifications_available", "review_record_complete",
            "officially_cross_checked", "commercial_reuse_cleared",
            "ready_for_release"
        ) if record.get(field) is not True]
        if missing:
            failures.append(f"{name}: {', '.join(missing)}")
    if summary.get("fully_verified_championships") != EXPECTED:
        failures.append("Summary does not certify 23 verified championships")
    if summary.get("complete") is not True:
        failures.append("Summary complete flag is not true")
    if failures:
        print("NOT RELEASE READY:")
        for failure in failures:
            print(" -", failure)
        return 1
    print("Data flags pass; independently verify preview accessibility before release.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
