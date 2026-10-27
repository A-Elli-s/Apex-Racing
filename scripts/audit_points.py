#!/usr/bin/env python3
"""Audit or reconstruct standings totals from *awarded* per-event points.

Never turn finishing positions into points without a series/season scoring model.
Never infer a complete season from winner-only or partial classifications.
The output is intended for the Apex Racing World development branch only.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STANDINGS = ROOT / 'data' / 'standings'


def number(value):
    value = str(value).strip().replace(',', '')
    if not value or value in ('—', '–', '-', 'N/A'):
        raise ValueError('Missing event points')
    try:
        result = Decimal(value)
    except InvalidOperation as error:
        raise ValueError('Non-numeric awarded points: ' + repr(value)) from error
    if not result.is_finite():
        raise ValueError('Non-finite awarded points')
    return result


def display(value):
    value = format(value, 'f')
    return value.rstrip('0').rstrip('.') if '.' in value else value


def audit_snapshot(snapshot, checked_at):
    """Return (changed, outcome), mutating only fully validated snapshots.

    For IMSA, per-event columns are the points awarded at each round.
    Other championships must explicitly identify awarded-points columns
    and verify that adjustments and all completed events are included.
    """
    data = snapshot.get('data')
    if not isinstance(data, dict):
        return False, 'no points table'
    headers, rows = data.get('headers'), data.get('rows')
    if not isinstance(headers, list) or not isinstance(rows, list) or len(rows) < 3:
        return False, 'no complete points table'
    if len(set(headers)) != len(headers):
        return False, 'duplicate column headings'

    series = snapshot.get('series')
    total_names = ('Total', 'Points', 'Pts', 'Championship points')
    total_indices = [i for i, header in enumerate(headers) if str(header).strip() in total_names]
    if len(total_indices) > 1:
        return False, 'ambiguous totals'
    total_index = total_indices[0] if total_indices else None

    if series == 'IMSA' and 'Drivers' in headers and total_index is not None:
        start = headers.index('Drivers') + 1
        event_columns = headers[start:total_index]
        if len(event_columns) < 2:
            return False, 'insufficient IMSA event columns'
    else:
        event_columns = data.get('awarded_points_columns', [])
        if not isinstance(event_columns, list) or len(event_columns) < 2:
            return False, 'no declared awarded-event-points columns'
        if not data.get('points_include_adjustments', False):
            return False, 'bonuses and penalties not confirmed'
        if not data.get('source_complete_through'):
            return False, 'source completeness not confirmed'

    try:
        indices = [headers.index(col) for col in event_columns]
    except ValueError:
        return False, 'declared event column missing'
    if len(indices) != len(set(indices)) or total_index in indices:
        return False, 'invalid event column selection'

    computed = []
    try:
        for row in rows:
            if not isinstance(row, list) or len(row) != len(headers):
                raise ValueError('row length mismatch')
            computed.append(sum((number(row[i]) for i in indices), Decimal(0)))
    except ValueError as error:
        return False, str(error)

    if total_index is not None:
        try:
            mismatches = [i for i, (row, value) in enumerate(zip(rows, computed))
                          if number(row[total_index]) != value]
        except ValueError as error:
            return False, 'invalid published total: ' + str(error)
        if mismatches:
            return False, 'published total disagrees with event sum for ' + str(len(mismatches)) + ' rows'
        outcome = 'verified_against_published_total'
    else:
        if not data.get('source_complete_through') or not data.get('points_include_adjustments'):
            return False, 'cannot safely reconstruct total'
        headers.append('Total')
        for row, value in zip(rows, computed):
            row.append(display(value))
        outcome = 'calculated_from_awarded_event_points'

    audit = {
        'status': outcome,
        'method': 'sum of already-awarded event points; not finishing positions',
        'event_columns': event_columns,
        'rows_checked': len(rows),
        'checked_at': checked_at,
    }
    changed = snapshot.get('points_audit') != audit
    snapshot['points_audit'] = audit
    return changed, outcome


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--write', action='store_true')
    parser.add_argument('--season', type=int, default=dt.datetime.now(dt.timezone.utc).year)
    args = parser.parse_args()
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    audited = 0
    for path in sorted(STANDINGS.glob('*-' + str(args.season) + '.json')):
        try:
            snapshot = json.loads(path.read_text(encoding='utf-8'))
            changed, status = audit_snapshot(snapshot, now)
            print(path.name, status)
            if changed and args.write:
                path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            if status in ('verified_against_published_total', 'calculated_from_awarded_event_points'):
                audited += 1
        except (OSError, ValueError, json.JSONDecodeError) as error:
            print(path.name, 'not audited:', error)
    print('Audited current-season snapshots:', audited)


if __name__ == '__main__':
    main()
