#!/usr/bin/env python3
"""Render data/quality/freshness.json as a Markdown action list.

Prints nothing and exits 0 when every series is current, so a caller can use
empty output to mean "nothing to report".
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]

SECTIONS = (
    ("automatic", "Bots should have refreshed these",
     "A collector exists for these but the snapshot is still behind the calendar. "
     "Check the latest *Schedule racing data bots* run for the failing step."),
    ("manual", "Needs a manual update",
     "The organizer's pages block automated access. Update the snapshot after the "
     "round and record the source and as-of date."),
    ("barred", "Link only (rights pending)",
     "No bot may collect these (see `data/quality/source-permissions-2026.json`). "
     "Nothing to do unless permission has been obtained."),
)


def build(freshness, manifest=None):
    manifest = manifest or {}
    stale = [r for r in freshness.get("series", []) if r.get("stale")]
    if not stale:
        return ""
    lines = ["Standings snapshots that predate a completed championship round "
             f"(checked {freshness.get('as_of', 'today')}).",
             "This is a currency check only; it does not verify any points.", ""]
    for path, title, hint in SECTIONS:
        rows = [r for r in stale if r.get("refresh_path") == path]
        if not rows:
            continue
        lines += [f"### {title}", hint, ""]
        for r in rows:
            link = manifest.get("series", {}).get(r["series"], {}).get("official_url")
            where = f" — [official standings]({link})" if link else ""
            lines.append(f"- [ ] **{r['series']}**: snapshot from {r.get('retrieved_utc_date')}, "
                         f"last scheduled round {r.get('latest_scheduled_round_date')}{where}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main():
    freshness = json.loads((ROOT / "data/quality/freshness.json").read_text(encoding="utf-8"))
    manifest_path = ROOT / "data/standings/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    sys.stdout.write(build(freshness, manifest))


if __name__ == "__main__":
    main()
