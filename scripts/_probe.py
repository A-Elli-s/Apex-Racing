import json,re,urllib.parse,urllib.request
from bs4 import BeautifulSoup
UA={"User-Agent":"ApexRacingWorldResearch/1.0 (contact@apexracingworld.com)"}
def api(**p):
    u="https://en.wikipedia.org/w/api.php?"+urllib.parse.urlencode({**p,"format":"json"})
    with urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=30) as r: return json.load(r)
def txt(c):
    for s in c.select("sup,.reference,.flagicon"): s.decompose()
    return " ".join(c.stripped_strings)
TITLES=["2026 NASCAR Cup Series","2026 NASCAR O'Reilly Auto Parts Series","2026 NASCAR Craftsman Truck Series",
"2026 Supercars Championship","2026 IMSA SportsCar Championship","2026 AMA Supercross Championship",
"2026 AMA Pro Motocross Championship","2026 FIM Motocross World Championship","2026 Monster Jam"]
for t in TITLES:
    print("\n#####",t)
    try:
        d=api(action="parse",page=t,prop="text|sections",redirects=1)
    except Exception as e:
        print("  FAIL",e)
        s=api(action="query",list="search",srsearch=t,srlimit=3)
        print("  search:",[x["title"] for x in s["query"]["search"]]); continue
    soup=BeautifulSoup(d["parse"]["text"]["*"],"html.parser")
    print("  resolved:",d["parse"]["title"])
    for tb in soup.select("table.wikitable"):
        trs=tb.find_all("tr")
        if len(trs)<8: continue
        head=" | ".join(txt(c) for c in trs[0].find_all(["th","td"],recursive=False))
        head2=" | ".join(txt(c) for c in trs[1].find_all(["th","td"],recursive=False)) if len(trs)>1 else ""
        low=(head+head2).lower()
        if "pts" not in low and "points" not in low: continue
        h=tb.find_previous(["h2","h3","h4"])
        print("  --- table rows=%d under '%s'"%(len(trs),h.get_text(' ',strip=True)[:50] if h else None))
        print("    H1:",head[:160]); print("    H2:",head2[:160])
        for tr in trs[2:5]:
            print("    R:"," | ".join(txt(c) for c in tr.find_all(["th","td"],recursive=False))[:160])
        print("    LAST:"," | ".join(txt(c) for c in trs[-1].find_all(["th","td"],recursive=False))[:160])
