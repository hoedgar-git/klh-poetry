#!/usr/bin/env python3
"""literal_docx_to_html.py — render a .docx AS-IS to standalone HTML.

No reorganization, no stanza grouping, no commentary detection, no
translation. Every paragraph in document order becomes one <p> (or an
<img> block for an image paragraph), preserving:
  - paragraph order (exact)
  - bold / italic runs
  - line breaks (<w:br/>) within a paragraph
  - hyperlinks
  - paragraph alignment (center/right) if set in the doc
  - blank paragraphs (kept as empty spacer <p> so vertical rhythm matches
    the original Word doc)
  - inline images (embedded as base64 so the HTML is self-contained)

Usage: python3 literal_docx_to_html.py <input.docx> <output.html> "<Title>"
"""
import sys, os, re, zipfile, base64, html
import xml.etree.ElementTree as ET

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
A = 'http://schemas.openxmlformats.org/drawingml/2006/main'


def qn(tag):
    return '{%s}%s' % (W, tag)


def parse(path):
    z = zipfile.ZipFile(path)
    rels_xml = z.read('word/_rels/document.xml.rels').decode('utf-8', 'ignore')
    rel_full = dict(re.findall(r'<Relationship[^>]*Id="([^"]+)"[^>]*Target="([^"]+)"', rels_xml))

    body = ET.fromstring(z.read('word/document.xml')).find(qn('body'))
    out = []
    for para in body.findall(qn('p')):
        align = None
        pPr = para.find(qn('pPr'))
        if pPr is not None:
            jc = pPr.find(qn('jc'))
            if jc is not None:
                v = jc.get(qn('val'))
                if v in ('center', 'right'):
                    align = v

        runs_html = []
        images = []
        has_text = False

        def render_run(run):
            nonlocal has_text
            tag = run.tag.split('}')[-1]
            if tag != 'r':
                buf = []
                for child in run:
                    if child.tag.split('}')[-1] == 'r':
                        buf.append(render_run(child))
                return ''.join(buf)
            rPr = run.find(qn('rPr'))
            bold = rPr is not None and rPr.find(qn('b')) is not None
            italic = rPr is not None and rPr.find(qn('i')) is not None
            pieces = []
            for node in run:
                t = node.tag.split('}')[-1]
                if t == 't' and node.text:
                    pieces.append(html.escape(node.text))
                elif t == 'br':
                    pieces.append('<br>')
                elif t == 'tab':
                    pieces.append('&emsp;')
                elif t == 'drawing':
                    for blip in node.iter('{%s}blip' % A):
                        rid = blip.get(qn('embed')) or blip.get('{%s}embed' % R)
                        tgt = rel_full.get(rid)
                        if tgt:
                            images.append(tgt)
            txt = ''.join(pieces)
            if txt.strip():
                has_text = True
            if not txt:
                return ''
            if bold:
                txt = '<strong>%s</strong>' % txt
            if italic:
                txt = '<em>%s</em>' % txt
            return txt

        def walk_hyperlink(node):
            nonlocal has_text
            rid = node.get(qn('id')) or node.get('{%s}id' % R)
            href = rel_full.get(rid, '')
            inner = []
            for child in node:
                if child.tag.split('}')[-1] == 'r':
                    inner.append(render_run(child))
            txt = ''.join(inner)
            if txt.strip():
                has_text = True
                safe_href = html.escape(href, quote=True)
                runs_html.append('<a href="%s" target="_blank" rel="noopener">%s</a>' % (safe_href, txt))

        for child in para:
            tag = child.tag.split('}')[-1]
            if tag == 'hyperlink':
                walk_hyperlink(child)
            elif tag == 'r':
                runs_html.append(render_run(child))

        out.append({
            'align': align,
            'html': ''.join(runs_html),
            'has_text': has_text,
            'images': images,
        })
    return out, z


def load_image(z, target):
    name = target if target.startswith('word/') else 'word/' + target.replace('../', '')
    name = name.replace('word/word/', 'word/')
    try:
        data = z.read(name)
    except KeyError:
        try:
            data = z.read('word/' + os.path.basename(target))
        except KeyError:
            return None
    ext = os.path.splitext(name)[1].lstrip('.').lower() or 'png'
    if ext == 'jpg':
        ext = 'jpeg'
    return 'data:image/%s;base64,%s' % (ext, base64.b64encode(data).decode('ascii'))


def render_html(paras, z):
    body = []
    for p in paras:
        for tgt in p['images']:
            src = load_image(z, tgt)
            if src:
                body.append('<div class="docx-img"><img src="%s" alt=""></div>' % src)
        if p['has_text']:
            style = ''
            if p['align'] == 'center':
                style = ' style="text-align:center"'
            elif p['align'] == 'right':
                style = ' style="text-align:right"'
            body.append('<p%s>%s</p>' % (style, p['html']))
        elif not p['images']:
            body.append('<p class="docx-blank">&nbsp;</p>')
    return '<div class="docx-literal">\n' + '\n'.join(body) + '\n</div>'


def main():
    inp, outp = sys.argv[1], sys.argv[2]
    paras, z = parse(inp)
    frag = render_html(paras, z)
    open(outp, 'w', encoding='utf-8').write(frag)
    print('wrote', outp, len(frag), 'chars,', len(paras), 'paragraphs')


if __name__ == '__main__':
    main()
