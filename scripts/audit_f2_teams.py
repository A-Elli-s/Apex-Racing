#!/usr/bin/env python3
"""Calculate F2 teams from all rostered drivers and audit published team totals."""
import datetime as dt
import json
import pathlib
from decimal import Decimal, InvalidOperation

ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/'data'/'standings'


def calculate(drivers,roster):
    if drivers.get('series')!='F2' or drivers.get('season')!=roster.get('season'):
        raise ValueError('Wrong series or season')
    data=drivers.get('data',{})
    if data.get('headers')!=['Position','Driver','Points'] or len(data.get('rows',[]))<18:
        raise ValueError('Incomplete F2 driver championship table')
    points={}
    for pos,name,total in data['rows']:
        if name in points or not name:
            raise ValueError('Duplicate/missing driver')
        try:score=Decimal(str(total))
        except InvalidOperation as error:raise ValueError('Invalid driver points') from error
        if not score.is_finite() or score<0:raise ValueError('Invalid driver points')
        points[name]=score
    teams=roster.get('teams',{})
    assigned=[name for names in teams.values() for name in names]
    if len(teams)<8 or len(assigned)!=len(set(assigned)) or set(assigned)!=set(points):
        raise ValueError('Incomplete or duplicated season roster')
    totals={team:sum((points[name] for name in names),Decimal(0)) for team,names in teams.items()}
    if len(set(totals.values()))!=len(totals):
        raise ValueError('Team points tied; cannot infer official tiebreak order')
    return [[str(i),team,str(int(score)) if score==int(score) else str(score)]
            for i,(team,score) in enumerate(sorted(totals.items(),key=lambda x:-x[1]),1)]


def audit_published(published,computed):
    if published.get('series')!='F2 Teams':
        raise ValueError('Wrong published series')
    data=published.get('data',{})
    if data.get('headers')!=['Position','Team','Points']:
        raise ValueError('Wrong published team schema')
    rows=data.get('rows',[])
    if len(rows)!=len(computed):
        raise ValueError('Published teams count mismatch')
    if rows!=computed:
        raise ValueError('Published team totals or positions differ from sum of drivers; preserve snapshot')
    return True


def main():
    year=dt.datetime.now(dt.timezone.utc).year
    roster_path=OUT/('f2-team-roster-'+str(year)+'.json')
    driver_path=OUT/('f2-standings-'+str(year)+'.json')
    if not roster_path.exists() or not driver_path.exists():
        print('No complete licensed F2 roster and driver points; no totals calculated')
        return
    roster=json.loads(roster_path.read_text(encoding='utf-8'))
    drivers=json.loads(driver_path.read_text(encoding='utf-8'))
    rows=calculate(drivers,roster)
    path=OUT/('f2-teams-'+str(year)+'.json')
    if path.exists():
        published=json.loads(path.read_text(encoding='utf-8'))
        audit_published(published,rows)
        status='verified_against_published_team_points'
    else:
        published={'series':'F2 Teams','season':year,'source_url':drivers['source_url'],
                   'official_url':'https://www.fiaformula2.com/en/standings/'+str(year)+'/teams',
                   'retrieved_at':dt.datetime.now(dt.timezone.utc).isoformat(),
                   'data':{'headers':['Position','Team','Points'],'rows':rows},
                   'provider':'Calculated from licensed community driver points and season roster',
                   'attribution':'Wikipedia contributors','license':'CC BY-SA 4.0',
                   'license_url':drivers['license_url']}
        status='calculated_from_rostered_driver_points'
    published['points_audit']={'status':status,
                               'method':'sum of championship points for all rostered drivers, including substitutes',
                               'roster_source':roster['source_url'],
                               'roster_verified':roster['verification_date'],
                               'rows_checked':len(rows),
                               'checked_at':dt.datetime.now(dt.timezone.utc).isoformat()}
    path.write_text(json.dumps(published,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    manifest_path=OUT/'manifest.json'
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    entry=manifest.setdefault('series',{}).setdefault('F2 Teams',{'seasons':{}})
    entry.setdefault('seasons',{})[str(year)]='/data/standings/'+path.name
    manifest['updated']=dt.datetime.now(dt.timezone.utc).isoformat()
    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('F2 team points',status,'for',len(rows),'teams')


if __name__=='__main__':main()
