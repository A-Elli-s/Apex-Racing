#!/usr/bin/env python3
"""Second-pass collector for public, JavaScript-rendered championship standings.

Runs after the fast HTML collector. Only publishes validated points tables.
Does not attempt to circumvent 403s, logins, paywalls or anti-bot challenges.
"""
import datetime
import json
import pathlib
import sys

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as BrowserTimeout

from update_standings import OFFICIAL, collect_tables, format_standings, OUT

SKIP_BLOCKED={'NASCAR Cup','NASCAR O’Reilly','NASCAR Trucks','Monster Jam'}
MAX_PAGES=20

def main():
    manifest_path=OUT/'manifest.json'
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    now=datetime.datetime.now(datetime.timezone.utc)
    year=now.year
    outcomes={}
    with sync_playwright() as playwright:
        browser=playwright.chromium.launch(headless=True)
        context=browser.new_context(user_agent='ApexRacingWorld/1.0 (+https://apexracingworld.com)', viewport={'width':1440,'height':900})
        for series,(template,slug) in list(OFFICIAL.items())[:MAX_PAGES]:
            existing=manifest.get('series',{}).get(series,{}).get('seasons',{}).get(str(year))
            if existing:
                outcomes[series]='already published'
                continue
            if series in SKIP_BLOCKED:
                outcomes[series]='blocked at source; browser bypass not attempted'
                continue
            url=template.replace('{year}',str(year))
            page=context.new_page()
            try:
                response=page.goto(url,wait_until='domcontentloaded',timeout=18000)
                status=response.status if response else None
                if status in (401,403,404,429):
                    raise ValueError('HTTP '+str(status)+'; no bypass attempted')
                if not response or status>=400:
                    raise ValueError('HTTP '+str(status))
                try:
                    page.locator('table').first.wait_for(state='attached',timeout=6500)
                except BrowserTimeout:
                    pass
                page.wait_for_timeout(1200)
                soup=BeautifulSoup(page.content(),'html.parser')
                tables=collect_tables(soup)
                headers,rows=format_standings(tables,series)
                if len(rows)<3:raise ValueError('too few standings rows')
                snapshot={'series':series,'season':year,'source_url':url,'official_url':url,
                          'retrieved_at':now.isoformat(),'data':{'headers':headers,'rows':rows},
                          'collection_method':'rendered public page'}
                path=OUT/(slug+'-'+str(year)+'.json')
                path.write_text(json.dumps(snapshot,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
                manifest['series'].setdefault(series,{'official_url':url,'provider':'Official championship website','seasons':{}})
                manifest['series'][series]['seasons'][str(year)]='/data/standings/'+path.name
                manifest['series'][series]['provider']='Official championship website'
                outcomes[series]='published '+str(len(rows))+' standings rows'
            except Exception as exc:
                outcomes[series]='not published: '+str(exc)[:220]
            finally:
                page.close()
        context.close()
        browser.close()
    manifest['updated']=now.isoformat()
    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for series,result in outcomes.items():print('Rendered collection:',series,'-',result)
    print('Rendered standings published:',sum('published ' in x for x in outcomes.values()))
    # Missing public data is reported, not fabricated or treated as a workflow crash.

if __name__=='__main__':
    main()
