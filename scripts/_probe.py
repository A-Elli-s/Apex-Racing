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

for t in ["2026 NHRA Mission Foods Drag Racing Series","2026 Supercars Championship"]:
    show(t)
import re
def get(u):
    try:
        r=urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"ApexRacingWorld/1.0 (+https://apexracingworld.com)"}),timeout=25)
        return r.status,r.read(400000).decode("utf-8","replace")
    except urllib.error.HTTPError as e: return e.code,""
    except Exception as e: return 0,str(e)[:80]
print("\n===== robots / terms evidence")
for u in ["https://www.nascar.com/robots.txt","https://cf.nascar.com/robots.txt","https://www.monsterjam.com/robots.txt",
          "https://www.supercars.com/robots.txt","https://www.nhra.com/robots.txt"]:
    st,b=get(u); print("\n",u,st,len(b))
    for l in b.splitlines():
        if re.search(r"(?i)^(user-agent|disallow|allow|crawl-delay).*(\*|stand|point|api|json|feed|cacher|\bdisallow: /$)",l): print("   ",l[:110])
print("\n===== terms keyword scan")
for u in ["https://www.nascar.com/terms-of-use/","https://www.monsterjam.com/en-us/terms-use","https://www.monsterjam.com/en-us/terms-of-use",
          "https://www.supercars.com/terms-and-conditions","https://www.nhra.com/terms-use"]:
    st,b=get(u); print("\n",u,st,len(b))
    t=re.sub(r"<[^>]+>"," ",b)
    for m in re.finditer(r"(?i)[^.]{0,140}(robot|spider|scrap|automated|data mining|harvest)[^.]{0,160}\.",t):
        print("   >",re.sub(r"\s+"," ",m.group(0))[:300])
        break
print("\n===== single honest GET of NASCAR public JSON feeds")
for u in ["https://cf.nascar.com/cacher/2026/race_list_basic.json","https://cf.nascar.com/live/feeds/live-points.json"]:
    st,b=get(u); print(u,st,len(b),b[:120].replace("\n"," "))
