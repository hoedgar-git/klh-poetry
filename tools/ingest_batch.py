import sys,json
sys.path.insert(0,"tools"); from ingest_lib import ingest
inv=json.load(open("data/flows/_inventory.json"))
byid={e["fileId"]:e for e in inv}
for path in sys.argv[1:]:
    try:
        d=json.load(open(path))
        e=byid.get(d.get("id"))
        if not e: print("SKIP no-inv-match", d.get("id")); continue
        nh,nimg,nb=ingest(d,e["kind"],e["slug"],e["title"])
        print(f"OK {e['slug']:16} {e['kind']:5} blocks={nb} haiku={nh} img={nimg}")
    except Exception as ex:
        print("ERR",path,str(ex)[:100])

def scan():
    import glob,os
    trs=sorted(glob.glob("/var/folders/ck/n7jlpv6908g75qp8j9yd7hww0000gn/T/claude-hostloop-plugins/916c06e11f4c7617/projects/*/*/tool-results/mcp-e8c72497-*download_file_content-*.txt"), key=os.path.getmtime)
    inv=json.load(open("data/flows/_inventory.json")); byid={e["fileId"]:e for e in inv}
    n=0
    for p in trs:
        try: d=json.load(open(p))
        except Exception: continue
        e=byid.get(d.get("id"))
        if not e: continue
        if os.path.exists(f"data/flows/{e['slug']}.json"): continue   # already done
        try:
            nh,nimg,nb=ingest(d,e["kind"],e["slug"],e["title"]); n+=1
            print(f"OK {e['slug']:16} {e['kind']:5} blocks={nb} haiku={nh} img={nimg}")
        except Exception as ex: print("ERR",e['slug'],str(ex)[:80])
    print("scan ingested",n)
if len(sys.argv)>1 and sys.argv[1]=="--scan": scan()
