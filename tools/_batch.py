import json,base64,os,sys
sys.path.insert(0,'tools')
import docx_to_flow as E
T="/var/folders/ck/n7jlpv6908g75qp8j9yd7hww0000gn/T/claude-hostloop-plugins/916c06e11f4c7617/projects/-Users-edgar2025-Library-Application-Support-Claude-local-agent-mode-sessions-350f3aa4-7ea1-4f66-9659-b4d39ebead86-a2c1a424-94af-4444-8bef-199316e55d29-local-3cc336cf-04eb-4c99-8543-ff98ca1e92b5-outpu-maqfx5/eb916c67-f84f-438d-be1f-9b8021b6e7d4/tool-results/"
jobs=[
 ("1783226805132","poem","p_5e319b47","印度之歌"),
 ("1783226843648","poem","p_c2ae755f","貝加爾湖漫步隨想"),
 ("1783226867730","poem","p_c1745bf6","光燦的古城"),
 ("1783226866910","poem","p_5cea581e","那時愛琴海沒有名字"),
 ("1783226865267","poem","p_c595ebe4","飛越Okavango內陸三角洲"),
 ("1783226889736","haiku","hdoc30","現代俳句和變奏 30"),
 ("1783226890833","haiku","hdoc15","現代俳句和變奏 15"),
 ("1783226895153","haiku","hdoc105","現代俳句和變奏 105"),
 ("1783226896499","haiku","hdoc148","現代俳句和變奏 148"),
 ("1783226897633","haiku","hdoc61","現代俳句和變奏 61"),
]
os.makedirs("data/flows",exist_ok=True)
tmp="tools/_tmp.docx"
for ts,kind,slug,title in jobs:
    p=T+"mcp-e8c72497-3d53-431f-9f62-72e02313374e-download_file_content-"+ts+".txt"
    d=json.load(open(p))
    open(tmp,"wb").write(base64.b64decode(d["content"]))
    blocks=E.parse_docx(tmp)
    imgdir="images/flow/"+slug
    flow=E.build_flow(blocks,kind,"flow/"+slug,imgdir)
    rec={"slug":slug,"kind":kind,"title":title,"source":d["title"],"flow":flow}
    json.dump(rec,open("data/flows/"+slug+".json","w"),ensure_ascii=False,indent=1)
    nimg=sum(1 for f in flow if f["type"]=="image")
    ntxt=sum(1 for f in flow if f["type"] in ("stanza","note","title","byline"))
    print(f"{slug:14s} {kind:6s} blocks={len(flow):4d} images={nimg:3d} text={ntxt:4d}  src={d['title'][:32]}")
os.remove(tmp)
print("DONE")
