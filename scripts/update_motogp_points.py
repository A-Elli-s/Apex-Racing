#!/usr/bin/env python3
"""Aggregate MotoGP, Moto2 and Moto3 points from complete MotoDB session data."""
import json
from datetime import datetime, date, timezone
from decimal import Decimal
from collections import defaultdict
from pathlib import Path
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]
BASE='https://raw.githubusercontent.com/vishwapramuditha/moto-db/main/data/motogp'
CLASSES={'MotoGP':'motogp','Moto2':'moto2','Moto3':'moto3'}

def fetch(url):
    with urlopen(Request(url,headers={'User-Agent':'ApexRacingWorld/1.0'}),timeout=25) as res:
        raw=res.read(2_000_001)
    if len(raw)>2_000_000:raise ValueError('oversize data')
    return json.loads(raw)

def collect(series,slug,events,year):
    scores=defaultdict(Decimal);names={};teams={};wins=defaultdict(int);races=[]
    for event in events:
        for session in (('SPR','RAC') if series=='MotoGP' else ('RAC',)):
            code=event['short_name']
            url=f'{BASE}/{year}/{code}/{slug}_{session}.json'
            doc=fetch(url)
            if str(doc.get('season'))!=str(year) or doc.get('event',{}).get('short_name')!=code or doc.get('session',{}).get('type')!=session:raise ValueError('session mismatch '+url)
            results=doc.get('results')
            if not isinstance(results,list) or len(results)<10:raise ValueError('missing race '+url)
            seen=set();rows=[]
            for r in results:
                rider=r.get('rider') or {};rid=rider.get('id') or rider.get('legacy_id');name=rider.get('full_name')
                if not rid or not name or rid in seen:raise ValueError('invalid rider '+url)
                seen.add(rid)
                p=r.get('points')
                if p is None or isinstance(p,bool):raise ValueError('missing points '+url)
                pts=Decimal(str(p))
                if not pts.is_finite() or pts<0:raise ValueError('invalid points '+url)
                scores[rid]+=pts;names[rid]=name;teams[rid]=(r.get('team') or {}).get('name') or '—'
                if session=='RAC' and r.get('position')==1:wins[rid]+=1
                rows.append([r.get('position') if r.get('position') is not None else 'NC',name,teams[rid],str(pts)])
            races.append({'event':event['name'],'date':event['date_end'],'session':'Sprint' if session=='SPR' else 'Grand Prix','source_url':url,'headers':['Finish','Rider','Team','Awarded points'],'rows':rows})
    if len(scores)<12:raise ValueError('incomplete rider field')
    order=sorted(scores,key=lambda rid:(-scores[rid],-wins[rid],names[rid]))
    rows=[];last=None;rank=0
    for i,rid in enumerate(order,1):
        if scores[rid]!=last:rank=i
        rows.append([rank,names[rid],teams[rid],str(scores[rid]),wins[rid]])
        last=scores[rid]
    return {'headers':['Points order','Rider','Latest team','Points','Grand Prix wins'],'rows':rows,'race_results':races,'provisional':True,'calculation':'Sum of source-awarded race and sprint points','caveat':'Equal-points riders share a points rank; official countback and later sanctions are not independently verified.','coverage':{'completed_rounds':len(events),'included_rounds':len(events),'sessions':len(races),'expected_sessions':len(events)*(2 if series=='MotoGP' else 1)}}

def main():
    now=datetime.now(timezone.utc);year=now.year
    url=f'{BASE}/{year}/schedule.json';schedule=fetch(url)
    events=schedule.get('events')
    if not isinstance(events,list) or len(events)<10:raise ValueError('incomplete calendar')
    finished=[];seen=set()
    for e in events:
        if e.get('test'):continue
        code=e.get('short_name');end=e.get('date_end')
        if not code or not end or code in seen:raise ValueError('invalid calendar round')
        seen.add(code);day=date.fromisoformat(end)
        if day.year!=year:continue
        if day<=now.date() and e.get('status') not in ('FINISHED','CANCELLED','CANCELED'):raise ValueError('past round unfinalized '+code)
        if day<=now.date() and e.get('status')=='FINISHED':finished.append(e)
    if not finished:raise ValueError('no completed rounds')
    finished.sort(key=lambda e:e['date_end'])
    out=ROOT/'data'/'standings';manifest_path=out/'manifest.json'
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    count=0
    for series,slug in CLASSES.items():
        try:
            data=collect(series,slug,finished,year)
            snapshot={'series':series,'season':year,'source_url':url,'official_url':'https://www.motogp.com/en/results','retrieved_at':now.isoformat(),'provider':'MotoDB community classifications (CC0)','data':data}
            (out/f'{slug}-{year}.json').write_text(json.dumps(snapshot,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            item=manifest['series'].setdefault(series,{'seasons':{}})
            item['official_url']=snapshot['official_url'];item['provider']=snapshot['provider']
            item.setdefault('seasons',{})[str(year)]=f'/data/standings/{slug}-{year}.json'
            print('Validated',series,len(data['rows']),'riders',len(finished),'rounds')
            count+=1
        except Exception as e:print('Preserved prior data for',series,str(e))
    if count:
        manifest['updated']=now.isoformat()
        manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if count<3:print('Some classes unavailable; not fabricating totals')

if __name__=='__main__':main()
