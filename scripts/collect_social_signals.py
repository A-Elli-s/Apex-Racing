"""Apex Racing Data Hub: normalize permitted public race-result feeds into a review queue.

Input: data/inbox/source-posts.json (manually exported or provider-authorized posts).
No scraping of X/Instagram or inference of official standings.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
INBOX=ROOT/"data/inbox/source-posts.json"
OUT=ROOT/"data/review/social-signals.json"
ALLOWED={"x","instagram","official","api"}
FIELDS=("source","source_url","published_at","series","text")

def main():
    if not INBOX.exists():
        print("No authorized source-posts input; retaining prior review queue.")
        return
    incoming=json.loads(INBOX.read_text(encoding="utf-8"))
    if not isinstance(incoming,list):
        raise ValueError("Input must be a list")
    rows=[]
    for item in incoming:
        if not isinstance(item,dict) or any(not item.get(k) for k in FIELDS):
            continue
        if item["source"] not in ALLOWED or not str(item["source_url"]).startswith("https://"):
            continue
        rows.append({k:str(item[k])[:4000] for k in FIELDS})
    seen=set()
    unique=[]
    for row in rows:
        key=(row["source_url"],row["series"])
        if key not in seen:
            seen.add(key)
            unique.append(row)
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps({"updated":datetime.now(timezone.utc).isoformat(),"status":"unverified_social_signals","items":unique},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Queued {len(unique)} unverified signals; standings unchanged")

if __name__=="__main__":
    main()
