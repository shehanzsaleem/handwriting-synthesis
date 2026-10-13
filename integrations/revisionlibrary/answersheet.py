"""Answer-sheet documents -> handwritten PDF pages.

An answer sheet is a Markdown-like file with YAML front matter::

    ---
    id: 01-maths-implicit
    subject: A-level Maths
    source: Revision Library mock bank a-level-maths, dif-019
    marks: 6
    paper: lined            # lined | narrow | squared | ipad-grid | ipad-dots | plain | exam
    hand: student           # hwsynth.hand.PROFILES key
    hand_overrides: {x_height: 2.4}
    pen: ballpoint          # hwsynth.ink.PENS key
    marker: teacher-red     # pen for marks and teacher comments
    question: |
      A curve is defined implicitly by ...
    score: 6/6              # optional ringed total at the end
    ---
    ## Q4 (a)
    Differentiate implicitly with respect to $x$:  {M1}
    $$ y^2 + 2xy\\frac{dy}{dx} - 2x = 0 $$  {M1 A1}
    $$ \\frac{dy}{dx} &= \\frac{2x - y^2}{2xy} \\\\ &= -\\frac{7}{6} $$  {A1}
    > Always substitute before rearranging.        (teacher comment, marker pen)
    ::: sketch {width: 80, height: 50}
    items: [...]                                    (hwsynth.sketch spec)
    :::
    ::: table
    | i | numbers[i] | largest |
    :::
    ::: code
    for i = 1 to 3
        if numbers[i] > largest then
    :::
    ---                                             (page break)

Blocks are separated by blank lines. ``{M1 A1}`` at the end of a block is written
in the right margin in the marker pen, level with the block's last line.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import yaml

from hwsynth.export import Scene, to_pdf, to_svg
from hwsynth.hand import PROFILES, Hand, _h
from hwsynth.layoutkit import text_line_box, wrap
from hwsynth.mathtype import Box, MathSetter, _wobbly
from hwsynth.sketch import Sketch

MARKS_RE = re.compile(r'\s*\{((?:[A-Z]\d+|✓|✗|\?)(?:\s+(?:[A-Z]\d+|✓|✗|\?))*)\}\s*$')

# ---------------------------------------------------------------- paper
PAPERS = {
    #            pitch  top   left  right bottom margin_line  background
    'lined':     dict(pitch=8.0, left=32, right=14, bottom=16, rules='lines', margin=28, bg='#ffffff'),
    'narrow':    dict(pitch=7.1, left=32, right=14, bottom=16, rules='lines', margin=28, bg='#ffffff'),
    'squared':   dict(pitch=10.0, left=18, right=14, bottom=16, rules='grid', grid=5.0, bg='#ffffff'),
    'ipad-grid': dict(pitch=9.0, left=16, right=16, bottom=16, rules='grid', grid=6.0, bg='#fcfcfa',
                      grid_colour='#e4e7ec'),
    'ipad-dots': dict(pitch=8.0, left=16, right=16, bottom=16, rules='dots', grid=5.0, bg='#fbfbf9'),
    'plain':     dict(pitch=8.0, left=18, right=16, bottom=16, rules=None, bg='#ffffff'),
    'exam':      dict(pitch=8.5, left=20, right=22, bottom=18, rules='dotted', bg='#ffffff'),
}


def _helv_width(s, size_pt):
    """Approximate Helvetica advance (mm); good enough for wrapping header text."""
    narrow = set('il.,:;|!\'tfjrI ')
    wide = set('mwMW@')
    em = sum(0.28 if c in narrow else 0.83 if c in wide else 0.62 if c.isupper() or c.isdigit() else 0.52
             for c in s)
    return em * size_pt * 25.4 / 72


def _printable(s):
    rep = {'−': '-', 'π': 'pi', 'θ': 'theta', '√': 'sqrt', '≤': '<=', '≥': '>=', '→': '->', '⇌': '<=>',
           '’': "'", '‘': "'", 'Δ': 'Delta', 'λ': 'lambda', 'μ': 'u', 'Σ': 'Sum', '∫': 'integral',
           '≠': '!=', '≈': '~', '₂': '2', '₃': '3', '₄': '4', '⁻': '-', '⁺': '+', '·': '.'}
    return ''.join(rep.get(c, c) for c in s)


def _wrap_print(text, width, size):
    lines = []
    for para in text.strip().split('\n'):
        words, cur = para.split(), ''
        for w in words:
            t = (cur + ' ' + w).strip()
            if cur and _helv_width(t, size) > width:
                lines.append(cur)
                cur = w
            else:
                cur = t
        lines.append(cur)
    return lines


@dataclass
class Block:
    kind: str            # label | text | math | sketch | table | code | comment | pagebreak
    body: str = ''
    marks: list = field(default_factory=list)
    opts: dict = field(default_factory=dict)


def parse(path_or_text):
    src = Path(path_or_text).read_text() if '\n' not in str(path_or_text) else str(path_or_text)
    m = re.match(r'^---\n(.*?)\n---\n', src, re.S)
    meta = yaml.safe_load(m.group(1)) if m else {}
    body = src[m.end():] if m else src
    blocks, lines, i = [], body.split('\n'), 0
    para = []

    def flush():
        if not para:
            return
        text = ' '.join(x.strip() for x in para)
        para.clear()
        marks = []
        mm = MARKS_RE.search(text)
        if mm:
            marks, text = mm.group(1).split(), text[:mm.start()]
        if text.startswith('$$'):
            end = text.rfind('$$')
            blocks.append(Block('math', text[2:end].strip(), marks))
        elif text.startswith('>'):
            blocks.append(Block('comment', re.sub(r'^>\s?', '', text), marks))
        else:
            blocks.append(Block('text', text, marks))

    while i < len(lines):
        ln = lines[i]
        s = ln.strip()
        if s.startswith(':::') and len(s) > 3:
            flush()
            head = s[3:].strip()
            kind, _, rest = head.partition(' ')
            opts = yaml.safe_load(rest) if rest.strip() else {}
            j = i + 1
            content = []
            while j < len(lines) and lines[j].strip() != ':::':
                content.append(lines[j])
                j += 1
            raw = '\n'.join(content)
            marks = []
            if kind in ('sketch',):
                spec = yaml.safe_load(raw) or {}
                spec.update({k: v for k, v in (opts or {}).items() if k in ('width', 'height')})
                blocks.append(Block('sketch', '', opts.get('marks', []) if opts else [], dict(opts or {}, spec=spec)))
            else:
                blocks.append(Block(kind, raw, (opts or {}).get('marks', []), opts or {}))
            i = j + 1
            continue
        if s == '---':
            flush()
            blocks.append(Block('pagebreak'))
        elif s.startswith('#'):
            flush()
            text = s.lstrip('#').strip()
            marks = []
            mm = MARKS_RE.search(text)
            if mm:
                marks, text = mm.group(1).split(), text[:mm.start()]
            blocks.append(Block('label', text, marks))
        elif not s:
            flush()
        else:
            # a display-maths block may span several source lines
            para.append(ln)
            if s.startswith('$$') and not (s.endswith('$$') and len(s) > 2 and s.count('$$') >= 2) \
                    and not re.search(r'\$\$\s*(\{[^}]*\})?\s*$', s[2:]):
                j = i + 1
                while j < len(lines):
                    para.append(lines[j])
                    if re.search(r'\$\$\s*(\{[^}]*\})?\s*$', lines[j].strip()):
                        break
                    j += 1
                i = j
                flush()
        i += 1
    flush()
    return meta, blocks


# ---------------------------------------------------------------- layout
class Composer:
    def __init__(self, meta, cache_dir=None):
        self.meta = meta
        prof = PROFILES[meta.get('hand', 'student')]
        over = dict(meta.get('hand_overrides') or {})
        over.setdefault('seed', int(meta.get('seed', 0)))
        self.hand = Hand(prof.with_(**over), cache_dir=cache_dir)
        mprof = PROFILES[meta.get('marker_hand', 'teacher')]
        self.marker_hand = Hand(mprof.with_(seed=int(meta.get('seed', 0)) + 7,
                                            x_height=meta.get('marker_x_height', mprof.x_height)),
                                cache_dir=cache_dir)
        self.pen = meta.get('pen', 'ballpoint')
        self.marker = meta.get('marker', 'teacher-red')
        self.paper = dict(PAPERS[meta.get('paper', 'lined')])
        self.paper.update(meta.get('paper_overrides') or {})
        self.W, self.H = 210.0, 297.0
        self.pages = []
        self.key = str(meta.get('id', 'doc'))
        self.ms = MathSetter(self.hand, key=self.key + ':math')
        self.mms = MathSetter(self.marker_hand, key=self.key + ':mmath')
        self.scale = float(meta.get('scale', 1.0))

    # -------------------------------------------------------------- pages
    def new_page(self):
        p = self.paper
        sc = Scene(self.W, self.H, background=p['bg'])
        top = 18.0
        if not self.pages:
            top = self._header(sc)
        self._rules(sc, top)
        self.pages.append(sc)
        self.top = top
        self.y_free = top + 1.0
        self.last_base = None

    def _header(self, sc):
        m = self.meta
        x0, x1 = 16.0, self.W - 16.0
        y = 14.0
        info = ' · '.join(str(v) for v in (m.get('subject'), m.get('source'),
                                           f"{m['marks']} marks" if m.get('marks') else None) if v)
        sc.text.append((x0, y, 7.5, _printable(info), '#6b7280', False))
        y += 5.5
        q = m.get('question')
        if q:
            size = float(m.get('question_size', 9.5))
            for ln in _wrap_print(_printable(q), x1 - x0, size):
                sc.text.append((x0, y, size, ln, '#1f2937', False))
                y += size * 0.42
        y += 2.0
        sc.add_rule([[x0, y], [x1, y]], '#9ca3af', 0.25)
        footer = m.get('footer', 'Revision Library · worked answer')
        if footer:
            sc.text.append((x0, self.H - 7.0, 7, _printable(footer), '#9ca3af', False))
        return y + 4.0

    def _rules(self, sc, top):
        p = self.paper
        kind = p.get('rules')
        col = p.get('grid_colour', '#b9d3ee')
        if kind in ('lines', 'dotted'):
            y = top + p['pitch']
            while y < self.H - p['bottom']:
                if kind == 'lines':
                    sc.add_rule([[0, y], [self.W, y]], col, 0.18)
                else:
                    sc.add_rule([[p['left'], y], [self.W - p['right'], y]], '#9ca3af', 0.2, dash=[0.4, 1.2])
                y += p['pitch']
            if p.get('margin'):
                sc.add_rule([[p['margin'], top - 2], [p['margin'], self.H]], '#e8a0a8', 0.25)
            self.rule0 = top + p['pitch']
        elif kind == 'grid':
            g = p['grid']
            x = 0.0
            while x <= self.W:
                sc.add_rule([[x, top - 2], [x, self.H]], col, 0.12)
                x += g
            y = top
            while y <= self.H:
                sc.add_rule([[0, y], [self.W, y]], col, 0.12)
                y += g
            self.rule0 = top + p['pitch']
        elif kind == 'dots':
            g = p['grid']
            pts = [[x, y] for y in np.arange(top, self.H - 4, g) for x in np.arange(g, self.W - 2, g)]
            sc.dots.append((np.array(pts), '#c9cdd3', 0.22))
            self.rule0 = top + p['pitch']
        else:
            self.rule0 = top + p['pitch']

    @property
    def page(self):
        return self.pages[-1]

    def _baseline_for(self, asc, gap=1.2):
        """Lowest-possible baseline on a rule such that the ink clears what is above."""
        p = self.paper
        need = self.y_free + asc + gap
        if p.get('rules') in ('lines', 'dotted', 'grid', 'dots', None):
            k = max(0, math.ceil((need - self.rule0 - 0.25) / p['pitch']))
            base = self.rule0 + k * p['pitch']
            if self.last_base is not None and base <= self.last_base:
                base = self.last_base + p['pitch']
            return base
        return need

    def _fits(self, base, desc):
        return base + desc < self.H - self.paper['bottom']

    def place(self, box: Box, x, asc=None, desc=None, pen=None, hand_rng_key='', min_base=None):
        """Put a box on the next free rule (new page if needed). Returns baseline y."""
        asc = box.ascent if asc is None else asc
        desc = box.descent if desc is None else desc
        base = self._baseline_for(asc)
        if min_base is not None:
            base = max(base, min_base)
        if not self._fits(base, desc):
            self.new_page()
            base = self._baseline_for(asc)
        rng = np.random.default_rng(_h(self.key, hand_rng_key, len(self.pages), base))
        ang = math.radians(rng.normal(0, 0.35))
        c, s = math.cos(ang), math.sin(ang)
        R = np.array([[c, s], [-s, c]])
        jx = rng.normal(0, 0.5)
        strokes = [(st @ R) + [x + jx, base] for st in box.strokes]
        self.page.add_ink(strokes, pen or self.pen, seed=_h(self.key, base, x) % (2 ** 31))
        self.y_free = base + desc
        self.last_base = base
        return base

    def write_marks(self, marks, base):
        if not marks:
            return
        box = text_line_box(self.marker_hand, self.mms, ' '.join(marks), key=f'{self.key}:mk{base:.1f}')
        x = self.W - self.paper['right'] + 1.0 - box.width
        x = min(x, self.W - 6 - box.width)
        self.page.add_ink(box.shifted(x, base), self.marker, seed=int(base * 10))

    # ------------------------------------------------------------- blocks
    def left(self):
        return float(self.paper['left'])

    def width(self):
        return self.W - self.paper['left'] - self.paper['right'] - 16.0

    def compose(self, blocks):
        self.new_page()
        for bi, b in enumerate(blocks):
            k = f'b{bi}'
            if b.kind == 'pagebreak':
                self.new_page()
            elif b.kind == 'label':
                box = text_line_box(self.hand, self.ms, b.body, scale=1.05, key=f'{self.key}:{k}')
                rng = np.random.default_rng(_h(self.key, k))
                ul = _wobbly([[-0.5, box.descent + 0.9], [box.width + 0.8, box.descent + 0.6]], rng, 0.08)
                box = Box(box.width, box.ascent, box.descent + 1.2, box.strokes + [ul])
                x = self.left() - (self.paper['left'] - self.paper.get('margin', self.paper['left'] - 4) + 0) \
                    if self.paper.get('margin') else self.left() - 2
                base = self.place(box, max(x, 6.0), hand_rng_key=k)
                self.write_marks(b.marks, base)
            elif b.kind in ('text', 'comment'):
                hand, ms = (self.marker_hand, self.mms) if b.kind == 'comment' else (self.hand, self.ms)
                pen = self.marker if b.kind == 'comment' else None
                indent = float(b.opts.get('indent', 0))
                lines = wrap(hand, ms, b.body, self.width() - indent, scale=self.scale, key=f'{self.key}:{k}')
                base = None
                for li, ln in enumerate(lines):
                    base = self.place(ln, self.left() + indent, pen=pen, hand_rng_key=f'{k}:{li}')
                self.write_marks(b.marks, base)
            elif b.kind == 'math':
                base = self._math(b, k)
                self.write_marks(b.marks, base)
            elif b.kind == 'sketch':
                self._sketch(b, k)
            elif b.kind == 'table':
                self._table(b, k)
            elif b.kind == 'code':
                self._code(b, k)
            elif b.kind == 'score':
                pass
        if self.meta.get('score'):
            self._score(self.meta['score'])
        return self.pages

    def _math(self, b, k):
        rows = self.ms.layout_lines(b.body, scale=self.scale)
        indent = self.left() + float(b.opts.get('indent', 7.0))
        col = max((l.width for l, _ in rows if l is not None), default=0.0)
        base = None
        for ri, (l, r) in enumerate(rows):
            if l is not None:
                box = Box(col + r.width + 0.7 * self.hand.profile.x_height, max(l.ascent, r.ascent),
                          max(l.descent, r.descent), l.shifted(col - l.width, 0) +
                          r.shifted(col + 0.7 * self.hand.profile.x_height * 0.0, 0))
            else:
                box = r
            base = self.place(box, indent, hand_rng_key=f'{k}:{ri}')
        return base

    def _sketch(self, b, k):
        spec = b.opts['spec']
        sk = Sketch.from_spec(self.hand, spec, key=f'{self.key}:{k}', pen=self.pen,
                              pens={'marker': self.marker})
        h = sk.h
        top = self.y_free + 2.0
        if top + h > self.H - self.paper['bottom']:
            self.new_page()
            top = self.y_free + 2.0
        align = b.opts.get('align', 'center')
        x = self.left() + (self.width() - sk.w) / 2 if align == 'center' else \
            self.left() + float(b.opts.get('indent', 4))
        for pen, strokes in sk.strokes.items():
            self.page.add_ink([s + [x, top] for s in strokes], pen, seed=_h(self.key, k, pen) % (2 ** 31))
        self.y_free = top + h
        self.last_base = None
        if b.marks:
            self.write_marks(b.marks, top + h - 2)

    def _table(self, b, k):
        rows = []
        for ln in b.body.strip().split('\n'):
            ln = ln.strip()
            if not ln.startswith('|') or set(ln) <= set('|-: '):
                continue
            rows.append([c.strip() for c in ln.strip('|').split('|')])
        spec = {'width': self.width(), 'height': 1, 'items': []}
        sk = Sketch(self.hand, spec['width'], 1, key=f'{self.key}:{k}', pen=self.pen)
        W, H = sk.table(rows, col_widths=b.opts.get('col_widths'), row_h=b.opts.get('row_h'))
        top = self.y_free + 3.0
        if top + H > self.H - self.paper['bottom']:
            self.new_page()
            top = self.y_free + 3.0
        x = self.left() + float(b.opts.get('indent', 4))
        for pen, strokes in sk.strokes.items():
            self.page.add_ink([s + [x, top] for s in strokes], pen, seed=_h(self.key, k) % (2 ** 31))
        self.y_free = top + H + 1.0
        self.last_base = None
        if b.marks:
            self.write_marks(b.marks, top + H - 2)

    def _code(self, b, k):
        xh = self.hand.profile.x_height
        indent_unit = float(b.opts.get('indent_unit', 3.2 * xh))
        base = None
        for li, raw in enumerate(b.body.rstrip().split('\n')):
            if not raw.strip():
                continue
            depth = (len(raw) - len(raw.lstrip(' '))) // 4
            line = raw.strip()
            box = text_line_box(self.hand, self.ms, _code_to_text(line), scale=self.scale,
                                key=f'{self.key}:{k}:{li}')
            base = self.place(box, self.left() + float(b.opts.get('indent', 4)) + depth * indent_unit,
                              hand_rng_key=f'{k}:{li}')
        if b.marks:
            self.write_marks(b.marks, base)

    def _score(self, score):
        box = self.mms.layout(score.replace('/', '/'), scale=1.4, display=False)
        x = self.W - self.paper['right'] - box.width - 6
        base = self._baseline_for(box.ascent, gap=3)
        if not self._fits(base, box.descent + 4):
            self.new_page()
            base = self._baseline_for(box.ascent, gap=3)
        self.page.add_ink(box.shifted(x, base), self.marker, seed=7)
        rng = np.random.default_rng(_h(self.key, 'ring'))
        cx, cy = x + box.width / 2, base - (box.ascent - box.descent) / 2
        sk = Sketch(self.marker_hand, 1, 1, key=self.key + ':ring', pen=self.marker)
        sk.circle([cx, cy], box.width / 2 + 3.0, ry=(box.ascent + box.descent) / 2 + 2.6)
        for pen, strokes in sk.strokes.items():
            self.page.add_ink(strokes, self.marker, seed=8)


def _code_to_text(line):
    """Pseudocode -> layoutkit text (operators become the symbols people write)."""
    for a, b in (('!=', '≠'), ('<=', '≤'), ('>=', '≥'), ('<-', '←')):
        line = line.replace(a, b)
    return line


def build(path, out_dir, cache_dir=None, formats=('pdf',)):
    meta, blocks = parse(path)
    comp = Composer(meta, cache_dir=cache_dir)
    pages = comp.compose(blocks)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = meta.get('id', Path(path).stem)
    written = []
    if 'pdf' in formats:
        f = out_dir / f'{stem}.pdf'
        f.write_bytes(to_pdf(pages, title=meta.get('title', stem)))
        written.append(f)
    if 'svg' in formats:
        for i, p in enumerate(pages, 1):
            f = out_dir / f'{stem}-p{i}.svg'
            f.write_text(to_svg(p))
            written.append(f)
    return meta, pages, written
