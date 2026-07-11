#!/usr/bin/env python3
"""Fill missing English via free no-key MT (MyMemory), cached into data/flows.
Idempotent (skips filled en). Skips-and-continues on per-line errors; stops only on
daily quota. Long commentary is chunked by sentence to fit MyMemory's query limit."""
import json,glob,os,time,re,urllib.parse,urllib.request,sys,ssl
CTX=ssl.create_default_context(); CTX.check_hostname=False; CTX.verify_mode=ssl.CERT_NONE
EMAIL="edgar.ho@meritamerica.org"
LOG=open("tools/_tr.log","a")
def log(m): LOG.write(m+"\n"); LOG.flush(); print(m)
calls=0; MAXCALLS=int(sys.argv[1]) if len(sys.argv)>1 else 700
QUOTA=[False]
def _one(zh):
    global calls
    zh=zh.strip()
    if not zh: return ""
    calls+=1
    q=urllib.parse.urlencode({"q":zh,"langpair":"zh-CN|en","de":EMAIL})
    try:
        with urllib.request.urlopen("https://api.mymemory.translated.net/get?"+q,timeout=20,context=CTX) as r:
            d=json.load(r)
        txt=str(d.get("responseData",{}).get("translatedText",""))
        if "MYMEMORY WARNING" in txt.upper() or d.get("responseStatus")==429:
            QUOTA[0]=True; log("QUOTA hit"); return None
        if "QUERY LENGTH LIMIT" in txt.upper(): return "__LEN__"
        time.sleep(0.2); return txt
    except Exception as e:
        log("EXC "+str(e)[:60]); return "__ERR__"
def tr(zh):                    # translate, chunking long text by sentence
    if len(zh)<=450:
        t=_one(zh); return None if t is None else (zh if t in ("__LEN__","__ERR__") else t)
    out=[]
    for s in re.split(r'(?<=[。！？!?])',zh):
        if not s.strip(): continue
        t=_one(s)
        if t is None: return None
        out.append(s if t in ("__LEN__","__ERR__") else t)
        if calls>=MAXCALLS: break
    return " ".join(out)
files=sorted(f for f in glob.glob("data/flows/*.json") if os.path.basename(f)!="manifest.json")
for f in files:
    if QUOTA[0] or calls>=MAXCALLS: break
    r=json.load(open(f)); ch=False
    for b in r["flow"]:
        if QUOTA[0] or calls>=MAXCALLS: break
        if b["type"]=="stanza" and b.get("zh") and not b.get("en"):
            en=[]
            for ln in b["zh"]:
                t=tr(ln)
                if t is None: break
                en.append(t)
                if calls>=MAXCALLS: break
            if len(en)==len(b["zh"]): b["en"]=en; ch=True
        elif b["type"]=="preface" and b.get("zh") and not b.get("en"):
            t=tr(b["zh"]);
            if t: b["en"]=t; ch=True
        elif b["type"]=="note":
            for pt in b.get("points",[]):
                if QUOTA[0] or calls>=MAXCALLS: break
                if pt.get("zh") and not pt.get("en"):
                    t=tr(pt["zh"])
                    if t is None: break
                    pt["en"]=t; ch=True
    if ch: json.dump(r,open(f,"w"),ensure_ascii=False,indent=1); log("saved %s calls=%d"%(r["slug"],calls))
log("DONE calls=%d quota=%s"%(calls,QUOTA[0]))
