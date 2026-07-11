#!/usr/bin/env python3
"""docx_to_flow.py — KLH poetry ingestion engine (v5).
Key spacing rule: consecutive non-empty lines = ONE stanza (tight); a BLANK
paragraph (or blank line) ends the stanza. Numbered haiku headers begin a new
stanza that includes the number + its lines as one tight block.
Commentary = '**' only (grouped into one note block of points; non-'**' continues
the previous point; small numbered list items inside commentary stay commentary).
Front-matter before the byline is subtitle/preface (never commentary). URLs -> links."""
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
        imgs=[]
        for blip in para.iter(f'{{{A}}}blip'):
            tgt=relmap.get(blip.get(f'{{{R}}}embed'))
            if not tgt: continue
            name=tgt if tgt.startswith('word/') else 'word/'+tgt.replace('../','')
            name=name.replace('word/word/','word/')
            try: data=z.read(name)
            except KeyError:
                try: data=z.read('word/'+os.path.basename(tgt))
                except KeyError: continue
            imgs.append(data)
        for data in imgs: blocks.append({'kind':'image','data':data})
        if text.strip(): blocks.append({'kind':'text','text':text})
        elif not imgs: blocks.append({'kind':'blank'})
    return blocks

def _cap(t):
    t=t.strip()
    if NUM.match(t) or NUMLEAD.match(t) or URL.search(t): return False
    if any(c in t for c in CAPCUE): return True
    return len(t)<=52

def build_flow(blocks, kind, slug, images_dir, max_px=1600):
    os.makedirs(images_dir,exist_ok=True)
    flow=[]; n=0; seen=0; body=False; note=None; last=None; byl=False
    st={'lines':[],'num':False}
    def flush():
        if st['lines']:
            b={'type':'stanza','zh':st['lines'][:],'en':[]}
            if st['num']: b['num']=True
            flow.append(b)
        st['lines']=[]; st['num']=False
    for b in blocks:
        if b['kind']=='blank':
            flush(); continue
        if b['kind']=='image':
            flush()
            n+=1; fn=f'img{n}.jpg'
            open(os.path.join(images_dir,fn),'wb').write(_resize(b['data'],max_px))
            last={'type':'image','src':f'images/{slug}/{fn}','caption_zh':'','caption_en':''}
            flow.append(last); note=None; continue
        raw=b['text']; star=raw.strip().startswith('**')
        t=re.sub(r'^\*+\s*','',raw).strip()
        if not t: continue
        if last is not None and not last['caption_zh']:
            if (not star and _cap(t)) or (star and len(t)<=60 and any(c in t for c in CAPCUE)):
                last['caption_zh']=t; last=None; continue
        last=None
        urls=URL.findall(t)
        if urls:
            flush()
            if flow and flow[-1]['type']=='yt': flow[-1]['urls']+=urls
            else: flow.append({'type':'yt','urls':urls})
            note=None; continue
        if LABEL.match(t) and len(t)<40: continue
        if seen==0 and kind=='poem' and not star:
            flush(); flow.append({'type':'title','zh':t}); seen+=1; continue
        if t in ('何康隆','Khang-Loon Ho','何康隆 Khang-Loon Ho'):
            flush(); byl=True; flow.append({'type':'byline','zh':t}); seen+=1; continue
        if not star and not byl:
            flush(); flow.append({'type':'subtitle','zh':t}); seen+=1; continue
        if NUM.match(t) or NUMLEAD.match(t):
            numval=int(re.match(r'\s*(\d+)',t).group(1))
            if note is None or numval>=100:
                flush(); body=True; note=None; st['lines']=[t]; st['num']=True; seen+=1; continue
            note['points'][-1]['zh'] += '\n'+t; seen+=1; continue
        if star:
            flush()
            if not body: flow.append({'type':'preface','zh':t}); seen+=1; continue
            if note is None: note={'type':'note','points':[]}; flow.append(note)
            note['points'].append({'zh':t,'en':''}); seen+=1; continue
        if note is not None:
            note['points'][-1]['zh'] += '\n'+t; seen+=1; continue
        body=True
        for ln in raw.split('\n'):
            if ln.strip()=='' : flush()
            else: st['lines'].append(ln.strip())
        seen+=1
    flush()
    return flow

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('docx'); ap.add_argument('--kind',required=True)
    ap.add_argument('--slug',required=True); ap.add_argument('--title',default=''); ap.add_argument('--repo',default='.')
    a=ap.parse_args()
    flow=build_flow(parse_docx(a.docx),a.kind,'flow/'+a.slug,os.path.join(a.repo,'images','flow',a.slug))
    os.makedirs(os.path.join(a.repo,'data','flows'),exist_ok=True)
    json.dump({'slug':a.slug,'kind':a.kind,'title':a.title,'source':os.path.basename(a.docx),'flow':flow},
              open(os.path.join(a.repo,'data','flows',a.slug+'.json'),'w'),ensure_ascii=False,indent=1)
    print("OK",a.slug,len(flow))
if __name__=='__main__': main()
