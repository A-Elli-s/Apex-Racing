#!/usr/bin/env python3
"""CC BY-SA Wikipedia standings snapshots for F2/F3, staged on dev only.

Read-only and conservative: do not confuse finishing positions with points.
These are community-maintained tables, not official classifications.
"""
import datetime as dt
import json
import pathlib
import re
import urllib.request
from bs4 import BeautifulSoup

ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/'data'/'standings'
LICENSE='https://creativecommons.org/licenses/by-sa/4.0/'
SERIES={'F2':'Formula_2_Championship','F3':'FIA_Formula_3_Championship'}
OFFICIAL={'F2':'https://www.fiaformula2.com/en/standings/{year}/drivers',
          'F3':'https://www.fiaformula3.com/en/standings/{year}/drivers'}


def cell_text(cell):
    clean=BeautifulSoup(str(cell),'html.parser')
    for item in clean.select('sup, .reference, .flagicon, .mw-editsection'):
        item.decompose()
    return ' '.join(clean.stripped_strings).strip()


def parse_table(soup,kind):
    key='driver' if kind=='drivers' else 'team'
    heading=next((h for h in soup.select('h2,h3,h4')
                  if key+'s' in h.get_text(' ',strip=True).lower()
                  and 'championship standings' in h.get_text(' ',strip=True).lower()),None)
    if heading is None:
        raise ValueError('Standings section heading absent')
    candidates=[]
    for table in heading.find_all_next('table'):
        nearest=table.find_previous(['h2','h3','h4'])
        if nearest is not heading:
            break
        if 'wikitable' not in table.get('class',[]):
            continue
        tr=table.find_all('tr')
        heading_text=' '.join(cell_text(c).lower() for row in tr[:3]
                              for c in row.find_all(['th','td'],recursive=False))
        if key not in heading_text or not ('points' in heading_text or 'pts' in heading_text):
            continue
        rows=[]
        for row in tr:
            cells=row.find_all(['th','td'],recursive=False)
            if len(cells)<3:
                continue
            rank=cell_text(cells[0])
            name=cell_text(cells[1])
            score=cell_text(cells[-1])
            if not re.fullmatch(r'\d{1,2}',rank):
                continue
            if not re.fullmatch(r'\d{1,4}(?:\.\d+)?',score):
                continue
            if not name or len(name)>90 or not re.search('[A-Za-z]',name):
                continue
            rows.append([int(rank),name,score])
        if rows:
            candidates.append(rows)
    if not candidates:
        raise ValueError('No usable ranked points table')
    rows=max(candidates,key=len)
    minimum=10 if kind=='drivers' else 5
    if len(rows)<minimum or len(rows)>65 or rows[0][0]!=1:
        raise ValueError('Standings coverage/leader validation failed')
    if len({r[1].casefold() for r in rows})!=len(rows):
        raise ValueError('Duplicate competitor names')
    if any(rows[i][0]<rows[i-1][0] for i in range(1,len(rows))):
        raise ValueError('Rank order inconsistent')
    if any(float(rows[i][2])>float(rows[i-1][2]) for i in range(1,len(rows))):
        raise ValueError('Points order inconsistent')
    return {'headers':['Position','Driver' if kind=='drivers' else 'Team','Points'],
            'rows':[[str(p),name,pts] for p,name,pts in rows]}


def fetch_html(url):
    req=urllib.request.Request(url,headers={
        'User-Agent':'ApexRacingWorld/1.0 (contact@apexracingworld.com; educational preview)',
        'Accept':'text/html'})
    with urllib.request.urlopen(req,timeout=25) as response:
        if response.status!=200:raise ValueError('HTTP '+str(response.status))
        body=response.read(3_000_001)
        if len(body)>3_000_000:raise ValueError('Oversize standings page')
        return BeautifulSoup(body,'html.parser')


def main():
    now=dt.datetime.now(dt.timezone.utc)
    year=now.year
    OUT.mkdir(parents=True,exist_ok=True)
    manifest_path=OUT/'manifest.json'
    manifest=json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.exists() else {'series':{}}
    count=0
    for series,article in SERIES.items():
        url='https://en.wikipedia.org/wiki/'+str(year)+'_'+article
        try:
            soup=fetch_html(url)
        except Exception as error:
            print(series,'source unavailable:',error)
            continue
        for kind in ('drivers','teams'):
            key=series if kind=='drivers' else series+' Teams'
            slug=series.lower()+'-standings' if kind=='drivers' else series.lower()+'-teams'
            try:
                data=parse_table(soup,kind)
                snapshot={'series':key,'season':year,'source_url':url,
                          'official_url':OFFICIAL[series].format(year=year),
                          'retrieved_at':now.isoformat(),'data':data,
                          'provider':'Wikipedia community standings (not official)',
                          'attribution':'Wikipedia contributors',
                          'license':'CC BY-SA 4.0','license_url':LICENSE}
                path=OUT/(slug+'-'+str(year)+'.json')
                path.write_text(json.dumps(snapshot,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
                entry=manifest.setdefault('series',{}).setdefault(key,{'seasons':{}})
                if key=='F3' and str(year) in entry.get('seasons',{}):
                    previous=entry['seasons'][str(year)]
                    if previous.endswith('/f3-'+str(year)+'.json'):
                        entry.setdefault('race_results_seasons',{})[str(year)]=previous
                entry.update({'official_url':snapshot['official_url'],'provider':snapshot['provider'],
                              'attribution':snapshot['attribution'],'license_url':LICENSE})
                entry.setdefault('seasons',{})[str(year)]='/data/standings/'+path.name
                count+=1
                print(key,'community standings staged:',len(data['rows']))
            except Exception as error:
                print(key,'not published; preserving existing:',error)
    if count:
        manifest['updated']=now.isoformat()
        manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Ladder community standings staged:',count)


if __name__=='__main__':main()
