#!/usr/bin/env python3
"""Determine whether the racing collectors should run today.

Run when ANY of these is true:
  * it is Monday (weekly sweep);
  * a listed race happened yesterday or the day before (results and penalties
    often finalise a day or two after the flag, and a failed run gets a retry);
  * a series that the bots are supposed to refresh is still behind the calendar
    (self-healing: a failed run is retried the next day instead of next Monday).

Series that cannot be refreshed by a bot (rights-restricted or blocked at the
source) never trigger a run; they are reported separately.
No network calls.
"""
import argparse
import datetime as dt
import json
from pathlib import Path

try:
    from scripts import check_freshness
except ImportError:  # executed as `python scripts/should_refresh_racing.py`
    import check_freshness

ROOT = Path(__file__).resolve().parents[1]
RACE_WINDOW_DAYS = 2


def decide(today=None, root=ROOT):
    today = today or dt.datetime.now(dt.timezone.utc).date()
    data = json.loads((Path(root) / "data/races.json").read_text(encoding="utf-8"))
    window = {(today - dt.timedelta(days=n)).isoformat()
              for n in range(1, RACE_WINDOW_DAYS + 1)}
    yesterday = (today - dt.timedelta(days=1)).isoformat()
    recent, completed = [], []
    for series, races in data.get("series", {}).items():
        for race in races:
            day = race.get("date")
            if day in window:
                item = {"series": series, "race": race.get("name", ""), "date": day}
                recent.append(item)
                if day == yesterday:
                    completed.append(item)
    try:
        behind = check_freshness.evaluate(today, root)
    except Exception as error:  # a broken report must never block collection
        behind, note = [], "freshness check failed: " + str(error)[:120]
    else:
        note = None
    stale_auto = [r["series"] for r in behind if r["stale"] and r["refresh_path"] == "automatic"]
    needs_manual = [r["series"] for r in behind if r["stale"] and r["refresh_path"] == "manual"]
    weekly = today.weekday() == 0
    decision = {"run": weekly or bool(recent) or bool(stale_auto),
                "weekly": weekly,
                "race_yesterday": completed,
                "races_in_window": recent,
                "stale_automatic_series": stale_auto,
                "needs_manual_update": needs_manual,
                "checked_on": today.isoformat()}
    if note:
        decision["note"] = note
    return decision


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="UTC date YYYY-MM-DD, for testing")
    args = parser.parse_args()
    today = dt.date.fromisoformat(args.date) if args.date else None
    print(json.dumps(decide(today), indent=2))
