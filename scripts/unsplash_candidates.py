#!/usr/bin/env python3
"""Generate an Unsplash candidate gallery for manual approval; never publishes images."""
import json, os, urllib.parse, urllib.request
from datetime import datetime, timezone
KEY=os.environ.get("UNSPLASH_ACCESS_KEY","")
if not KEY:
    raise SystemExit("UNSPLASH_ACCESS_KEY secret is missing. Add it in GitHub Actions secrets.")
queries={
"Formula 1":"formula one racing car","Formula 2":"formula racing single seater","Formula 3":"open wheel racing","IndyCar":"indycar racing","NASCAR Cup":"nascar stock car racing","NASCAR O'Reilly":"nascar racing car","NASCAR Trucks":"nascar racing truck","WEC":"endurance racing prototype","IMSA":"sports car racing","Formula E":"formula e electric racing","WRC":"rally car racing","Supercars":"australian supercars racing","NHRA":"drag racing car","MotoGP":"motogp motorcycle racing","Moto2":"motorcycle circuit racing","Moto3":"motorcycle racing track","WorldSBK":"superbike racing","Supercross":"supercross motorcycle stadium","Pro Motocross":"motocross racing","MXGP":"motocross championship","Dakar Rally":"dakar desert rally","Off-road racing":"offroad desert racing","Monster Jam":"monster truck racing"
}
out={"generated_at":datetime.now(timezone.utc).isoformat(),"note":"Candidate photos only. Review Unsplash page, photographer, subject, license, and API requirements before publishing.","series":{}}
for name,query in queries.items():
    params=urllib.parse.urlencode({"query":query,"per_page":5,"orientation":"landscape","content_filter":"high"})
    req=urllib.request.Request("https://api.unsplash.com/search/photos?"+params,headers={"Authorization":"Client-ID "+KEY,"Accept-Version":"v1","User-Agent":"ApexRacingHub/1.0"})
    try:
        with urllib.request.urlopen(req,timeout=25) as response:
            payload=json.load(response)
        out["series"][name]=[{"id":p.get("id"),"description":p.get("alt_description") or p.get("description") or "","photographer":p.get("user",{}).get("name"),"photo_page":p.get("links",{}).get("html"),"preview":p.get("urls",{}).get("small"),"image_url":p.get("urls",{}).get("regular"),"download_location":p.get("links",{}).get("download_location")} for p in payload.get("results",[])]
    except Exception as e:
        out["series"][name]={"error":str(e)}
os.makedirs("data",exist_ok=True)
with open("data/unsplash-candidates.json","w",encoding="utf-8") as f:json.dump(out,f,indent=2,ensure_ascii=False)
print("Wrote candidate metadata for",len(out["series"]),"championships. No website photos changed.")
