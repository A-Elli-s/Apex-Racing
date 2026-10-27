#!/usr/bin/env python3
"""Stage community MotoGP/Moto2/Moto3 2026 rider points, not official standings.

Only Wikipedia's CC BY-SA pages are considered here. Parsing fails closed if
the standings table changes shape. Never infer points from finishing places.
Commercial-site publication requires attribution/share-alike review first.
"""
import datetime as dt
import json
import pathlib
import re
import urllib.parse
import urllib.request

from bs4 import BeautifulSoup

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "standings"
YEAR = dt.datetime.now(dt.timezone.utc).year
PAGES = {
    "MotoGP": f"{YEAR}_MotoGP_World_Championship",
    "Moto2": f"{YEAR}_Moto2_World_Championship",
    "Moto3": f"{YEAR}_Moto3_World_Championship",
}
LICENSE = "https://creativecommons.org/licenses/by-sa/4.0/"


def text(cell):
    # Strip citation/superscript decorations, not the rider's name.
    copy = BeautifulSoup(str(cell), "html.parser")
    for element in copy.select("sup.reference, span.reference, .sortkey"):
        element.decompose()
    return " ".join(copy.stripped_strings)


def get_table(page):
    url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode({
        "action": "parse", "page": page, "prop": "text", "format": "json",
    })
    req = urllib.request.Request(url, headers={
        "User-Agent": "ApexRacingWorldResearch/1.0 (contact@apexracingworld.com)",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=25) as response:
        if response.status != 200:
            raise ValueError("Wikipedia HTTP " + str(response.status))
        raw = response.read(3_000_001)
        if len(raw) > 3_000_000:
            raise ValueError("Wikipedia response too large")
        payload = json.loads(raw)
    html = payload.get("parse", {}).get("text", {}).get("*")
    if not html:
        raise ValueError("Wikipedia page unavailable")
    soup = BeautifulSoup(html, "html.parser")
    for table in soup.select("table.wikitable"):
        trs = table.find_all("tr")
        if len(trs) < 18:
            continue
        headings = " ".join(text(row) for row in trs[:2]).lower()
        if not ("rider" in headings and ("pts" in headings or "points" in headings)
                and ("pos" in headings or "rank" in headings)):
            continue
        rows = []
        seen = set()
        for tr in trs:
            cells = tr.find_all(["th", "td"], recursive=False)
            if len(cells) < 5:
                continue
            rank_raw = text(cells[0]).strip()
            if not re.fullmatch(r"\d{1,2}", rank_raw):
                continue
            name = text(cells[1]).strip()
            # The final column of the rider table must be championship points.
            pts_raw = text(cells[-1]).replace(",", "").strip()
            if not re.fullmatch(r"\d+(?:\.\d+)?", pts_raw):
                continue
            rank = int(rank_raw)
            if not name or name in seen or rank < 1:
                continue
            seen.add(name)
            rows.append([str(rank), name, pts_raw])
        # Require a substantial, ordered championship table. Reject team tables,
        # partial top-five lists, empty pre-season standings and malformed rows.
        if len(rows) < 15 or rows[0][0] != "1":
            continue
        if any(int(rows[i][0]) < int(rows[i-1][0]) for i in range(1, len(rows))):
            continue
        if any(float(rows[i][2]) > float(rows[i-1][2]) for i in range(1, len(rows))):
            continue
        if float(rows[0][2]) <= 0:
            continue
        return rows
    raise ValueError("No complete ranked rider points table found")


def main():
    manifest_path = OUT / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for series, page in PAGES.items():
        try:
            rows = get_table(page)
            source = "https://en.wikipedia.org/wiki/" + page
            now = dt.datetime.now(dt.timezone.utc).isoformat()
            snapshot = {
                "series": series, "season": YEAR, "source_url": source,
                "official_url": "https://www.motogp.com/en/world-standing/" + str(YEAR) + "/" + series.lower() + "/championship-standings",
                "retrieved_at": now,
                "provider": "Wikipedia community standings (not official)",
                "attribution": "Wikipedia contributors", "license": "CC BY-SA 4.0",
                "license_url": LICENSE, "reuse_review_required": True,
                "data": {"headers": ["Position", "Rider", "Points"], "rows": rows},
                "points_audit": {"status": "community_points_not_officially_verified",
                                 "method": "published community points, not inferred from race finishes"},
            }
            path = OUT / (series.lower() + "-community-" + str(YEAR) + ".json")
            path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            entry = manifest.setdefault("series", {}).setdefault(series, {})
            entry["seasons"] = dict(entry.get("seasons", {}))
            entry["seasons"][str(YEAR)] = "/data/standings/" + path.name
            entry.update({"provider": snapshot["provider"], "official_url": snapshot["official_url"],
                          "reuse_review_required": True, "attribution": "Wikipedia contributors",
                          "license_url": LICENSE})
            print(series, "community standings staged:", len(rows))
        except Exception as error:
            print(series, "community standings not staged; existing data preserved:", str(error)[:220])
    manifest["updated"] = dt.datetime.now(dt.timezone.utc).isoformat()
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
