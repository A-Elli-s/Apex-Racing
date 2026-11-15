#!/usr/bin/env python3
"""Report which standings snapshots may be behind the calendar.

Network-free. For every series in the standings manifest it finds the most
recent championship round that has already been scheduled to run and asks
whether the published snapshot was retrieved after that round. A snapshot taken
before (or on the day of) a round cannot contain that round's points, so it is
flagged for refresh.

This is a currency check only. It never verifies that any points are correct.

Usage:
    python scripts/check_freshness.py                # print a table
    python scripts/check_freshness.py --write        # also write data/quality/freshness.json
    python scripts/check_freshness.py --strict       # exit 1 if anything is stale
"""
import argparse
import datetime as dt
import json
import pathlib
import sys

try:
    from scripts.calendar_rules import championship_events
    from scripts.snapshot_freshness import snapshot_freshness
except ImportError:  # executed as `python scripts/check_freshness.py`
    from calendar_rules import championship_events
    from snapshot_freshness import snapshot_freshness

ROOT = pathlib.Path(__file__).resolve().parents[1]

MOTO = "MotoGP / Moto2 / Moto3"
NASCAR = "NASCAR Cup / O’Reilly / Trucks"

# manifest series -> (calendar group in races.json, event-name prefixes or None)
CALENDAR = {
    "F1": ("Formula 1", None),
    "F2": ("Formula 2", None),
    "F3": ("Formula 3", None),
    "IndyCar": ("IndyCar", None),
    "WEC": ("WEC", None),
    "IMSA": ("IMSA", None),
    "Formula E": ("Formula E", None),
    "WRC": ("WRC", None),
    "Supercars": ("Supercars", None),
    "NHRA": ("NHRA", None),
    "WorldSBK": ("WorldSBK", None),
    "Supercross": ("Supercross", None),
    "Pro Motocross": ("Pro Motocross", None),
    "MXGP": ("MXGP", None),
    "Monster Jam": ("Monster Jam", None),
    "MotoGP": (MOTO, None),
    "Moto2": (MOTO, None),
    "Moto3": (MOTO, None),
    "NASCAR Cup": (NASCAR, ("cup",)),
    "NASCAR O’Reilly": (NASCAR, ("xfinity", "o’reilly", "o'reilly", "oreilly")),
    "NASCAR Trucks": (NASCAR, ("truck", "craftsman")),
}

# How each series can be brought up to date.
#   automatic - a collector in scripts/ refreshes it and the scheduled workflow runs it.
#   barred    - rights are pending (data/quality/source-permissions-2026.json); no bot
#               may collect it. Link to the organizer instead.
#   manual    - the organizer's pages block automated access, so a person (or a
#               research session) must update the snapshot after each round.
REFRESH_PATH = {
    "F1": "automatic", "F2": "automatic", "F3": "automatic",
    "IndyCar": "automatic", "WEC": "automatic", "WRC": "automatic",
    "Formula E": "automatic", "IMSA": "automatic",
    "MotoGP": "automatic", "Moto2": "automatic", "Moto3": "automatic",
    "Supercross": "automatic", "Pro Motocross": "automatic", "MXGP": "automatic",
    "NHRA": "barred", "Supercars": "barred", "WorldSBK": "barred",
    "NASCAR Cup": "manual", "NASCAR O’Reilly": "manual", "NASCAR Trucks": "manual",
    "Monster Jam": "manual",
}

STALE_STATUSES = {"potentially_stale_after_scheduled_round",
                  "same_day_timing_requires_review"}


def _load(path):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def _events_for(races, series):
    group, prefixes = CALENDAR[series]
    events = races.get("series", {}).get(group, [])
    if prefixes:
        events = [e for e in events
                  if str(e.get("name", "")).lower().split(" — ")[0].strip() in prefixes]
    return events


def evaluate(as_of=None, root=ROOT):
    """Return one record per series that has a published current-season snapshot."""
    as_of = as_of or dt.datetime.now(dt.timezone.utc).date()
    root = pathlib.Path(root)
    races = _load(root / "data" / "races.json")
    manifest = _load(root / "data" / "standings" / "manifest.json")
    year = as_of.year
    records = []
    for series in CALENDAR:
        entry = manifest.get("series", {}).get(series, {})
        rel = entry.get("seasons", {}).get(str(year))
        refresh_path = REFRESH_PATH.get(series, "manual")
        if not rel:
            records.append({"series": series, "status": "no_snapshot", "stale": False,
                            "refresh_path": refresh_path})
            continue
        path = root / rel.lstrip("/")
        try:
            snapshot = _load(path)
        except (OSError, ValueError):
            records.append({"series": series, "snapshot": rel, "refresh_path": refresh_path,
                            "status": "snapshot_unreadable", "stale": True})
            continue
        events = championship_events(series, _events_for(races, series), year)
        result = snapshot_freshness(snapshot, events, as_of=as_of)
        status = result["status"]
        record = {"series": series, "snapshot": rel, "status": status,
                  "refresh_path": refresh_path,
                  "stale": status in STALE_STATUSES or status in (
                      "retrieval_timestamp_missing", "invalid_retrieval_timestamp"),
                  "retrieved_utc_date": result.get("retrieved_utc_date"),
                  "latest_scheduled_round_date": result.get("latest_scheduled_round_date")}
        # A same-day snapshot only matters once that round day is behind us.
        if status == "same_day_timing_requires_review":
            latest = dt.date.fromisoformat(result["latest_scheduled_round_date"])
            record["stale"] = latest < as_of
        records.append(record)
    return records


def stale_series(as_of=None, root=ROOT, path=None):
    """Names of stale series, optionally only those with the given refresh path."""
    return [r["series"] for r in evaluate(as_of, root)
            if r["stale"] and (path is None or r["refresh_path"] == path)]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--date", help="UTC date YYYY-MM-DD (for testing)")
    parser.add_argument("--write", action="store_true",
                        help="write data/quality/freshness.json")
    parser.add_argument("--strict", action="store_true",
                        help="exit 1 when any series is stale")
    args = parser.parse_args(argv)
    as_of = dt.date.fromisoformat(args.date) if args.date else None
    records = evaluate(as_of)
    stale = [r for r in records if r["stale"]]
    for r in records:
        flag = "STALE" if r["stale"] else "ok   "
        print(f"{flag} {r['series']:16} {r['refresh_path']:9} "
              f"snapshot={r.get('retrieved_utc_date')} "
              f"last_round={r.get('latest_scheduled_round_date')} [{r['status']}]")
    by_path = {p: [r["series"] for r in stale if r["refresh_path"] == p]
               for p in ("automatic", "manual", "barred")}
    print(f"\n{len(stale)} of {len(records)} series are behind the calendar: "
          f"{len(by_path['automatic'])} the bots should refresh, "
          f"{len(by_path['manual'])} need a manual update, "
          f"{len(by_path['barred'])} are rights-restricted (link only)")
    if args.write:
        out = ROOT / "data" / "quality" / "freshness.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        payload = {"checked_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                   "as_of": (as_of or dt.datetime.now(dt.timezone.utc).date()).isoformat(),
                   "note": "Currency check only; does not verify points.",
                   "stale_series": [r["series"] for r in stale],
                   "stale_by_refresh_path": by_path, "series": records}
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")
    return 1 if (args.strict and stale) else 0


if __name__ == "__main__":
    sys.exit(main())
