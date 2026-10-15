#!/usr/bin/env python3
"""Refresh Apex Racing Hub schedule data. Only publish validated records from known sources."""
import json, urllib.request, datetime, pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/"data"/"races.json"
def get(url):
    req=urllib.request.Request(url,headers={"User-Agent":"ApexRacingHub/1.0 (schedule updater)"})
    with urllib.request.urlopen(req,timeout=25) as response:return json.load(response)
def valid(rows):
    result=[]
    for r in rows:
        try:
            datetime.date.fromisoformat(r["date"])
            assert r["name"] and r["venue"] and r["url"].startswith("https://")
            result.append({k:r[k] for k in ("date","name","venue","url","tickets") if k in r})
        except (ValueError,AssertionError,KeyError,TypeError):continue
    return sorted(result,key=lambda x:x["date"])
def main():
    existing=json.loads(OUT.read_text()) if OUT.exists() else {"series":{}}
    series=existing.get("series",{})
    try:
        data=get("https://api.jolpi.ca/ergast/f1/current.json?limit=100")
        races=data["MRData"]["RaceTable"]["Races"]
        rows=[{"date":r["date"],"name":r["raceName"],"venue":r["Circuit"]["circuitName"],"url":r.get("url","https://www.formula1.com/en/racing/"),"tickets":"https://tickets.formula1.com/"} for r in races]
        if rows:series["Formula 1"]=valid(rows)
        print("Formula 1: refreshed",len(rows),"races")
    except Exception as ex:print("Formula 1 feed unavailable; preserving previous data:",ex)
    # Other championships can be refreshed by adding a verified JSON feed URL in
    # data/sources.json. The updater preserves previous dates if a feed fails.
    sources=ROOT/"data"/"sources.json"
    if sources.exists():
        for name,url in json.loads(sources.read_text()).items():
            try:
                payload=get(url)
                rows=payload.get("races",payload) if isinstance(payload,dict) else payload
                validated=valid(rows)
                if validated:series[name]=validated;print(name,": refreshed",len(validated),"races")
            except Exception as ex:print(name,": preserving previous data:",ex)
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps({"updated":datetime.datetime.now(datetime.timezone.utc).isoformat(),"series":series},ensure_ascii=False,indent=2)+"\n")
if __name__=="__main__":main()
