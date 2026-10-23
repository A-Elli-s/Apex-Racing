#!/usr/bin/env python3
"""Compute F3 team standings by summing all assigned drivers' championship points.

Requires a complete season-specific roster including substitutions and a
verified totals cross-check. Never guesses roster membership or tiebreaks.
"""
import datetime as dt
import json
import pathlib
from decimal import Decimal, InvalidOperation

ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/'data'/'standings'


def calculate(drivers,roster):
    if drivers.get('series')!='F3' or drivers.get('season')!=roster.get('season'):
        raise ValueError('Season or series mismatch')
    data=drivers.get('data',{})
    if data.get('headers')!=['Position','Driver','Points']:
        raise ValueError('Unexpected driver standings schema')
    rows=data.get('rows',[])
    if len(rows)<20 or len(rows)>50:
        raise ValueError('Driver standings incomplete')
    by_driver={}
    for rank,name,points in rows:
        if not name or name in by_driver:
            raise ValueError('Missing or duplicate driver')
        try:score=Decimal(str(points))
        except InvalidOperation as error:raise ValueError('Invalid driver points') from error
        if not score.is_finite() or score<0:
            raise ValueError('Invalid driver points')
        by_driver[name]=score
    teams=roster.get('teams',{})
    if not isinstance(teams,dict) or len(teams)<8:
        raise ValueError('Incomplete team roster')
    assigned=[name for drivers_list in teams.values() for name in drivers_list]
    if len(assigned)!=len(set(assigned)) or set(assigned)!=set(by_driver):
        missing=set(by_driver)-set(assigned)
        extra=set(assigned)-set(by_driver)
        raise ValueError('Team roster does not cover every driver: missing='+repr(sorted(missing))+' extra='+repr(sorted(extra)))
    totals={team:sum((by_driver[name] for name in names),Decimal(0)) for team,names in teams.items()}
    expected=roster.get('verified_totals',{})
    if set(expected)!=set(totals) or any(totals[t]!=Decimal(str(expected[t])) for t in totals):
        raise ValueError('Calculated team points differ from independently checked totals; preserve last snapshot')
    ordered=sorted(totals.items(),key=lambda x:(-x[1],x[0]))
    if len(set(totals.values()))!=len(totals):
        raise ValueError('Points tied; championship tiebreaker must be checked')
    return {'headers':['Position','Team','Points'],
            'rows':[[str(i),team,str(int(score)) if score==int(score) else str(score)]
                    for i,(team,score) in enumerate(ordered,1)]}


def main():
    year=dt.datetime.now(dt.timezone.utc).year
    roster_path=OUT/('f3-team-roster-'+str(year)+'.json')
    if not roster_path.exists():
        print('No verified F3 team roster for',year,'; no data published')
        return
    roster=json.loads(roster_path.read_text(encoding='utf-8'))
    manifest_path=OUT/'manifest.json'
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    path=manifest.get('series',{}).get('F3',{}).get('seasons',{}).get(str(year))
    if not path or not path.endswith('f3-standings-'+str(year)+'.json'):
        print('No licensed F3 driver points snapshot; no data published')
        return
    drivers=json.loads((ROOT/path.lstrip('/')).read_text(encoding='utf-8'))
    data=calculate(drivers,roster)
    now=dt.datetime.now(dt.timezone.utc).isoformat()
    snapshot={'series':'F3 Teams','season':year,'source_url':drivers['source_url'],
              'official_url':'https://www.fiaformula3.com/en/standings/'+str(year)+'/teams',
              'retrieved_at':now,'data':data,
              'provider':'Calculated from community driver championship points and verified season roster',
              'attribution':'Wikipedia contributors','license':'CC BY-SA 4.0',
              'license_url':drivers['license_url'],
              'points_audit':{'status':'calculated_and_cross_checked',
                              'method':'sum of each rostered driver championship points including substitutes',
                              'roster_source':roster['source_url'],
                              'verification_source':roster['verification_source_url'],
                              'verification_date':roster['verification_date'],
                              'rows_checked':len(data['rows'])}}
    dest=OUT/('f3-teams-'+str(year)+'.json')
    dest.write_text(json.dumps(snapshot,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    entry=manifest.setdefault('series',{}).setdefault('F3 Teams',{'seasons':{}})
    entry.update({'official_url':snapshot['official_url'],'provider':snapshot['provider'],
                  'attribution':snapshot['attribution'],'license_url':snapshot['license_url']})
    entry.setdefault('seasons',{})[str(year)]='/data/standings/'+dest.name
    manifest['updated']=now
    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('F3 team points calculated and cross-checked:',len(data['rows']))


if __name__=='__main__':main()
