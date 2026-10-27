#!/usr/bin/env python3
"""Audit all current-season standings snapshots and independently sourced alternatives.

Does not claim agreement when only one source is available. Never changes points.
Output is a machine-readable QA report for the development website.
"""
import datetime as dt
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/'data/standings/manifest.json'
OUT=ROOT/'data/quality/standings-audit.json'
YEAR=dt.datetime.now(dt.timezone.utc).year
SERIES=('F1','F2','F3','IndyCar','NASCAR Cup','NASCAR O’Reilly','WEC','IMSA','Formula E','WRC','Supercars','NHRA','MotoGP','Moto2','Moto3','WorldSBK','Supercross','Pro Motocross','MXGP','NASCAR Trucks','Dakar Rally','Off-road racing','Monster Jam')

def points_table(data):
    if not isinstance(data,dict):return None
    headers=data.get('headers')
    rows=data.get('rows')
    if not isinstance(headers,list) or not isinstance(rows,list):return None
    ix=next((i for i,h in enumerate(headers) if str(h).strip().lower() in ('points','pts','pt','total','total points')),None)
    if ix is None:return None
    checked=[]
    for row in rows:
        if not isinstance(row,list) or len(row)!=len(headers):continue
        try: score=float(str(row[ix]).replace(',',''))
        except (ValueError,TypeError):continue
        if score<0:continue
        checked.append(score)
    return checked if len(checked)>=3 else None

def main():
    manifest=json.loads(MANIFEST.read_text(encoding='utf-8'))
    entries={}
    for series in SERIES:
        entry=manifest.get('series',{}).get(series,{})
        path=entry.get('seasons',{}).get(str(YEAR))
        item={'status':'missing','source_count':0,'independently_verified':False,'official_url':entry.get('official_url')}
        if path:
            local=ROOT/path.lstrip('/')
            try:
                snapshot=json.loads(local.read_text(encoding='utf-8'))
                if snapshot.get('series')!=series or snapshot.get('season')!=YEAR:raise ValueError('series/year mismatch')
                scores=points_table(snapshot.get('data'))
                if scores is None:
                    item['status']='not_a_points_table'
                else:
                    item['status']='single_source_unverified'
                    item['competitors']=len(scores)
                    item['leader_points']=scores[0]
                    item['source_count']=1
                    item['source_url']=snapshot.get('source_url')
                    item['retrieved_at']=snapshot.get('retrieved_at')
            except (OSError,ValueError,TypeError,KeyError) as exc:
                item['status']='invalid_snapshot'
                item['error']=str(exc)[:150]
        entries[series]=item
    OUT.parent.mkdir(parents=True,exist_ok=True)
    report={'generated_at':dt.datetime.now(dt.timezone.utc).isoformat(),'season':YEAR,
            'method':'structural validation; independent cross-source verification pending',
            'summary':{status:sum(x['status']==status for x in entries.values()) for status in ('missing','invalid_snapshot','not_a_points_table','single_source_unverified')},
            'series':entries}
    OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Standings quality audit:',report['summary'])

if __name__=='__main__':main()
