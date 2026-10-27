#!/usr/bin/env python3
"""Audit DEV-only season coverage and reconcile per-round IMSA points.

A published snapshot is NOT proof of official verification. Never infer missing
championship totals from race wins, podiums or incomplete classifications.
"""
import datetime as dt
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
YEAR = dt.datetime.now(dt.timezone.utc).year
DATA = ROOT / "data"
STANDINGS = DATA / "standings"
SERIES = (
    "F1", "F2", "F3", "IndyCar", "NASCAR Cup", "NASCAR O’Reilly",
    "WEC", "IMSA", "Formula E", "WRC", "Supercars", "NHRA",
    "MotoGP", "Moto2", "Moto3", "WorldSBK", "Supercross",
    "Pro Motocross", "MXGP", "NASCAR Trucks", "Dakar Rally",
    "Off-road racing", "Monster Jam",
)
CALENDAR = {
    "F1": "Formula 1", "F2": "Formula 2", "F3": "Formula 3",
    "IndyCar": "IndyCar", "WEC": "WEC", "Formula E": "Formula E",
    "WRC": "WRC", "MotoGP": "MotoGP / Moto2 / Moto3",
    "Moto2": "MotoGP / Moto2 / Moto3", "Moto3": "MotoGP / Moto2 / Moto3",
    "NASCAR Cup": "NASCAR Cup / O’Reilly / Trucks",
    "NASCAR O’Reilly": "NASCAR Cup / O’Reilly / Trucks",
    "NASCAR Trucks": "NASCAR Cup / O’Reilly / Trucks",
}
NASCAR_TAG = {
    "NASCAR Cup": "CUP", "NASCAR O’Reilly": "O’REILLY",
    "NASCAR Trucks": "TRUCK",
}

def read(path):
    return json.loads(path.read_text(encoding="utf-8"))

def snapshot_for(manifest, series, section):
    path = manifest.get("series", {}).get(series, {}).get(section, {}).get(str(YEAR))
    if not isinstance(path, str) or not path.startswith("/data/standings/"):
        return None
    filename = path.removeprefix("/data/standings/")
    if "/" in filename or "\\" in filename:
        return None
    file = STANDINGS / filename
    if not file.is_file():
        return None
    data = read(file)
    if data.get("series") != series or str(data.get("season")) != str(YEAR):
        return None
    return data

def numeric(v):
    try:
        number = float(str(v).replace(",", "").strip())
        if number < 0 or not (number < float("inf")):
            return None
        return number
    except (ValueError, TypeError):
        return None

def points_valid(snapshot):
    if not snapshot:
        return False
    data = snapshot.get("data", {})
    if not isinstance(data, dict):
        return False
    headers, rows = data.get("headers"), data.get("rows")
    if not isinstance(headers, list) or not isinstance(rows, list):
        return False
    idx = next((i for i, h in enumerate(headers) if str(h).strip().lower() in ("points", "point", "pts", "total")), None)
    if idx is None or len(rows) < 3:
        return False
    return all(isinstance(r, list) and len(r) == len(headers) and numeric(r[idx]) is not None for r in rows)

def results_valid(snapshot):
    if not snapshot:
        return False
    data = snapshot.get("data")
    if isinstance(data, dict):
        data = data.get("results")
    return isinstance(data, list) and len(data) >= 3 and all(
        isinstance(row, dict) and row.get("winning_driver") and
        (row.get("round") or row.get("event") or row.get("eprix"))
        for row in data
    )

def reconcile_imsa(snapshot):
    """IMSA snapshot's per-event columns already include awarded event points.

    Only sum complete numeric event columns; do not infer qualification/bonus
    scoring independently or replace an inconsistent published total.
    """
    if not snapshot or not isinstance(snapshot.get("data"), dict):
        return {"status": "unavailable"}
    headers = snapshot["data"].get("headers", [])
    rows = snapshot["data"].get("rows", [])
    try:
        total_idx = next(i for i, h in enumerate(headers) if str(h).strip().lower() == "total")
    except StopIteration:
        return {"status": "missing_total_column"}
    if total_idx < 4 or len(rows) < 3:
        return {"status": "insufficient_round_data"}
    # Expected schema: Rank, Drivers, round 1 ... round N, Total.
    mismatches = []
    checked = 0
    for row in rows:
        if not isinstance(row, list) or len(row) != len(headers):
            return {"status": "invalid_row"}
        rounds = [numeric(x) for x in row[2:total_idx]]
        actual = numeric(row[total_idx])
        if len(rounds) < 3 or None in rounds or actual is None:
            return {"status": "incomplete_round_data"}
        computed = sum(rounds)
        checked += 1
        if abs(computed - actual) > 0.001:
            mismatches.append({"driver": str(row[1]), "calculated": computed, "published": actual})
    return {"status": "matched" if not mismatches else "mismatch",
            "rows_checked": checked, "mismatches": mismatches[:10],
            "method": "sum of published per-event points, not raw finish positions"}

def main():
    manifest = read(STANDINGS / "manifest.json")
    calendar = read(DATA / "races.json").get("series", {})
    report = {"season": YEAR, "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
              "status": "audit_only_not_official_verification", "series": {}}
    for name in SERIES:
        key = CALENDAR.get(name)
        events = calendar.get(key, []) if key else []
        if name in NASCAR_TAG:
            tag = NASCAR_TAG[name]
            events = [event for event in events if str(event.get("name", "")).upper().startswith(tag)]
        valid_events = [e for e in events if isinstance(e, dict) and str(e.get("date", "")).startswith(str(YEAR) + "-")
                        and e.get("name") and e.get("venue") and e.get("url")]
        points = snapshot_for(manifest, name, "seasons")
        results = snapshot_for(manifest, name, "race_results_seasons")
        entry = manifest.get("series", {}).get(name, {})
        provider = entry.get("provider", "")
        points_ok = points_valid(points)
        calendar_ok = len(valid_events) >= 3
        results_ok = results_valid(results)
        rights_pending = bool(entry.get("reuse_review_required") or (points or {}).get("reuse_review_required"))
        # Missing permission metadata does not mean commercial reuse is allowed.
        rights_cleared = entry.get("commercial_reuse_cleared") is True
        officially_checked = bool(points and points.get("points_audit", {}).get("status")
                                 in ("officially_verified", "calculated_and_officially_verified"))
        release_ready = (points_ok and calendar_ok and results_ok and
                         officially_checked and rights_cleared and not rights_pending)
        report["series"][name] = {
            "calendar_events": len(valid_events),
            "calendar_available": calendar_ok,
            "points_table_available": points_ok,
            "race_results_snapshot_available": results_ok,
            "points_source": points.get("source_url") if points_ok else None,
            "provider": provider,
            "officially_cross_checked": officially_checked,
            "source_reuse_review_required": rights_pending,
            "commercial_reuse_cleared": rights_cleared,
            "ready_for_release": release_ready,
        }
    imsa = snapshot_for(manifest, "IMSA", "seasons")
    report["imsa_round_points_audit"] = reconcile_imsa(imsa)
    report["summary"] = {
        "total_championships": len(SERIES),
        "calendars_with_events": sum(v["calendar_available"] for v in report["series"].values()),
        "points_tables_with_numeric_totals": sum(v["points_table_available"] for v in report["series"].values()),
        "race_results_snapshots": sum(v["race_results_snapshot_available"] for v in report["series"].values()),
        "complete_and_officially_cross_checked": sum(
            v["calendar_available"] and v["points_table_available"] and v["officially_cross_checked"]
            for v in report["series"].values()),
        "fully_complete_and_cleared": sum(v["ready_for_release"] for v in report["series"].values()),
        "source_reuse_review_pending": sum(v["source_reuse_review_required"] for v in report["series"].values()),
    }
    output = DATA / "coverage.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))
    print("IMSA points reconciliation:", report["imsa_round_points_audit"]["status"])

if __name__ == "__main__":
    main()
