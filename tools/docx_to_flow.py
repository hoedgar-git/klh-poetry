#!/usr/bin/env python3
"""docx_to_flow.py — ingestion engine for the KLH poetry site (v4).
Rules:
- '**' is the ONLY commentary marker. A new '**' paragraph starts a new commentary POINT.
- Non-'**' text that follows commentary CONTINUES the previous point.
- Non-'**' text before the poem body is front-matter (preface), never commentary.
- Starred text before the poem body is still preface (ignore stars) — not commentary.
- Adjacent commentary points are grouped into ONE note block (rendered with light separators).
- Blank lines inside a text paragraph split it into separate stanzas (no double-spacing;
  restores N-line groupings).
- URLs always render as link blocks (never commentary); bare labels (YouTube/Links) dropped.
"""
import sys, os, re, zipfile, io, argparse, json
import xml.etree.ElementTree as ET
W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
A='http://schemas.openxmlformats.org/drawingml/2006/main'
NUM=re.compile(r'^\s*\d{1,4}\s*[.。、]\s*$')
NUMLEAD=re.compile(r'^\s*\d{1,4}\s*[.。、]\s')
URL=re.compile(r'https?://\S+')
CAPCUE=('攝影','照片','網路','圖：','圖/','Photo','photo','（網路','Masquerade','Carnival')
LABEL=re.compile(r'^(youtube|links?|連結|影音|歌曲連結|song links?|link[:：])',re.I)

def _resize(data,max_px=1600,q=82):
    try:
        from PIL import Image
        im=Image.open(io.BytesIO(data)); im.load()
        if im.mode in ('RGBA','P','LA'): im=im.convert('RGB')
        w,h=im.size
        if max(w,h)>max_px:
            s=max_px/max(w,h); im=im.resize((int(w*s),int(h*s)))
        o=io.BytesIO(); im.save(o,'JPEG',quality=q,optimize=True); return o.getvalue()
    except Exception:
        return data

def parse_docx(path):
    z=zipfile.ZipFile(path)
    rels=z.read('word/_rels/document.xml.rels').decode('utf-8','ignore')
    relmap=dict(re.findall(r'Id="([^"]+)"[^>]*Target="([^"]+)"',rels))
    body=ET.fromstring(z.read('word/document.xml')).find(f'{{{W}}}body')
    blocks=[]
    for para in body.findall(f'{{{W}}}p'):
        parts=[]
        for node in para.iter():
            tag=node.tag.split('}')[-1]
            if tag=='t' and node.text: parts.append(node.text)
            elif tag=='br': parts.append('\n')
            elif tag=='tab': parts.append('\t')
        text=''.join(parts)
        for blip in para.iter(f'{{{A}}}blip'):
            tgt=relmap.get(blip.get(f'{{{R}}}embed'))
            if not tgt: continue
            name=tgt if tgt.startswith('word/') else 'word/'+tgt.replace('../','')
            name=name.replace('word/word/','word/')
            try: data=z.read(name)
            except KeyError:
                try: data=z.read('word/'+os.path.basename(tgt))
                except KeyError: continue
            blocks.append({'kind':'image','data':data})
        if text.strip(): blocks.append({'kind':'text','text':text})
    return blocks

def _cap(t):
    t=t.strip()
    if NUM.match(t) or NUMLEAD.match(t) or URL.search(t): return False
    if any(c in t for c in CAPCUE): return True
    return len(t)<=52

def build_flow(blocks, kind, slug, images_dir, max_px=1600):
    os.makedirs(images_dir,exist_ok=True)
    flow=[]; n=0; seen=0; body=False; note=None; last=None; byl=False
    for b in blocks:
        if b['kind']=='image':
            n+=1; fn=f'img{n}.jpg'
            open(os.path.join(images_dir,fn),'wb').write(_resize(b['data'],max_px))
            last={'type':'image','src':f'images/{slug}/{fn}','caption_zh':'','caption_en':''}
            flow.append(last); note=None; continue
        raw=b['text']; star=raw.strip().startswith('**')
        t=re.sub(r'^\*+\s*','',raw).strip()
        if not t: continue
        # caption directly after an image
        if last is not None and not last['caption_zh']:
            if (not star and _cap(t)) or (star and len(t)<=60 and any(c in t for c in CAPCUE)):
                last['caption_zh']=t; last=None; continue
        last=None
        # links -> always a link block
        urls=URL.findall(t)
        if urls:
            if flow and flow[-1]['type']=='yt': flow[-1]['urls']+=urls
            else: flow.append({'type':'yt','urls':urls})
            note=None; continue
        if LABEL.match(t) and len(t)<40:   # bare "YouTube" / "Links:" label
            continue
        # title / byline (poem)
        if seen==0 and kind=='poem' and not star:
            flow.append({'type':'title','zh':t}); seen+=1; continue
        if t in ('何康隆','Khang-Loon Ho','何康隆 Khang-Loon Ho'):
            byl=True; flow.append({'type':'byline','zh':t}); seen+=1; continue
        # front-matter subtitle: non-star text before the byline (location line, series header)
        if not star and not byl:
            flow.append({'type':'subtitle','zh':t}); seen+=1; continue
        # numbered line: real haiku header (big number, or when not mid-commentary)
        # vs a small "1./2./3." list item inside commentary (keep it in the commentary)
        if NUM.match(t) or NUMLEAD.match(t):
            numval=int(re.match(r'\s*(\d+)',t).group(1))
            if note is None or numval>=100:
                body=True; note=None
                flow.append({'type':'stanza','zh':[t],'en':[],'num':True}); seen+=1; continue
            note['points'][-1]['zh'] += '\n'+t; seen+=1; continue
        if star:
            if not body:
                flow.append({'type':'preface','zh':t}); seen+=1; continue
            if note is None:
                note={'type':'note','points':[]}; flow.append(note)
            note['points'].append({'zh':t,'en':''}); seen+=1; continue
        # non-star text
        if note is not None:
            note['points'][-1]['zh'] += '\n'+t; seen+=1; continue
        body=True
        for g in re.split(r'\n\s*\n', raw.strip()):
            lines=[ln.strip() for ln in g.split('\n') if ln.strip()!='']
            if lines: flow.append({'type':'stanza','zh':lines,'en':[]})
        seen+=1
    return flow

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('docx'); ap.add_argument('--kind',required=True)
    ap.add_argument('--slug',required=True); ap.add_argument('--title',default=''); ap.add_argument('--repo',default='.')
    a=ap.parse_args()
    blocks=parse_docx(a.docx); flow=build_flow(blocks,a.kind,'flow/'+a.slug,os.path.join(a.repo,'images','flow',a.slug))
    os.makedirs(os.path.join(a.repo,'data','flows'),exist_ok=True)
    json.dump({'slug':a.slug,'kind':a.kind,'title':a.title,'source':os.path.basename(a.docx),'flow':flow},
              open(os.path.join(a.repo,'data','flows',a.slug+'.json'),'w'),ensure_ascii=False,indent=1)
    print("OK",a.slug,len(flow),"blocks")
if __name__=='__main__': main()
