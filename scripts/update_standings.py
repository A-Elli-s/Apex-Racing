#!/usr/bin/env python3
"""Weekly snapshot of permitted public motorsport data. Preserve last valid snapshots."""
import datetime,json,pathlib,urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/'data'/'standings'
SOURCES={'WEC':('wec','standings.json','https://www.fiawec.com/'),
         'Formula E':('formula_e','results.json','https://www.fiaformulae.com/en/standings'),
         'WRC':('wrc','results.json','https://www.wrc.com/'),
         'F3':('f3','results.json','https://www.fiaformula3.com/Standings/Driver')}
def fetch(url):
    req=urllib.request.Request(url,headers={'User-Agent':'ApexRacingWorld/1.0 (+https://apexracingworld.com)'})
    with urllib.request.urlopen(req,timeout=30) as response:
        if response.status!=200:raise ValueError('HTTP '+str(response.status))
        raw=response.read(2_000_001)
        if len(raw)>2_000_000:raise ValueError('oversize feed')
        return json.loads(raw)
def valid(series,data):
    if series=='WEC':return isinstance(data,dict) and isinstance(data.get('hypercarDriverStandings'),list) and len(data['hypercarDriverStandings'])>0
    return (isinstance(data,list) and len(data)>0) or (isinstance(data,dict) and isinstance(data.get('results'),list) and len(data['results'])>0)

# Official championship pages. HTML tables are parsed conservatively; never publish unverified rows.
OFFICIAL={
 'F2':('https://www.fiaformula2.com/en/standings/{year}/drivers','f2'),
 'IndyCar':('https://www.indycar.com/Standings','indycar'),
 'MotoGP':('https://stats.motogp.com/en/world-standing/{year}/MotoGP/RidersChampionship','motogp'),
 'Moto2':('https://stats.motogp.com/en/world-standing/{year}/Moto2/TeamsChampionship','moto2'),
 'Moto3':('https://stats.motogp.com/en/world-standing/{year}/Moto3/TeamsChampionship','moto3'),
 'F3':('https://www.fiaformula3.com/en/standings/{year}/drivers','f3-official'),
 'NASCAR Cup':('https://www.nascar.com/standings/nascar-cup-series/','nascar-cup'),
 'NASCAR O’Reilly':('https://www.nascar.com/standings/nascar-xfinity-series/','nascar-oreilly'),
 'NASCAR Trucks':('https://www.nascar.com/standings/nascar-craftsman-truck-series/','nascar-trucks'),
 'IMSA':('https://www.imsa.com/standings/','imsa'),
 'Supercars':('https://www.supercars.com/standings','supercars'),
 'NHRA':('https://www.nhra.com/standings','nhra'),
 'WorldSBK':('https://www.worldsbk.com/en/results%20statistics','worldsbk'),
 'Supercross':('https://www.supercrosslive.com/standings/','supercross'),
 'Pro Motocross':('https://promotocross.com/standings','pro-motocross'),
 'MXGP':('https://www.mxgp.com/standings','mxgp'),
 'Dakar Rally':('https://www.dakar.com/en/rankings','dakar'),
 'Off-road racing':('https://score-international.com/','off-road'),
 'Monster Jam':('https://www.monsterjam.com/en-us/standings/','monster-jam'),
}
def fetch_html(url):
    from bs4 import BeautifulSoup
    req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (compatible; ApexRacingWorld/1.0; +https://apexracingworld.com)','Accept':'text/html'})
    with urllib.request.urlopen(req,timeout=35) as response:
        if response.status!=200:raise ValueError('HTTP '+str(response.status))
        content=response.read(3_000_001)
        if len(content)>3_000_000:raise ValueError('oversize page')
    return BeautifulSoup(content,'html.parser')
def collect_tables(soup):
    """Collect table contents first, without assuming a championship's column names."""
    collected=[]
    for table in soup.select('table'):
        trs=table.select('tr')
        if not trs:continue
        header_tr=table.select_one('thead tr') or trs[0]
        headers=[' '.join(cell.stripped_strings).strip() for cell in header_tr.find_all(['th','td'],recursive=False)]
        if not headers:continue
        rows=[]
        for tr in trs:
            if tr is header_tr:continue
            cells=[' '.join(cell.stripped_strings).strip() for cell in tr.find_all(['td','th'],recursive=False)]
            if len(cells)==len(headers) and any(cells):rows.append(cells)
        if rows:collected.append({'headers':headers,'rows':rows})
    return collected

def format_standings(collected,series):
    """Only publish a table after checking its structure and championship points."""
    candidates=[]
    for item in collected:
        headers,rows=item['headers'],item['rows']
        norm=[h.lower().strip() for h in headers]
        points_idx=next((i for i,h in enumerate(norm) if 'point' in h or h in ('pts','pt') or (series=='IMSA' and h=='total')),None)
        if points_idx is None:continue
        identity_idx=next((i for i,h in enumerate(norm) if any(t in h for t in ('driver','rider','team','competitor','name','entrant','athlete'))),None)
        if identity_idx is None:continue
        valid_rows=[]
        for row in rows:
            points=row[points_idx].replace(',','').replace(' ','')
            if not points.replace('.','',1).isdigit():continue
            if not row[identity_idx].strip():continue
            valid_rows.append(row)
        if len(valid_rows)<3:continue
        score=len(valid_rows)+(10 if any('driver' in h or 'rider' in h for h in norm) else 0)
        if series=='IMSA' and 'total' in norm:score+=5
        candidates.append((score,headers,valid_rows))
    if not candidates:raise ValueError('No validated points standings found among '+str(len(collected))+' extracted HTML tables; headers='+repr([t['headers'] for t in collected[:5]]))
    _,headers,rows=max(candidates,key=lambda x:x[0])
    return headers,rows

def official_table(soup,series):
    return format_standings(collect_tables(soup),series)

def refresh_official(now,manifest):
    for series,(template,slug) in OFFICIAL.items():
        previous=manifest['series'].get(series,{'seasons':{}})
        manifest['series'][series]={'official_url':template.replace('{year}',str(now.year)),'provider':previous.get('provider','Official championship website'),'seasons':dict(previous.get('seasons',{}))}
        for year in (now.year,now.year-1):
            path=OUT/(slug+'-'+str(year)+'.json')
            url=template.replace('{year}',str(year))
            # IndyCar's unversioned page is current-season only.
            if series=='IndyCar':url='https://www.indycar.com/standings/'+str(year)
            if '{year}' not in template and series not in ('IndyCar',) and year!=now.year:continue
            try:
                soup=fetch_html(url)
                headers,rows=official_table(soup,series)
                data={'headers':headers,'rows':rows}
                path.write_text(json.dumps({'series':series,'season':year,'source_url':url,'official_url':url,'retrieved_at':now.isoformat(),'data':data},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
                print('Official standings refreshed',series,year,len(rows))
            except Exception as e:print('Official source not parsed; preserving last snapshot:',series,year,str(e))
            if path.exists():
                manifest['series'][series]['seasons'][str(year)]='/data/standings/'+path.name
                manifest['series'][series]['provider']='Official championship website'

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    now=datetime.datetime.now(datetime.timezone.utc)
    manifest={'updated':now.isoformat(),'series':{}}
    for series,(slug,filename,official) in SOURCES.items():
        manifest['series'][series]={'official_url':official,'provider':'MotoDB community dataset (not official)','seasons':{}}
        for year in (now.year,now.year-1):
            path=OUT/(slug+'-'+str(year)+'.json')
            url=f'https://raw.githubusercontent.com/vishwapramuditha/moto-db/main/data/{slug}/{year}/{filename}'
            try:
                data=fetch(url)
                if not valid(series,data):raise ValueError('missing/empty expected records')
                snapshot={'series':series,'season':year,'source_url':url,'official_url':official,'retrieved_at':now.isoformat(),'data':data}
                path.write_text(json.dumps(snapshot,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
                print('Updated',series,year)
            except Exception as e:print('Preserving previous snapshot for',series,year,':',e)
            if path.exists():
                manifest['series'][series]['seasons'][str(year)]='/data/standings/'+path.name
    refresh_official(now,manifest)
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':main()
