import os,json,base64,re,shutil,sys
sys.path.insert(0,os.path.dirname(__file__)); import docx_to_flow as E
NUM=E.NUM; NUMLEAD=E.NUMLEAD
def isnum(l): return bool(NUM.match(l) or NUMLEAD.match(l))
_TM=None
def _tm():
    global _TM
    if _TM is None:
        _TM=json.load(open("data/flows/_tm.json")) if os.path.exists("data/flows/_tm.json") else {"lines":{},"notes":{},"pref":{}}
    return _TM
def _apply(blocks):
    tm=_tm()
    for b in blocks:
        if b["type"]=="stanza":
            nn=[l for l in b["zh"] if not isnum(l)]
            if nn and all(l.strip() in tm["lines"] for l in nn):
                b["en"]=[("" if isnum(l) else tm["lines"][l.strip()]) for l in b["zh"]]
        elif b["type"]=="preface" and b["zh"].strip() in tm["pref"]: b["en"]=tm["pref"][b["zh"].strip()]
        elif b["type"]=="note":
            for pt in b["points"]:
                if pt["zh"].strip() in tm["notes"]: pt["en"]=tm["notes"][pt["zh"].strip()]
def ingest(d, kind, slug, title):
    docx="tools/_ing_%s.docx"%re.sub(r'[^A-Za-z0-9_]','',slug)
    open(docx,"wb").write(base64.b64decode(d["content"]))
    real=os.path.join("images","flow",slug)
    if os.path.exists(real): shutil.rmtree(real)
    flow=E.build_flow(E.parse_docx(docx),kind,"flow/"+slug,real)
    os.remove(docx)
    _apply(flow)
    if kind=="haiku":
        front=[]; haiku=[]; cur=None
        for b in flow:
            if b["type"]=="stanza" and b.get("num"):
                m=re.match(r'\s*(\d+)',b["zh"][0]); n=int(m.group(1)) if m else 0
                cur={"n":n,"flow":[b]}; haiku.append(cur)
            elif cur is None: front.append(b)
            else: cur["flow"].append(b)
        rec={"slug":slug,"kind":"haiku","title":title,"source":d.get("title",""),"front":front,"haiku":haiku}
        nh=len(haiku)
    else:
        rec={"slug":slug,"kind":kind,"title":title,"source":d.get("title",""),"flow":flow}; nh=0
    os.makedirs("data/flows",exist_ok=True)
    json.dump(rec,open(f"data/flows/{slug}.json","w"),ensure_ascii=False,indent=1)
    nimg=sum(1 for b in flow if b["type"]=="image")
    return nh,nimg,len(flow)
