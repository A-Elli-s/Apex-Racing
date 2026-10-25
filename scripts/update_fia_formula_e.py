#!/usr/bin/env python3
"""Refresh Formula E driver/team points from the FIA's public standings table.

Season spans two calendar years. Stage on dev only; rights review required
before commercial redistribution. Fail closed: keep previous verified snapshots.
"""
import datetime as dt
import json
import pathlib
import re

from update_standings import fetch_html, OUT

YEAR = dt.datetime.now(dt.timezone.utc).year
URL = f"https://www.fia.com/events/abb-fia-formula-e-world-championship/season-{YEAR-1}-{YEAR}/standings"
MIN_ROWS = {"Formula E": 15, "Formula E Teams": 8}

def parse_points(text):
    m = re.search(r"\b(\d+(?:\.\d+)?)\b", text.replace(",", ""))
    return float(m.group(1)) if m else None

def parse_table(table, kind):
    rows = table.find_all("tr")
    header = " ".join(rows[0].stripped_strings).lower() if rows else ""
    if kind == "Formula E" and "drivers" not in header:
        return []
    if kind == "Formula E Teams" and "teams" not in header:
        return []
    if "pts" not in header and "points" not in header:
        return []
    result = []
    for tr in rows[1:]:
        cells = tr.find_all(["td", "th"], recursive=False)
        if len(cells) < 5:
            continue
        rank = cells[0].get_text(" ", strip=True)
        if not re.fullmatch(r"\d{1,2}", rank):
            continue
        name = cells[1].get_text(" ", strip=True)
        if len(name) < 3 or len(name) > 90:
            continue
        points = parse_points(cells[-1].get_text(" ", strip=True))
        if points is None or points < 0 or points > 1500:
            continue
        # Each intermediate column represents awarded event points plus finish
        # position (e.g. "15 4"); blank means no awarded points.
        event_points = []
        for cell in cells[2:-1]:
            raw = cell.get_text(" ", strip=True)
            value = parse_points(raw) if raw else 0.0
            if value is None:
                break
            event_points.append(value)
        if len(event_points) != len(cells) - 3 or len(event_points) < 8:
            continue
        if abs(sum(event_points) - points) > 0.01:
            continue
        result.append([rank, name, str(int(points)) if points.is_integer() else str(points)])
    if len(result) < MIN_ROWS[kind]:
        return []
    if [int(row[0]) for row in result] != list(range(1, len(result)+1)):
        return []
    if any(float(result[i][2]) < float(result[i+1][2]) for i in range(len(result)-1)):
        return []
    return result

def main():
    try:
        soup = fetch_html(URL)
    except Exception as exc:
        print("FIA Formula E unavailable; keeping existing dev snapshots:", exc)
        return
    tables = soup.select("table")
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    manifest_path = OUT / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for series, slug, label in [
        ("Formula E", "formula-e", "Driver"),
        ("Formula E Teams", "formula-e-teams", "Team"),
    ]:
        candidates = [parse_table(t, series) for t in tables]
        candidates = [rows for rows in candidates if rows]
        if not candidates:
            print(series, "not parsed; preserving previous verified snapshot")
            continue
        rows = max(candidates, key=len)
        snapshot = {
            "series": series, "season": YEAR, "source_url": URL, "official_url": URL,
            "retrieved_at": now, "provider": "FIA public championship standings",
            "reuse_review_required": True,
            "data": {"headers": ["Position", label, "Points"], "rows": rows},
            "points_audit": {
                "status": "officially_verified",
                "method": "sum of FIA per-event awarded points matched FIA published total for every row",
                "rows_checked": len(rows), "verification_source": URL,
                "verification_date": dt.datetime.now(dt.timezone.utc).date().isoformat(),
            },
        }
        path = OUT / (slug + "-" + str(YEAR) + ".json")
        path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        entry = manifest.setdefault("series", {}).setdefault(series, {"seasons": {}})
        entry.setdefault("seasons", {})[str(YEAR)] = "/data/standings/" + path.name
        entry.update({"official_url": URL, "provider": "FIA public standings (reuse review required)",
                      "reuse_review_required": True})
        print("Validated", series, len(rows), "rows with per-event point reconciliation")
    manifest["updated"] = now
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")

if __name__ == "__main__":
    main()
