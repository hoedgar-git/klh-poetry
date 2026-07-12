import json,base64,os,sys,shutil
sys.path.insert(0,'tools'); import docx_to_flow as E
T="/var/folders/ck/n7jlpv6908g75qp8j9yd7hww0000gn/T/claude-hostloop-plugins/916c06e11f4c7617/projects/-Users-edgar2025-Library-Application-Support-Claude-local-agent-mode-sessions-350f3aa4-7ea1-4f66-9659-b4d39ebead86-a2c1a424-94af-4444-8bef-199316e55d29-local-3cc336cf-04eb-4c99-8543-ff98ca1e92b5-outpu-maqfx5/eb916c67-f84f-438d-be1f-9b8021b6e7d4/tool-results/mcp-e8c72497-3d53-431f-9f62-72e02313374e-download_file_content-"
jobs=[("1783733037260","hdoc15"),("1783733038430","hdoc30"),("1783733043637","hdoc61"),("1783733046917","hdoc105"),("1783733049908","hdoc148")]
tmp="tools/_h.docx"
for ts,slug in jobs:
    d=json.load(open(T+ts+".txt")); open(tmp,"wb").write(base64.b64decode(d["content"]))
    old=json.load(open(f"data/flows/{slug}.json"))
    real="images/flow/"+slug
    if os.path.exists(real): shutil.rmtree(real)
    flow=E.build_flow(E.parse_docx(tmp),"haiku","flow/"+slug,real)
    json.dump({"slug":slug,"kind":"haiku","title":old.get("title",""),"source":d["title"],"flow":flow},open(f"data/flows/{slug}.json","w"),ensure_ascii=False,indent=1)
os.remove(tmp)
# verify hdoc30 around 295
r=json.load(open("data/flows/hdoc30.json"))
hit=False
for b in r["flow"]:
    if b["type"]=="stanza" and b.get("num") and b["zh"][0].strip().startswith("295"): hit=True
    if b["type"]=="note":
        for pt in b["points"]:
            if "\n1" in pt["zh"] or pt["zh"].strip().startswith("1"): print("295-area commentary point (first 90):", pt["zh"][:90].replace(chr(10)," / "))
print("has 295 header stanza:",hit)
