import json,base64,os,sys,shutil
sys.path.insert(0,'tools'); import docx_to_flow as E
T="/var/folders/ck/n7jlpv6908g75qp8j9yd7hww0000gn/T/claude-hostloop-plugins/916c06e11f4c7617/projects/-Users-edgar2025-Library-Application-Support-Claude-local-agent-mode-sessions-350f3aa4-7ea1-4f66-9659-b4d39ebead86-a2c1a424-94af-4444-8bef-199316e55d29-local-3cc336cf-04eb-4c99-8543-ff98ca1e92b5-outpu-maqfx5/eb916c67-f84f-438d-be1f-9b8021b6e7d4/tool-results/mcp-e8c72497-3d53-431f-9f62-72e02313374e-download_file_content-"
jobs=[
 ("1783733013437","poem","p_5e319b47"),
 ("1783733016089","poem","p_c2ae755f"),
 ("1783733018509","poem","p_c1745bf6"),
 ("1783733019915","poem","p_5cea581e"),
 ("1783733021041","poem","p_c595ebe4"),
 ("1783733037260","haiku","hdoc15"),
 ("1783733038430","haiku","hdoc30"),
 ("1783733043637","haiku","hdoc61"),
 ("1783733046917","haiku","hdoc105"),
 ("1783733049908","haiku","hdoc148"),
]
def norm(flow):
    # compare ignoring image src filename (only structure/text/captions)
    out=[]
    for b in flow:
        c=dict(b); c.pop('src',None)
        out.append(c)
    return json.dumps(out,ensure_ascii=False,sort_keys=True)

changed=[]; unchanged=[]
tmpdoc="tools/_u.docx"; tmpimg="tools/_uimg"
for ts,kind,slug in jobs:
    d=json.load(open(T+ts+".txt"))
    open(tmpdoc,"wb").write(base64.b64decode(d["content"]))
    if os.path.exists(tmpimg): shutil.rmtree(tmpimg)
    blocks=E.parse_docx(tmpdoc)
    newflow=E.build_flow(blocks,kind,"flow/"+slug,tmpimg)
    oldpath="data/flows/"+slug+".json"
    old=json.load(open(oldpath)) if os.path.exists(oldpath) else {"flow":[]}
    if norm(newflow)!=norm(old.get("flow",[])):
        changed.append(slug)
        # replace images
        real="images/flow/"+slug
        if os.path.exists(real): shutil.rmtree(real)
        shutil.move(tmpimg, real)
        rec={"slug":slug,"kind":kind,"title":old.get("title",""),"source":d["title"],"flow":newflow}
        json.dump(rec,open(oldpath,"w"),ensure_ascii=False,indent=1)
    else:
        unchanged.append(slug)
        if os.path.exists(tmpimg): shutil.rmtree(tmpimg)
if os.path.exists(tmpdoc): os.remove(tmpdoc)
print("CHANGED:",changed)
print("UNCHANGED:",unchanged)
