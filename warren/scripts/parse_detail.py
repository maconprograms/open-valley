#!/usr/bin/env python3
"""Parse a NEMRC Warren VT camadetail HTML page into a flat dict. Stdlib only.

The page nests tables several levels deep, so we capture EVERY <td>'s *direct*
text (text inside that cell but not inside a deeper nested <td>) using a stack.
Leaf cells (labels, values, headers) get their real text; wrapper cells get
none and are skipped. We then walk the cells in document order:
  - class 'camaHeader' -> sets the current section
  - class 'camaLabel'  -> a label; its value is the next following cell that is
    not itself a label or header.
BUILDING / LAND are all-caps rowspan markers; each starts a numbered sub-section.
<br> inside a cell is preserved as ' | ' (used to split the owner mailing block).
"""
import sys, json, re
from html.parser import HTMLParser


class CellExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.cells = []      # ordered: {"cls": set, "buf": [...]} -> text later
        self.stack = []      # open <td> frames (references into self.cells)

    def handle_starttag(self, tag, attrs):
        if tag == 'br' and self.stack:
            self.stack[-1]['buf'].append('\n')
            return
        if tag == 'td':
            d = dict(attrs)
            cell = {'cls': set((d.get('class') or '').split()), 'buf': []}
            self.cells.append(cell)   # record in document (start) order
            self.stack.append(cell)

    def handle_startendtag(self, tag, attrs):
        if tag == 'br' and self.stack:
            self.stack[-1]['buf'].append('\n')

    def handle_endtag(self, tag):
        if tag == 'td' and self.stack:
            self.stack.pop()

    def handle_data(self, data):
        if self.stack:                # direct text -> innermost open <td>
            self.stack[-1]['buf'].append(data)

    def handle_entityref(self, name):
        if self.stack:
            self.stack[-1]['buf'].append({'nbsp': ' ', 'amp': '&'}.get(name, ''))

    def finalize(self):
        for c in self.cells:
            raw = ''.join(c['buf']).replace('\xa0', ' ')
            lines = [' '.join(ln.split()) for ln in raw.split('\n')]
            c['text'] = ' | '.join(ln for ln in lines if ln)
        return self.cells


def parse(html):
    p = CellExtractor()
    p.feed(html)
    cells = p.finalize()
    out = {}
    section = 'General'
    seen = {}
    sec_seen = {}

    def put(key, val):
        full = f"{section} / {key}"
        if full in out:
            seen[full] = seen.get(full, 1) + 1
            full = f"{full} #{seen[full]}"
        out[full] = val

    n = len(cells)
    for i, c in enumerate(cells):
        if 'camaHeader' in c['cls']:
            if c['text']:
                section = c['text']
        elif 'camaLabel' in c['cls']:
            label = c['text']
            if not label:
                continue
            if label in ('BUILDING', 'LAND'):
                sec_seen[label] = sec_seen.get(label, 0) + 1
                section = label if sec_seen[label] == 1 else f"{label} #{sec_seen[label]}"
                continue
            val = ''
            for j in range(i + 1, n):
                nj = cells[j]['cls']
                if 'camaLabel' in nj or 'camaHeader' in nj:
                    break
                if cells[j]['text']:
                    val = cells[j]['text']
                    break
            put(label, val)
    return out


if __name__ == '__main__':
    html = open(sys.argv[1], encoding='utf-8', errors='replace').read()
    print(json.dumps(parse(html), indent=2, ensure_ascii=False))
