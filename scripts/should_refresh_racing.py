#!/usr/bin/env python3
"""Determine whether the racing collectors should run.
Weekly Monday refresh, or the UTC day after any listed race. No network calls.
"""
import argparse
import datetime as dt
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def decide(today=None):
    today = today or dt.datetime.now(dt.timezone.utc).date()
    data = json.loads((ROOT / "data/races.json").read_text(encoding="utf-8"))
    yesterday = (today - dt.timedelta(days=1)).isoformat()
    completed = []
    for series, races in data.get("series", {}).items():
        for race in races:
            if race.get("date") == yesterday:
                completed.append({"series": series, "race": race.get("name", ""), "date": yesterday})
    return {"run": today.weekday() == 0 or bool(completed),
            "weekly": today.weekday() == 0,
            "race_yesterday": completed,
            "checked_on": today.isoformat()}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="UTC date YYYY-MM-DD, for testing")
    args = parser.parse_args()
    today = dt.date.fromisoformat(args.date) if args.date else None
    print(json.dumps(decide(today), indent=2))
