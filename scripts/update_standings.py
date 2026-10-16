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
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':main()
