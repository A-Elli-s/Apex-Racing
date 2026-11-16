import json,re,urllib.request
UA={"User-Agent":"ApexRacingWorld/1.0 (+https://apexracingworld.com)"}
def get(u):
    try:
        r=urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=30); return r.status,r.read(3000000).decode("utf-8","replace")
    except urllib.error.HTTPError as e: return e.code,""
    except Exception as e: return 0,str(e)[:80]
print("===== NASCAR feeds")
st,b=get("https://cf.nascar.com/cacher/2026/race_list_basic.json"); d=json.loads(b)
print("keys",list(d.keys()))
for k,v in d.items():
    done=[r for r in v if r.get("winner_driver_id")]
    last=max(done,key=lambda r:r["race_date"]) if done else None
    print(k,"races",len(v),"with winner",len(done),"last:",last and (last["race_date"][:10],last["race_name"],last.get("race_type_id")),"| keys:",sorted(v[0].keys())[:40])
for sid in (1,2,3):
    for u in (f"https://cf.nascar.com/cacher/2026/{sid}/final/{sid}-driver-points.json",
              f"https://cf.nascar.com/cacher/2026/{sid}/final/{sid}-owner-points.json"):
        st,b=get(u); print("\n",u,st,len(b))
        if st==200:
            try:
                j=json.loads(b); print("  type",type(j).__name__,"n",len(j))
                rows=j if isinstance(j,list) else next((v for v in j.values() if isinstance(v,list)),[])
                print("  keys",sorted(rows[0].keys()))
                for r in rows[:3]: print("  ",{k:r.get(k) for k in ("position","first_name","last_name","driver_name","points","wins","is_in_chase","playoff_points","poles","top_5","top_10","starts","delta_leader","bonus_points")})
                print("   LAST",{k:rows[-1].get(k) for k in ("position","first_name","last_name","points")})
            except Exception as e: print("  parse err",e,b[:200])
st,b=get("https://cf.nascar.com/live/feeds/live-points.json"); j=json.loads(b)
print("\nlive-points n",len(j),"series_ids",sorted({r.get("series_id") for r in j}),"keys",sorted(j[0].keys())[:30])
print("\n===== robots full")
for u in ("https://www.monsterjam.com/robots.txt","https://www.supercars.com/robots.txt"):
    st,b=get(u); print(u,st); print(b[:400])
print("\n===== NHRA terms scan")
st,b=get("https://www.nhra.com/terms-use"); t=re.sub(r"\s+"," ",re.sub(r"<[^>]+>"," ",b)); print(st,len(t))
seen=0
for m in re.finditer(r"(?i)(robot|spider|scrap|automat|data mining|harvest|database|crawl|extract)",t):
    print(" >",t[max(0,m.start()-150):m.end()+200]); seen+=1
    if seen>=6: break
print("\n===== Supercars terms scan")
st,b=get("https://www.supercars.com/terms-and-conditions"); t=re.sub(r"\s+"," ",re.sub(r"<[^>]+>"," ",b)); print(st,len(t))
seen=0
for m in re.finditer(r"(?i)(robot|spider|scrap|automat|data mining|harvest|crawl|extract|copyright)",t):
    print(" >",t[max(0,m.start()-120):m.end()+180]); seen+=1
    if seen>=4: break
