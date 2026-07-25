#!/usr/bin/env python3
"""ingest_local.py — ingest a LOCAL .docx (from the Google Drive mirror) into the
flow model, mirroring tools/ingest_lib.ingest() but reading the file directly
instead of base64. Run from repo root.

Usage as module:  from ingest_local import ingest_local
CLI:  python3 tools/ingest_local.py <docx> <kind> <slug> <title> [--out data/flows]
"""
import os, sys, json, shutil, re, argparse
sys.path.insert(0, os.path.dirname(__file__))
import docx_to_flow as E
from ingest_lib import _apply


def ingest_local(path, kind, slug, title, out_dir="data/flows", images_root="images"):
    real = os.path.join(images_root, "flow", slug)
    if os.path.exists(real):
        shutil.rmtree(real)
    flow = E.build_flow(E.parse_docx(path), kind, "flow/" + slug, real)
    _apply(flow)
    if kind == "haiku":
        front, haiku, cur = [], [], None
        for b in flow:
            if b["type"] == "stanza" and b.get("num"):
                m = re.match(r'\s*(\d+)', b["zh"][0]); n = int(m.group(1)) if m else 0
                cur = {"n": n, "flow": [b]}; haiku.append(cur)
            elif cur is None:
                front.append(b)
            else:
                cur["flow"].append(b)
        rec = {"slug": slug, "kind": "haiku", "title": title,
               "source": os.path.basename(path), "front": front, "haiku": haiku}
        nh = len(haiku)
    else:
        rec = {"slug": slug, "kind": kind, "title": title,
               "source": os.path.basename(path), "flow": flow}
        nh = 0
    os.makedirs(out_dir, exist_ok=True)
    json.dump(rec, open(os.path.join(out_dir, slug + ".json"), "w"),
              ensure_ascii=False, indent=1)
    nimg = sum(1 for b in flow if b["type"] == "image")
    return nh, nimg, len(flow)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("docx"); ap.add_argument("kind"); ap.add_argument("slug"); ap.add_argument("title")
    ap.add_argument("--out", default="data/flows"); ap.add_argument("--images", default="images")
    a = ap.parse_args()
    nh, nimg, nb = ingest_local(a.docx, a.kind, a.slug, a.title, a.out, a.images)
    print(f"OK {a.slug} kind={a.kind} blocks={nb} haiku={nh} img={nimg}")
