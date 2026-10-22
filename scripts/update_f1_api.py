#!/usr/bin/env python3
"""Refresh validated F1 calendar and points standings; preserve all other series.
Jolpica public API is rate-limited; confirm commercial redistribution permission
before publishing generated snapshots on a monetized website.
"""
import datetime as dt
import json
import pathlib
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
YEAR = dt.datetime.now(dt.timezone.utc).year
BASE = "https://api.jolpi.ca/ergast/f1"
OFFICIAL = "https://www.formula1.com/en/racing/2026"

def get(path):
    req = urllib.request.Request(BASE + "/" + path, headers={"User-Agent": "ApexRacingWorld/1.0", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=25) as response:
        if response.status != 200:
            raise ValueError("HTTP " + str(response.status))
        return json.loads(response.read(2_000_000))

def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

def main():
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    calendar_path = ROOT / "data" / "races.json"
    calendar = json.loads(calendar_path.read_text(encoding="utf-8")) if calendar_path.exists() else {"series": {}}
    try:
        races = get(f"{YEAR}.json?limit=100")["MRData"]["RaceTable"]["Races"]
        rows = []
        for race in races:
            date = race.get("date", "")
            name = race.get("raceName", "")
            venue = race.get("Circuit", {}).get("circuitName", "")
            if len(date) != 10 or not name or not venue:
                continue
            rows.append({"date": date, "name": name, "venue": venue, "url": "https://www.formula1.com/en/racing/" + str(YEAR)})
        if len(rows) < 10:
            raise ValueError("F1 calendar failed completeness check")
        calendar.setdefault("series", {})["Formula 1"] = rows
        calendar["updated"] = now
        write(calendar_path, calendar)
        print("F1 calendar refreshed:", len(rows))
    except Exception as error:
        print("F1 calendar preserved:", error)

    manifest_path = ROOT / "data" / "standings" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {"series": {}}
    for endpoint, series, slug, identity, field in [
        ("driverStandings", "F1", "f1", "Driver", "Driver"),
        ("constructorStandings", "F1 Constructors", "f1-constructors", "Constructor", "Constructor"),
    ]:
        try:
            lists = get(f"{YEAR}/{endpoint}.json?limit=100")["MRData"]["StandingsTable"]["StandingsLists"]
            if not lists:
                raise ValueError("No current standings published")
            standings = lists[0].get("DriverStandings" if identity == "Driver" else "ConstructorStandings", [])
            rows = []
            for record in standings:
                person = record.get(field) or {}
                name = (person.get("givenName", "") + " " + person.get("familyName", "")).strip() if identity == "Driver" else person.get("name", "")
                points = record.get("points", "")
                if not name or not str(points).replace(".", "", 1).isdigit():
                    continue
                rows.append([str(record.get("position", len(rows) + 1)), name, str(points)])
            if len(rows) < 3:
                raise ValueError("Too few validated championship standings")
            path = ROOT / "data" / "standings" / f"{slug}-{YEAR}.json"
            write(path, {"series": series, "season": YEAR, "source_url": BASE + f"/{YEAR}/{endpoint}.json",
                         "official_url": OFFICIAL, "retrieved_at": now,
                         "data": {"headers": ["Position", "Driver" if identity == "Driver" else "Team", "Points"], "rows": rows}})
            entry = manifest.setdefault("series", {}).setdefault(series, {"official_url": OFFICIAL, "provider": "Jolpica-F1", "seasons": {}})
            entry.setdefault("seasons", {})[str(YEAR)] = "/data/standings/" + path.name
            print(series, "refreshed:", len(rows))
        except Exception as error:
            print(series, "preserved:", error)
    manifest["updated"] = now
    write(manifest_path, manifest)

if __name__ == "__main__":
    main()
