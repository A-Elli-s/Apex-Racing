#!/usr/bin/env python3
"""Fail-closed data readiness gate. Does not certify preview accessibility."""
import json
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
    if detail.get("season") != summary.get("season"):
        failures.append("Season mismatch between reports")
    for name, record in sorted(series.items()):
        if not isinstance(record, dict):
            failures.append(f"{name}: invalid record")
            continue
        missing = [field for field in REQUIRED if record.get(field) is not True]
        if missing:
            failures.append(f"{name}: missing {', '.join(missing)}")
        if championships.get(name, {}).get("fully_verified") is not True:
            failures.append(f"{name}: not fully verified in summary")
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
