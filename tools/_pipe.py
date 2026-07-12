import json,base64,os,sys,glob,shutil,re
sys.path.insert(0,'tools'); import docx_to_flow as E
NUM=E.NUM; NUMLEAD=E.NUMLEAD
def isnum(l): return bool(NUM.match(l) or NUMLEAD.match(l))
T="/var/folders/ck/n7jlpv6908g75qp8j9yd7hww0000gn/T/claude-hostloop-plugins/916c06e11f4c7617/projects/-Users-edgar2025-Library-Application-Support-Claude-local-agent-mode-sessions-350f3aa4-7ea1-4f66-9659-b4d39ebead86-a2c1a424-94af-4444-8bef-199316e55d29-local-3cc336cf-04eb-4c99-8543-ff98ca1e92b5-outpu-maqfx5/eb916c67-f84f-438d-be1f-9b8021b6e7d4/tool-results/mcp-e8c72497-3d53-431f-9f62-72e02313374e-download_file_content-"
jobs=[("1783733013437","poem","p_5e319b47"),("1783733016089","poem","p_c2ae755f"),
 ("1783733018509","poem","p_c1745bf6"),("1783733019915","poem","p_5cea581e"),
 ("1783733021041","poem","p_c595ebe4"),("1783733037260","haiku","hdoc15"),
 ("1783733038430","haiku","hdoc30"),("1783733043637","haiku","hdoc61"),
 ("1783733046917","haiku","hdoc105"),("1783733049908","haiku","hdoc148")]
# 1) harvest TM
tm={"lines":{},"notes":{},"pref":{}}
for f in glob.glob("data/flows/*.json"):
    if os.path.basename(f)=="manifest.json": continue
    r=json.load(open(f))
    for b in r["flow"]:
        if b["type"]=="stanza" and b.get("en") and len(b["en"])==len(b["zh"]):
            for z,e in zip(b["zh"],b["en"]):
                if e and e.strip(): tm["lines"][z.strip()]=e
        elif b["type"]=="preface" and b.get("en"): tm["pref"][b["zh"].strip()]=b["en"]
        elif b["type"]=="note":
            for pt in b["points"]:
                if pt.get("en"): tm["notes"][pt["zh"].strip()]=pt["en"]
json.dump(tm,open("data/flows/_tm.json","w"),ensure_ascii=False)
print("TM harvested: lines=%d notes=%d pref=%d"%(len(tm["lines"]),len(tm["notes"]),len(tm["pref"])))
# 2) re-extract all + 3) re-apply TM
tmp="tools/_p.docx"
for ts,kind,slug in jobs:
    d=json.load(open(T+ts+".txt")); open(tmp,"wb").write(base64.b64decode(d["content"]))
    old=json.load(open(f"data/flows/{slug}.json"))
    real="images/flow/"+slug
    if os.path.exists(real): shutil.rmtree(real)
    flow=E.build_flow(E.parse_docx(tmp),kind,"flow/"+slug,real)
    for b in flow:
        if b["type"]=="stanza":
            nonnum=[l for l in b["zh"] if not isnum(l)]
            if nonnum and all(l.strip() in tm["lines"] for l in nonnum):
                b["en"]=[("" if isnum(l) else tm["lines"][l.strip()]) for l in b["zh"]]
        elif b["type"]=="preface" and b["zh"].strip() in tm["pref"]: b["en"]=tm["pref"][b["zh"].strip()]
        elif b["type"]=="note":
            for pt in b["points"]:
                if pt["zh"].strip() in tm["notes"]: pt["en"]=tm["notes"][pt["zh"].strip()]
    json.dump({"slug":slug,"kind":kind,"title":old.get("title",""),"source":d["title"],"flow":flow},
              open(f"data/flows/{slug}.json","w"),ensure_ascii=False,indent=1)
os.remove(tmp)
print("re-extracted + re-applied TM")
# verify spacing structure: haiku 30 around 297-300, and Baikal litany stanza sizes
r=json.load(open("data/flows/hdoc30.json"))
for b in r["flow"]:
    if b["type"]=="stanza" and b.get("num") and any(x in b["zh"][0] for x in("297","298","299","300")):
        print("HAIKU", b["zh"][0].strip(), "-> one stanza of", len(b["zh"]),"lines")
r=json.load(open("data/flows/p_c2ae755f.json"))
sts=[len(b["zh"]) for b in r["flow"] if b["type"]=="stanza"]
print("Baikal stanza line-counts:",sts)
