#!/usr/bin/env python3
"""Audit and, when necessary, derive IMSA points from complete per-round scores.

Never infer other championships' scoring rules, bonus points, dropped rounds,
playoff resets, or penalties. Only sum an explicit points-by-event source table.
"""
import datetime as dt
import json
import pathlib
from decimal import Decimal, InvalidOperation

ROOT = pathlib.Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / "data" / "standings"


def numeric(value):
    if isinstance(value, bool) or value is None:
        raise ValueError("Missing/non-numeric round score")
    raw = str(value).replace(",", "").strip()
    if not raw or raw in ("—", "-", "DNS", "DNF"):
        raise ValueError("Missing/non-numeric round score")
    try:
        number = Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError("Non-numeric round score: " + raw) from exc
    if not number.is_finite() or number < 0:
        raise ValueError("Invalid points: " + raw)
    return number


def audit_imsa(snapshot):
    if snapshot.get("series") != "IMSA":
        raise ValueError("Not an IMSA snapshot")
    table = snapshot.get("data", {})
    headers, rows = table.get("headers"), table.get("rows")
    if not isinstance(headers, list) or not isinstance(rows, list) or len(rows) < 3:
        raise ValueError("Incomplete standings table")
    normalized = [str(h).strip().lower() for h in headers]
    if len(normalized) < 6 or normalized[:2] != ["rank", "drivers"] or normalized[-1] != "total":
        raise ValueError("Unexpected IMSA table format; manual review required")
    rounds = list(range(2, len(headers) - 1))
    if len(rounds) < 3 or any(not str(headers[i]).strip() for i in rounds):
        raise ValueError("Insufficient identified scoring rounds")
    calculated = 0
    for row in rows:
        if not isinstance(row, list) or len(row) != len(headers) or not str(row[1]).strip():
            raise ValueError("Incomplete IMSA competitor row")
        total = sum((numeric(row[i]) for i in rounds), Decimal(0))
        published = str(row[-1]).strip()
        if published:
            if numeric(published) != total:
                raise ValueError("Published total does not equal sum of rounds for " + str(row[1]))
        else:
            row[-1] = format(total, "f")
            calculated += 1
    snapshot["points_audit"] = {
        "status": "calculated_from_complete_round_columns" if calculated else "verified_against_published_total",
        "method": "Sum of every explicitly provided per-round points value; incomplete rows rejected",
        "rows_checked": len(rows),
        "rounds_checked": len(rounds),
        "calculated_totals": calculated,
        "checked_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "scoring_scope": "Only the specific IMSA standings class represented in this table",
    }
    return snapshot


def main():
    year = dt.datetime.now(dt.timezone.utc).year
    path = DIRECTORY / f"imsa-{year}.json"
    if not path.exists():
        print("No current-year IMSA snapshot to audit")
        return
    original = json.loads(path.read_text(encoding="utf-8"))
    result = audit_imsa(original)
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("IMSA audited:", result["points_audit"]["rows_checked"], "drivers over",
          result["points_audit"]["rounds_checked"], "rounds; totals calculated:",
          result["points_audit"]["calculated_totals"])


if __name__ == "__main__":
    main()
