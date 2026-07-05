#!/usr/bin/env python3
"""docx_to_flow.py — reusable ingestion engine for the KLH poetry site.
Turns a .docx into an ORDERED, lossless 'flow' of typed blocks that preserve
the author's exact in-document sequence, and extracts + resizes images.
Block types: title, byline, epigraph, stanza, note, image(+caption), yt(links).
Raw text is always preserved so any auto-tag can be corrected by hand."""
import sys, os, json, re, zipfile, io, argparse
import xml.etree.ElementTree as ET
W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
A='http://schemas.openxmlformats.org/drawingml/2006/main'
NUM=re.compile(r'^\s*\d{1,4}\s*[.。、]\s*$')          # haiku header e.g. "601."
NUMLEAD=re.compile(r'^\s*\d{1,4}\s*[.。、]\s')          # "601. text"
URL=re.compile(r'https?://\S+')
CAPCUE=('攝影','照片','網路','圖：','圖/','Photo','photo','（網路','Masquerade','Carnival')

def _resize(data, max_px=1600, quality=82):
    try:
        from PIL import Image
        im=Image.open(io.BytesIO(data)); im.load()
        if im.mode in ('RGBA','P','LA'): im=im.convert('RGB')
        w,h=im.size
        if max(w,h)>max_px:
            s=max_px/max(w,h); im=im.resize((int(w*s),int(h*s)))
        o=io.BytesIO(); im.save(o,'JPEG',quality=quality,optimize=True); return o.getvalue()
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
            imgs.append((os.path.splitext(tgt)[1] or '.jpeg', data))
        for ext,data in imgs: blocks.append({'kind':'image','ext':ext,'data':data})
        if text.strip(): blocks.append({'kind':'text','text':text.strip()})
    return blocks

def _looks_caption(t):
    t=t.strip()
    if NUM.match(t) or NUMLEAD.match(t): return False
    if URL.search(t): return False
    if any(c in t for c in CAPCUE): return True
    return len(t)<=52

def build_flow(blocks, kind, slug, images_dir, max_px=1600):
    os.makedirs(images_dir, exist_ok=True)
    flow=[]; n=0; note_mode=False; text_seen=0; verse_seen=False; last_img=None
    for b in blocks:
        if b['kind']=='image':
            n+=1; fn=f'img{n}.jpg'
            open(os.path.join(images_dir,fn),'wb').write(_resize(b['data'],max_px))
            last_img={'type':'image','src':f'images/{slug}/{fn}','caption_zh':'','caption_en':''}
            flow.append(last_img); continue
        t=re.sub(r'^\*\*\s*','',b['text']).strip()
        is_note_mark=b['text'].strip().startswith('**')
        # caption: short/cue text right after an image with no caption yet
        if last_img is not None and not last_img['caption_zh'] and _looks_caption(t) and not is_note_mark:
            last_img['caption_zh']=t; last_img=None; continue
        if last_img is not None and not last_img['caption_zh'] and is_note_mark and len(t)<=60 and any(c in t for c in CAPCUE):
            last_img['caption_zh']=t; last_img=None; continue
        last_img=None
        # youtube / links
        urls=URL.findall(t)
        if urls and len(t)-sum(len(u) for u in urls) < 30:
            if flow and flow[-1]['type']=='yt': flow[-1]['urls']+=urls
            else: flow.append({'type':'yt','label':'','urls':urls})
            continue
        # headers / structure
        if text_seen==0 and kind=='poem':
            flow.append({'type':'title','zh':t}); text_seen+=1; continue
        if t in ('何康隆','Khang-Loon Ho','何康隆 Khang-Loon Ho'):
            flow.append({'type':'byline','zh':t}); text_seen+=1; continue
        if NUM.match(t) or NUMLEAD.match(t):
            note_mode=False; verse_seen=True
            flow.append({'type':'stanza','zh':t.split('\n'),'en':[],'num':True}); text_seen+=1; continue
        if not verse_seen and (t.startswith('「') or t.startswith('“')) and not is_note_mark:
            flow.append({'type':'epigraph','zh':t}); text_seen+=1; continue
        if is_note_mark: note_mode=True
        if note_mode:
            flow.append({'type':'note','zh':t,'en':''})
        else:
            verse_seen=True
            flow.append({'type':'stanza','zh':t.split('\n'),'en':[]})
        text_seen+=1
    return flow

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('docx'); ap.add_argument('--kind',required=True,choices=['poem','haiku','artwork'])
    ap.add_argument('--slug',required=True); ap.add_argument('--title',default=''); ap.add_argument('--repo',default='.')
    ap.add_argument('--maxpx',type=int,default=1600); a=ap.parse_args()
    imgd=os.path.join(a.repo,'images',a.slug); blocks=parse_docx(a.docx)
    flow=build_flow(blocks,a.kind,a.slug,imgd,a.maxpx)
    os.makedirs(os.path.join(a.repo,'data','flows'),exist_ok=True)
    rec={'slug':a.slug,'kind':a.kind,'title':a.title,'source':os.path.basename(a.docx),'flow':flow}
    json.dump(rec,open(os.path.join(a.repo,'data','flows',a.slug+'.json'),'w'),ensure_ascii=False,indent=1)
    print(f"OK {a.slug}: {len(flow)} blocks, {sum(1 for f in flow if f['type']=='image')} images")

if __name__=='__main__': main()
