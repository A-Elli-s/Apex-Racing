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
    # Community-maintained motorsport dataset; preserve last good data on failure.
    base="https://raw.githubusercontent.com/vishwapramuditha/moto-db/main/data"
    from urllib.parse import quote
    def date_of(value,year):
        if not value:return None
        value=str(value)
        try:return datetime.date.fromisoformat(value[:10]).isoformat()
        except ValueError:pass
        for fmt in ("%d %B %Y","%d %b %Y","%d %B","%d %b"):
            try:
                dt=datetime.datetime.strptime(value,fmt)
                return dt.replace(year=year if "%Y" not in fmt else dt.year).date().isoformat()
            except ValueError:pass
        return None
    def row(day,name,venue,url,tickets=None):
        return dict(date=day,name=str(name or "Race"),venue=str(venue or "Venue TBA"),url=url,**({"tickets":tickets} if tickets else {}))
    def convert(sport,data,year):
        url={
          "f2":"https://www.fiaformula2.com/Calendar",
          "f3":"https://www.fiaformula3.com/Calendar",
          "motogp":"https://www.motogp.com/en/calendar",
          "nascar":"https://www.nascar.com/nascar-cup-series/2026/schedule/",
          "indycar":"https://www.indycar.com/Schedule",
          "wec":"https://www.fiawec.com/en/calendar/80",
          "formula_e":"https://www.fiaformulae.com/en/calendar",
          "wrc":"https://www.wrc.com/en/calendar"
        }[sport]
        out=[]
        if sport=="nascar":
            for label,items in data.get("series",{}).items():
                for e in items:
                    day=date_of(e.get("date_scheduled") or e.get("race_date"),year)
                    if day:out.append(row(day,label.upper()+" — "+e.get("race_name","Race"),e.get("track_name"),url,"https://www.nascar.com/tickets/"))
        elif sport=="motogp":
            for e in data.get("events",[]):
                if e.get("test"):continue
                day=date_of(e.get("date_end"),year)
                if day:out.append(row(day,e.get("sponsored_name") or e.get("name"),e.get("circuit",{}).get("name"),url,"https://tickets.motogp.com/"))
        elif sport in ("f2","f3"):
            for e in data.get("races",[]):
                day=date_of(e.get("date"),year)
                circuit=e.get("Circuit",{})
                venue=circuit.get("circuitName") if isinstance(circuit,dict) else e.get("circuit")
                if day:out.append(row(day,e.get("raceName") or e.get("name") or "Round "+str(e.get("round")),venue,url))
        elif sport=="indycar":
            for e in data.get("races",[]):
                day=date_of(e.get("date"),year)
                if day:out.append(row(day,e.get("name"),e.get("venue") or e.get("location") or e.get("short_name"),url))
        elif sport=="wec":
            for e in data.get("races",[]):
                day=date_of(e.get("date") or e.get("startDate"),year)
                venue=e.get("location") or {}
                if day:out.append(row(day,e.get("name"),venue.get("venue") if isinstance(venue,dict) else venue,e.get("url") or url))
        elif sport=="formula_e":
            for e in data if isinstance(data,list) else data.get("races",[]):
                day=date_of(e.get("date"),year)
                if day:out.append(row(day,e.get("eprix") or e.get("name"),e.get("country") or e.get("circuit"),url))
        elif sport=="wrc":
            for e in data.get("races",[]):
                day=date_of(e.get("finish_date") or e.get("start_date"),year)
                if day:out.append(row(day,e.get("name"),e.get("location") or e.get("country") or "Rally location: see official calendar",url))
        return valid(out)
    mapping={"f2":"Formula 2","f3":"Formula 3","motogp":"MotoGP / Moto2 / Moto3","nascar":"NASCAR Cup / O’Reilly / Trucks","indycar":"IndyCar","wec":"WEC","formula_e":"Formula E","wrc":"WRC"}
    for sport,name in mapping.items():
        rows=[]
        for year in (datetime.date.today().year,datetime.date.today().year+1):
            try:
                data=get(f"{base}/{sport}/{year}/schedule.json")
                rows.extend(convert(sport,data,year))
            except Exception as ex:print(name,year,": feed unavailable:",str(ex)[:150])
        if rows:
            series[name]=valid(rows)
            print(name,": refreshed",len(rows),"races")
    # Optional additional verified JSON sources, configured per championship.
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
