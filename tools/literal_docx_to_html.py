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

# Same '**' signal used by docx_to_flow.py (engine v5) to detect commentary —
# reused here ONLY to tag paragraphs for CSS styling (smaller/plainer font).
# No reorganization, grouping, or removal of content — literal order is untouched.
NUM = re.compile(r'^\s*\d{1,4}\s*[.。、]\s*$')
NUMLEAD = re.compile(r'^\s*\d{1,4}\s*[.。、]\s')
URLRE = re.compile(r'https?://\S+')


def qn(tag):
    return '{%s}%s' % (W, tag)


def dominant_size(doc_xml):
    """Half-point font size used most often in the doc — our '100%' baseline."""
    from collections import Counter
    sizes = re.findall(r'<w:sz w:val="(\d+)"/>', doc_xml)
    if not sizes:
        return 24  # 12pt fallback
    return int(Counter(sizes).most_common(1)[0][0])


def parse(path):
    z = zipfile.ZipFile(path)
    rels_xml = z.read('word/_rels/document.xml.rels').decode('utf-8', 'ignore')
    rel_full = dict(re.findall(r'<Relationship[^>]*Id="([^"]+)"[^>]*Target="([^"]+)"', rels_xml))
    doc_xml_raw = z.read('word/document.xml').decode('utf-8', 'ignore')
    base_sz = dominant_size(doc_xml_raw)

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
        plain_parts = []

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
            sz_ratio = None
            if rPr is not None:
                szEl = rPr.find(qn('sz'))
                if szEl is not None:
                    try:
                        v = int(szEl.get(qn('val')))
                        if v and abs(v - base_sz) >= 2:
                            sz_ratio = round(v / base_sz, 2)
                    except (TypeError, ValueError):
                        pass
            pieces = []
            for node in run:
                t = node.tag.split('}')[-1]
                if t == 't' and node.text:
                    pieces.append(html.escape(node.text))
                    plain_parts.append(node.text)
                elif t == 'br':
                    pieces.append('<br>')
                    plain_parts.append('\n')
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
            if sz_ratio:
                txt = '<span style="font-size:%sem">%s</span>' % (sz_ratio, txt)
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

        plain = ''.join(plain_parts)
        stripped = plain.strip()
        out.append({
            'align': align,
            'html': ''.join(runs_html),
            'has_text': has_text,
            'images': images,
            'star': stripped.startswith('**'),
            'is_num': bool(NUM.match(stripped) or NUMLEAD.match(stripped)),
            'has_url': bool(URLRE.search(plain)),
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
    in_note = False
    for p in paras:
        if p['images']:
            in_note = False
            for tgt in p['images']:
                src = load_image(z, tgt)
                if src:
                    body.append('<div class="docx-img"><img src="%s" alt=""></div>' % src)
        if p['has_text']:
            # Mirror docx_to_flow's '**' commentary signal purely for styling:
            # a numbered stanza line or a link line ends any commentary run;
            # a '**'-prefixed line starts (or continues) one. Order/content
            # is untouched — this only adds a CSS class.
            if p['is_num'] or p['has_url']:
                in_note = False
            elif p['star']:
                in_note = True
            classes = []
            if in_note:
                classes.append('docx-note')
            style = ''
            if p['align'] == 'center':
                style = ' style="text-align:center"'
            elif p['align'] == 'right':
                style = ' style="text-align:right"'
            cls = ' class="%s"' % ' '.join(classes) if classes else ''
            body.append('<p%s%s>%s</p>' % (cls, style, p['html']))
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
