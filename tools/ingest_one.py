#!/usr/bin/env python3
"""Ingest ONE downloaded doc. Args: <download_json_tmp> <kind> <slug> <title>
The tmp file is the Drive connector's saved result: JSON {content: base64, title, ...}.
Writes data/flows/<slug>.json. Haiku are segmented into per-haiku objects.
Re-applies data/flows/_tm.json translation memory if present. Idempotent-ish."""
import sys,os,json,base64,re
sys.path.insert(0,os.path.join(os.path.dirname(__file__)))
import docx_to_flow as E
NUM=E.NUM; NUMLEAD=E.NUMLEAD
def isnum(l): return bool(NUM.match(l) or NUMLEAD.match(l))
tmpjson,kind,slug,title = sys.argv[1],sys.argv[2],sys.argv[3],sys.argv[4]
repo=os.getcwd()
d=json.load(open(tmpjson)); 
docx=os.path.join("tools","_ingest_%s.docx"%slug)
open(docx,"wb").write(base64.b64decode(d["content"]))
real=os.path.join("images","flow",slug)
if os.path.exists(real):
    import shutil; shutil.rmtree(real)
flow=E.build_flow(E.parse_docx(docx),kind,"flow/"+slug,real)
os.remove(docx)
# translation memory re-apply
tm={"lines":{},"notes":{},"pref":{}}
tmf="data/flows/_tm.json"
if os.path.exists(tmf): tm=json.load(open(tmf))
def apply_blocks(blocks):
    for b in blocks:
        if b["type"]=="stanza":
            nn=[l for l in b["zh"] if not isnum(l)]
            if nn and all(l.strip() in tm["lines"] for l in nn):
                b["en"]=[("" if isnum(l) else tm["lines"][l.strip()]) for l in b["zh"]]
        elif b["type"]=="preface" and b["zh"].strip() in tm["pref"]: b["en"]=tm["pref"][b["zh"].strip()]
        elif b["type"]=="note":
            for pt in b["points"]:
                if pt["zh"].strip() in tm["notes"]: pt["en"]=tm["notes"][pt["zh"].strip()]
apply_blocks(flow)
if kind=="haiku":
    front=[]; haiku=[]; cur=None
    for b in flow:
        if b["type"]=="stanza" and b.get("num"):
            m=re.match(r'\s*(\d+)',b["zh"][0]); n=int(m.group(1)) if m else 0
            cur={"n":n,"flow":[b]}; haiku.append(cur)
        elif cur is None: front.append(b)
        else: cur["flow"].append(b)
    rec={"slug":slug,"kind":"haiku","title":title,"source":d["title"],"front":front,"haiku":haiku}
else:
    rec={"slug":slug,"kind":kind,"title":title,"source":d["title"],"flow":flow}
os.makedirs("data/flows",exist_ok=True)
json.dump(rec,open(f"data/flows/{slug}.json","w"),ensure_ascii=False,indent=1)
nimg=sum(1 for b in flow if b["type"]=="image")
print(f"OK {slug} kind={kind} blocks={len(flow)} haiku={len(rec.get('haiku',[]))} images={nimg}")
