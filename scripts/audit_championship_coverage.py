#!/usr/bin/env python3
"""Audit 23-series development coverage without inventing missing race/points data.

A snapshot's presence is not proof of accuracy, licensing or completeness.
This report deliberately distinguishes available data from independently verified data.
Run after every dev-branch calendar or standings refresh.
"""
import datetime as dt
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
YEAR = dt.datetime.now(dt.timezone.utc).year
SERIES = [
    'F1','F2','F3','IndyCar','NASCAR Cup','NASCAR O’Reilly','WEC','IMSA',
    'Formula E','WRC','Supercars','NHRA','MotoGP','Moto2','Moto3','WorldSBK',
    'Supercross','Pro Motocross','MXGP','NASCAR Trucks','Dakar Rally',
    'Off-road racing','Monster Jam'
]
CALENDAR_KEYS = {
    'F1':'Formula 1','F2':'Formula 2','F3':'Formula 3',
    'NASCAR Cup':'NASCAR Cup / O’Reilly / Trucks',
    'NASCAR O’Reilly':'NASCAR Cup / O’Reilly / Trucks',
    'NASCAR Trucks':'NASCAR Cup / O’Reilly / Trucks',
    'MotoGP':'MotoGP / Moto2 / Moto3','Moto2':'MotoGP / Moto2 / Moto3',
    'Moto3':'MotoGP / Moto2 / Moto3',
    'Off-road racing':'SCORE Off-road',
}
NASCAR_PREFIX = {'NASCAR Cup':'CUP —','NASCAR O’Reilly':'O’REILLY —','NASCAR Trucks':'TRUCK —'}

def load(path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None

def file_for_url(url):
    if not isinstance(url,str) or not url.startswith('/data/standings/'):
        return None
    name=url.split('/')[-1]
    if name in ('.','..') or '/' in name or not name.endswith('.json'):
        return None
    return ROOT/'data'/'standings'/name

def points_audit(series, entry):
    url=entry.get('seasons',{}).get(str(YEAR))
    path=file_for_url(url)
    snapshot=load(path) if path else None
    if not isinstance(snapshot,dict):
        return {'status':'missing','reason':'No current-season points snapshot'}
    data=snapshot.get('data')
    if snapshot.get('series')!=series or str(snapshot.get('season'))!=str(YEAR):
        return {'status':'invalid','reason':'Series or season mismatch'}
    if not isinstance(data,dict):
        return {'status':'not_points','reason':'Snapshot contains no championship points table'}
    headers=data.get('headers')
    rows=data.get('rows')
    if not isinstance(headers,list) or not isinstance(rows,list) or len(rows)<3:
        return {'status':'not_points','reason':'No complete points-table structure'}
    points_index=next((i for i,h in enumerate(headers) if str(h).strip().lower() in ('points','point','pts','total')),None)
    if points_index is None:
        return {'status':'not_points','reason':'No explicit points-total column'}
    valid=0
    for row in rows:
        if not isinstance(row,list) or len(row)!=len(headers):
            continue
        try:
            points=float(str(row[points_index]).replace(',','').strip())
            if points>=0 and points<10000000:
                valid+=1
        except (ValueError,TypeError):
            pass
    if valid<3 or valid<len(rows):
        return {'status':'invalid','reason':f'Numeric totals in only {valid}/{len(rows)} rows'}
    if entry.get('partial_field'):
        return {'status':'partial_points_table_not_complete','rows':valid,
                'reason':'Manifest explicitly marks this championship field partial'}
    return {'status':'points_available_not_independently_verified',
            'rows':valid,'source_url':snapshot.get('source_url'),
            'retrieved_at':snapshot.get('retrieved_at'),
            'calculation_audit':snapshot.get('points_audit')}

def race_audit(series, entry, races):
    """Count classifications conservatively; three ranked entries do not prove a season.

    All completed scheduled events must be represented before a structural
    completeness claim. Organizer verification, penalties, sprints, and source
    rights remain separate mandatory release gates.
    """
    url = entry.get('race_results_seasons', {}).get(str(YEAR))
    if not url and series in ('Formula E', 'WRC'):
        url = entry.get('seasons', {}).get(str(YEAR))
    path = file_for_url(url)
    snapshot = load(path) if path else None
    if not isinstance(snapshot, dict) or snapshot.get('series') != series or str(snapshot.get('season')) != str(YEAR):
        return {'status': 'missing'}
    data = snapshot.get('data')
    items = data if isinstance(data, list) else (data.get('results') if isinstance(data, dict) else None)
    if not isinstance(items, list):
        return {'status': 'missing'}

    today = dt.datetime.now(dt.timezone.utc).date()
    key = CALENDAR_KEYS.get(series, series)
    calendar = races.get(key, [])
    if not isinstance(calendar, list):
        calendar = []
    if series in NASCAR_PREFIX:
        calendar = [x for x in calendar if isinstance(x, dict) and
                    str(x.get('name', '')).startswith(NASCAR_PREFIX[series])]
    completed_calendar_events = 0
    for event in calendar:
        if not isinstance(event, dict):
            continue
        try:
            day = dt.date.fromisoformat(str(event.get('date')))
        except (ValueError, TypeError):
            continue
        if day < today and day.year in ((YEAR - 1, YEAR) if series == 'Formula E' else (YEAR,)):
            completed_calendar_events += 1

    classified = 0
    seen_events = set()
    for event in items:
        if not isinstance(event, dict):
            continue
        event_id = str(event.get('round') or event.get('event') or event.get('eprix') or '').strip()
        competitors = event.get('classification') or event.get('results')
        if not event_id or event_id in seen_events or not isinstance(competitors, list) or len(competitors) < 3:
            continue
        positions = []
        for competitor in competitors:
            if not isinstance(competitor, dict):
                break
            try:
                position = int(competitor.get('position', competitor.get('rank')))
                if position < 1:
                    break
                positions.append(position)
            except (ValueError, TypeError):
                break
        if len(positions) != len(competitors) or len(set(positions)) != len(positions):
            continue
        seen_events.add(event_id)
        classified += 1

    if classified:
        # No calendar, fewer classified events than completed rounds, or an
        # unverified race-by-race mapping is not a complete season.
        status = ('candidate_classifications_require_round_and_official_review'
                  if completed_calendar_events and classified >= completed_calendar_events
                  else 'partial_classifications_not_complete')
        return {'status': status, 'classified_events': classified,
                'completed_calendar_events': completed_calendar_events}
    count = sum(isinstance(x, dict) and bool(x.get('winning_driver')) for x in items)
    return {'status': 'winner_summaries_available_not_full_classifications' if count else 'missing',
            'count': count, 'completed_calendar_events': completed_calendar_events}

def calendar_audit(series,races):
    key=CALENDAR_KEYS.get(series,series)
    items=races.get(key,[])
    if not isinstance(items,list):
        items=[]
    if series in NASCAR_PREFIX:
        items=[x for x in items if isinstance(x,dict) and str(x.get('name','')).startswith(NASCAR_PREFIX[series])]
    count=0
    for x in items:
        if not isinstance(x,dict) or not x.get('name') or not x.get('url'):
            continue
        try:
            when=dt.date.fromisoformat(str(x.get('date')))
        except (TypeError,ValueError):
            continue
        if when.year in (YEAR,YEAR-1 if series=='Formula E' else YEAR):
            count+=1
    if not count:
        return {'status':'missing','events':0}
    if count < 3:
        return {'status':'partial_calendar_entries_not_verified','events':count}
    if series in ('MotoGP','Moto2','Moto3'):
        return {'status':'shared_calendar_not_class_verified','events':count}
    if series=='NASCAR O’Reilly':
        return {'status':'legacy_xfinity_labels_need_validation','events':count}
    return {'status':'calendar_entries_present_not_independently_verified','events':count}

def main():
    manifest=load(ROOT/'data'/'standings'/'manifest.json') or {}
    races=load(ROOT/'data'/'races.json') or {}
    entries=manifest.get('series',{})
    calendar=races.get('series',{})
    coverage={}
    for series in SERIES:
        entry=entries.get(series,{})
        coverage[series]={
            'calendar':calendar_audit(series,calendar),
            'championship_points':points_audit(series,entry),
            'individual_race_results':race_audit(series,entry,calendar),
        }
    # A source cannot become "verified" merely because a JSON file exists.
    # Independent reviews must be recorded explicitly in the manifest entry.
    verified_count=0
    for series in SERIES:
        review=entries.get(series,{}).get('verification',{})
        present=coverage[series]
        reviewed=(
            review.get('season')==YEAR
            and review.get('points')=='cross_checked'
            and review.get('calendar')=='cross_checked'
            and review.get('race_results')=='complete_classifications_checked'
            and review.get('rights')=='approved'
            and review.get('race_round_mapping')=='cross_checked'
            and entries.get(series,{}).get('commercial_reuse_cleared') is True
            and not entries.get(series,{}).get('reuse_review_required')
        )
        available=(
            present['championship_points']['status']=='points_available_not_independently_verified'
            and present['calendar']['status']=='calendar_entries_present_not_independently_verified'
            and present['individual_race_results']['status']=='candidate_classifications_require_round_and_official_review'
        )
        verified=bool(reviewed and available)
        coverage[series]['fully_verified']=verified
        if verified:
            verified_count+=1
    report={
        'generated_at':dt.datetime.now(dt.timezone.utc).isoformat(),
        'season':YEAR,'target_championships':len(SERIES),
        'points_tables_available':sum(v['championship_points']['status']=='points_available_not_independently_verified' for v in coverage.values()),
        'calendar_feeds_present':sum(v['calendar']['status']!='missing' for v in coverage.values()),
        'race_winner_feeds_present':sum(v['individual_race_results']['status']=='winner_summaries_available_not_full_classifications' for v in coverage.values()),
        'partial_classification_feeds_present':sum(v['individual_race_results']['status'] in ('partial_classifications_not_complete','candidate_classifications_require_round_and_official_review') for v in coverage.values()),
        'fully_verified_championships':verified_count,
        'complete':verified_count==len(SERIES),
        'note':'Presence is not verification. Complete classification data, season-specific scoring/penalties, organizer cross-check and source permissions must be recorded in each series verification manifest before completion.',
        'championships':coverage,
    }
    out=ROOT/'data'/'quality'/'championship-coverage.json'
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Coverage audit:',report['points_tables_available'],'points tables,',report['calendar_feeds_present'],'calendars,',report['race_winner_feeds_present'],'race-winner feeds of',len(SERIES),'championships.')

if __name__=='__main__':
    main()
