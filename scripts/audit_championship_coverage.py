#!/usr/bin/env python3
"""Audit 23-series development coverage without inventing missing race/points data.

A snapshot's presence is not proof of accuracy, licensing or completeness.
This report deliberately distinguishes available data from independently verified data.
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
}
NASCAR_PREFIX = {'NASCAR Cup':'CUP —','NASCAR O’Reilly':'XFINITY —','NASCAR Trucks':'TRUCK —'}

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
    return {'status':'points_available_not_independently_verified',
            'rows':valid,'source_url':snapshot.get('source_url'),
            'retrieved_at':snapshot.get('retrieved_at'),
            'calculation_audit':snapshot.get('points_audit')}

def race_audit(series,entry):
    url=entry.get('race_results_seasons',{}).get(str(YEAR))
    if not url and series in ('Formula E','WRC'):
        url=entry.get('seasons',{}).get(str(YEAR))
    path=file_for_url(url)
    snapshot=load(path) if path else None
    if not isinstance(snapshot,dict):
        return {'status':'missing'}
    data=snapshot.get('data')
    items=data if isinstance(data,list) else (data.get('results') if isinstance(data,dict) else None)
    if not isinstance(items,list):
        return {'status':'missing'}
    count=sum(isinstance(x,dict) and bool(x.get('winning_driver')) for x in items)
    return {'status':'winner_summaries_available_not_full_classifications' if count else 'missing','count':count}

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
            'individual_race_results':race_audit(series,entry),
        }
    # Completion requires a future, explicit independent verification step for
    # classification completeness, scoring adjustments and publication rights.
    report={
        'generated_at':dt.datetime.now(dt.timezone.utc).isoformat(),
        'season':YEAR,'target_championships':len(SERIES),
        'points_tables_available':sum(v['championship_points']['status']=='points_available_not_independently_verified' for v in coverage.values()),
        'calendar_feeds_present':sum(v['calendar']['status']!='missing' for v in coverage.values()),
        'race_winner_feeds_present':sum(v['individual_race_results']['status']!='missing' for v in coverage.values()),
        'fully_verified_championships':0,
        'complete':False,
        'note':'Presence is not verification. Complete classification data, season-specific scoring/penalties, organizer cross-check and source permissions remain required.',
        'championships':coverage,
    }
    out=ROOT/'data'/'coverage.json'
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Coverage audit:',report['points_tables_available'],'points tables,',report['calendar_feeds_present'],'calendars,',report['race_winner_feeds_present'],'race-winner feeds of',len(SERIES),'championships.')

if __name__=='__main__':
    main()
