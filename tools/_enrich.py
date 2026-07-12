import json,glob,os,re
poems=json.load(open("data/poems.json")); byid={p["id"]:p for p in poems}
flows={}
for f in glob.glob("data/flows/*.json"):
    if os.path.basename(f)=="manifest.json": continue
    r=json.load(open(f)); flows[r["slug"]]=r
def poem_format(flow):
    st=[b for b in flow if b["type"]=="stanza"]
    txt=" ".join(" ".join(b.get("zh",[])) for b in st)
    if re.search(r'[〈（(]\s*\d+\s*[〉）)]',txt): return "組詩 Sequence"
    return "長詩 Long-form" if len(st)>=9 else "抒情 Lyric"
def geo_bits(p):
    tags=list(p.get("geo_tags") or []); g=(p.get("geo") or "").strip()
    if g:
        place=g.split(",")[0].strip()
        if place and place not in tags: tags=[place]+tags
    return tags
man={"poems":[],"haiku":[],"artwork":[]}
for slug,r in flows.items():
    if r["kind"]=="poem":
        p=byid.get(slug,{})
        tags={"geo":geo_bits(p),"subject":list(p.get("themes") or []),"format":poem_format(r["flow"])}
        r["tags"]=tags; json.dump(r,open("data/flows/"+slug+".json","w"),ensure_ascii=False,indent=1)
        man["poems"].append({"slug":slug,"title":r["title"],"title_en":p.get("title_en") or "","tags":tags})
    elif r["kind"]=="haiku" and "haiku" in r:
        ns=[hk["n"] for hk in r["haiku"] if hk.get("n")]
        s=re.search(r'(\d+)\s*$',r["title"]); s=int(s.group(1)) if s else 0
        theme=""; m=re.search(r'《([^》]+)》',r["title"]+" "+r.get("source",""))
        if m: theme=m.group(1)
        meta={"slug":r["slug"],"series":str(s),"range":(f"{min(ns)}\u2013{max(ns)}" if ns else ""),"count":len(ns),"theme":theme}
        r["meta"]=meta; json.dump(r,open("data/flows/"+r["slug"]+".json","w"),ensure_ascii=False,indent=1)
        man["haiku"].append(meta); continue
    elif r["kind"]=="haiku":
        s=re.search(r'(\d+)\s*$',r["title"]); s=int(s.group(1)) if s else 0
        nums=[]
        for b in r["flow"]:
            if b["type"]=="stanza" and b.get("num"):
                m=re.match(r'\s*(\d{1,4})',b["zh"][0])
                if m: nums.append(int(m.group(1)))
        if s:
            keep=[n for n in nums if s*10-11<=n<=s*10+2]
            if keep: nums=keep
        rng=f"{min(nums)}–{max(nums)}" if nums else ""
        theme=""; m=re.search(r'《([^》]+)》',r["title"]+" "+r.get("source",""))
        if m: theme=m.group(1)
        meta={"slug":slug,"series":str(s),"range":rng,"count":len(nums),"theme":theme}
        r["meta"]=meta; json.dump(r,open("data/flows/"+slug+".json","w"),ensure_ascii=False,indent=1)
        man["haiku"].append(meta)
man["poems"].sort(key=lambda x:x["title"]); man["haiku"].sort(key=lambda x:int(x["series"] or 0))
json.dump(man,open("data/flows/manifest.json","w"),ensure_ascii=False,indent=1)
flows2={}
for f in glob.glob("data/flows/*.json"):
    if os.path.basename(f)=="manifest.json": continue
    rr=json.load(open(f)); flows2[rr["slug"]]=rr
open("data/flows/_embedded.js","w").write("window.MANIFEST="+json.dumps(man,ensure_ascii=False)+";\nwindow.FLOWS="+json.dumps(flows2,ensure_ascii=False)+";\n")
print("enriched; haiku meta:",[(h["series"],h["range"]) for h in man["haiku"]])
