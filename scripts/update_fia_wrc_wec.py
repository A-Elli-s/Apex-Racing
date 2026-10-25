#!/usr/bin/env python3
"""Stage official FIA WEC and WRC championship points, preserving old snapshots.

FIA pages may change markup; accept only complete structured tables. Do not
circumvent access controls or imply permission for commercial redistribution.
"""
import datetime as dt
import json
import re

from update_standings import fetch_html, OUT

YEAR = dt.datetime.now(dt.timezone.utc).year
SOURCES = {
    "WEC": ("world-endurance-championship", "Drivers", 15, "wec-points", True),
    "WEC Teams": ("world-endurance-championship", "Manufacturers", 5, "wec-manufacturers", True),
    "WRC": ("world-rally-championship", "Drivers", 10, "wrc-points", False),
    "WRC Teams": ("world-rally-championship", "Manufacturers", 2, "wrc-manufacturers", False),
}

def number(text):
    m = re.search(r"(?<!\w)(\d+(?:\.\d+)?)(?!\w)", str(text).replace(",", ""))
    return float(m.group(1)) if m else None

def parse(table, identity, minimum, require_sum):
    trs = table.find_all("tr")
    if not trs:
        return []
    heading = " ".join(" ".join(tr.stripped_strings) for tr in trs[:3]).lower()
    if identity.lower() not in heading or not ("pts" in heading or "points" in heading):
        return []
    rows = []
    for tr in trs[1:]:
        cells = tr.find_all(["td", "th"], recursive=False)
        if len(cells) < 5:
            continue
        rank = cells[0].get_text(" ", strip=True)
        if not re.fullmatch(r"\d{1,3}", rank):
            continue
        name = cells[1].get_text(" ", strip=True)
        if not 3 <= len(name) <= 100:
            continue
        total = number(cells[-1].get_text(" ", strip=True))
        if total is None or not 0 <= total <= 2000:
            continue
        if require_sum:
            values = []
            for cell in cells[2:-1]:
                raw = cell.get_text(" ", strip=True)
                value = number(raw) if raw else 0.0
                if value is None:
                    break
                values.append(value)
            if len(values) < 4 or len(values) != len(cells) - 3 or abs(sum(values) - total) > 0.01:
                continue
        rows.append([rank, name, str(int(total)) if total.is_integer() else str(total)])
    if len(rows) < minimum:
        return []
    if any(float(rows[i][2]) < float(rows[i+1][2]) for i in range(len(rows)-1)):
        return []
    # Ties are legitimate in WEC. Rank numbers must never decrease.
    if any(int(rows[i][0]) > int(rows[i+1][0]) for i in range(len(rows)-1)):
        return []
    return rows

def main():
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    manifest_path = OUT / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    pages = {}
    for series, (slug, identity, minimum, filename, require_sum) in SOURCES.items():
        url = f"https://www.fia.com/events/{slug}/season-{YEAR}/standings"
        if slug not in pages:
            try:
                pages[slug] = fetch_html(url)
            except Exception as exc:
                print(slug, "source unavailable; preserving snapshots:", exc)
                pages[slug] = None
        soup = pages[slug]
        if soup is None:
            continue
        candidates = [parse(table, identity, minimum, require_sum) for table in soup.select("table")]
        # The first matching table is the top-level championship, not WRC2/LMGT3.
        rows = next((r for r in candidates if r), None)
        if not rows:
            print(series, "no verified top-class table; preserving snapshot")
            continue
        snapshot = {
            "series": series, "season": YEAR, "source_url": url, "official_url": url,
            "retrieved_at": now, "provider": "FIA official championship standings",
            "reuse_review_required": True,
            "data": {"headers": ["Position", identity[:-1] if identity.endswith("s") else identity, "Points"], "rows": rows},
            "points_audit": {
                "status": "officially_verified",
                "method": ("FIA per-round awarded points sum reconciled with FIA total" if require_sum
                           else "published FIA points total; rally bonus and eligibility rules not independently recalculated"),
                "rows_checked": len(rows), "verification_source": url,
                "verification_date": dt.datetime.now(dt.timezone.utc).date().isoformat(),
            },
        }
        path = OUT / f"{filename}-{YEAR}.json"
        path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        entry = manifest.setdefault("series", {}).setdefault(series, {"seasons": {}})
        entry.setdefault("seasons", {})[str(YEAR)] = "/data/standings/" + path.name
        entry.update({"official_url": url, "provider": "FIA official standings (reuse review required)",
                      "reuse_review_required": True})
        print(series, "published", len(rows), "rows from FIA source")
    manifest["updated"] = now
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")

# Development-only source refresh; preserve snapshots on source failure.
if __name__ == "__main__":
    main()
