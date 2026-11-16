import json,urllib.parse,urllib.request
from bs4 import BeautifulSoup
UA={"User-Agent":"ApexRacingWorldResearch/1.0 (contact@apexracingworld.com)"}
def api(**p):
    u="https://en.wikipedia.org/w/api.php?"+urllib.parse.urlencode({**p,"format":"json"})
    with urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=30) as r: return json.load(r)
def txt(c):
    for s in c.select("sup,.reference,.flagicon"): s.decompose()
    return " ".join(c.stripped_strings)
def cells(tr): return [txt(c) for c in tr.find_all(["th","td"],recursive=False)]
def show(title):
    print("\n#####",title)
    try:
        s=api(action="query",list="search",srsearch=title,srlimit=4)
        print("  search:",[x["title"] for x in s["query"]["search"]])
        d=api(action="parse",page=title,prop="text",redirects=1)
        if "parse" not in d: print("  NO PAGE"); return
    except Exception as e:
        print("  ERR",str(e)[:100]); return
    soup=BeautifulSoup(d["parse"]["text"]["*"],"html.parser")
    n=0
    for tb in soup.select("table.wikitable"):
        trs=tb.find_all("tr")
        if len(trs)<6: continue
        h=cells(trs[0]); low=" ".join(h).lower()
        if not any(k in low for k in ("pts","points")): continue
        n+=1
        sec=tb.find_previous(["h2","h3","h4"])
        print("  --- rows=%d section=%r"%(len(trs),sec.get_text(' ',strip=True)[:45] if sec else None))
        print("    HEAD(%d):"%len(h),h[:3],"...",h[-4:])
        for tr in trs[1:3]:
            c=cells(tr); print("    ROW(%d):"%len(c),c[:3],"...",c[-3:])
        if n>=3: break
    if n==0: print("  (no points tables)")
for t in ["2026 NASCAR Cup Series","2026 AMA Pro Motocross Championship","2026 Pro Motocross Championship",
          "2026 Motocross World Championship","2026 FIM Motocross World Championship",
          "2026 NHRA Drag Racing Series","2026 NHRA Camping World Drag Racing Series","NHRA Drag Racing Series",
          "2026 Monster Jam season","Monster Jam World Finals","Monster Jam"]:
    show(t)
