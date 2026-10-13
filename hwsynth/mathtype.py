"""Handwritten maths typesetting for a LaTeX subset.

Supported: ``\\frac \\dfrac \\tfrac``, ``^ _``, ``\\sqrt[n]{}``, ``\\left( \\right)`` (also
``[ ] \\{ \\} |``, stretched by hand), ``\\int \\sum \\prod \\lim`` with limits,
``\\begin{pmatrix|bmatrix|vmatrix}``, ``\\text{}``, ``\\boxed{}``, ``\\vec \\hat \\bar
\\overline \\dot``, ``\\underline``, ``\\cancel``, Greek letters, common relations and
arrows, ``\\quad \\qquad \\, \\;`` spacing, and ``\\ce{}`` for chemical formulae.

Layout is TeX-like but written: each run of symbols goes through the hand's
glyph pen and every rule (fraction bar, radical, bracket) is drawn as a slightly
wobbly pen stroke. Coordinates are mm, baseline y = 0, y down.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import numpy as np

from .hand import _h
from .strokes import Ink

GREEK = {
    'alpha': 'α', 'beta': 'β', 'gamma': 'γ', 'delta': 'δ', 'epsilon': 'ε', 'varepsilon': 'ε',
    'eta': 'η', 'theta': 'θ', 'lambda': 'λ', 'mu': 'μ', 'pi': 'π', 'rho': 'ρ', 'sigma': 'σ',
    'tau': 'τ', 'phi': 'φ', 'varphi': 'φ', 'chi': 'χ', 'omega': 'ω', 'Delta': 'Δ', 'Sigma': 'Σ',
    'Omega': 'Ω', 'nabla': '∇', 'partial': '∂', 'infty': '∞',
}
SYMBOLS = {
    'times': '×', 'div': '÷', 'pm': '±', 'mp': '∓', 'cdot': '·', 'le': '≤', 'leq': '≤', 'ge': '≥',
    'geq': '≥', 'ne': '≠', 'neq': '≠', 'approx': '≈', 'equiv': '≡', 'to': '→', 'rightarrow': '→',
    'leftarrow': '←', 'gets': '←', 'leftrightarrow': '↔', 'Rightarrow': '⇒', 'implies': '⇒',
    'Leftrightarrow': '⇔', 'iff': '⇔', 'rightleftharpoons': '⇌', 'therefore': '∴', 'because': '∵',
    'in': '∈', 'perp': '⊥', 'angle': '∠', 'circ': '°', 'degree': '°', 'prime': '′', 'uparrow': '↑',
    'downarrow': '↓', 'checkmark': '✓', 'lt': '<', 'gt': '>', 'ldots': '...', 'dots': '...',
    'cdots': '···', '%': '%', '#': '#', '&': '&', '$': '$', '_': '_',
}
FUNCS = {'sin', 'cos', 'tan', 'sec', 'cosec', 'csc', 'cot', 'ln', 'log', 'exp', 'lim', 'max', 'min',
         'arcsin', 'arccos', 'arctan', 'sinh', 'cosh', 'tanh', 'det', 'arg', 'Re', 'Im'}
BIN = set('+−×÷±∓·*')
REL = set('=≠≈≤≥<>→←↔⇒⇔⇌≡∈∴∵')
PUNCT = set(',;:')
OPEN, CLOSE = set('([{'), set(')]}')


# --------------------------------------------------------------------- parsing
def tokenize(s):
    toks, i = [], 0
    while i < len(s):
        c = s[i]
        if c == '\\':
            m = re.match(r'\\([A-Za-z]+|.)', s[i:])
            toks.append('\\' + m.group(1))
            i += len(m.group(0))
            if m.group(1).isalpha():
                while i < len(s) and s[i] == ' ':
                    i += 1
        elif c.isspace():
            i += 1
        else:
            toks.append(c)
            i += 1
    return toks


@dataclass
class Node:
    kind: str
    value: str = ''
    kids: list = field(default_factory=list)
    sup: 'Node | None' = None
    sub: 'Node | None' = None


class Parser:
    def __init__(self, src):
        self.raw = src
        self.t = tokenize(src)
        self.i = 0

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else None

    def take(self):
        tok = self.peek()
        self.i += 1
        return tok

    def group(self):
        """A braced group or a single token as a list of nodes."""
        if self.peek() == '{':
            self.take()
            out = self.seq(stop={'}'})
            self.take()
            return out
        return [self.atom()] if self.peek() is not None else []

    def raw_group(self):
        """Raw text inside braces (for \\text and \\ce)."""
        # find in the raw source: rebuild from tokens is lossy for spaces
        depth, out = 0, []
        assert self.take() == '{'
        while True:
            tok = self.take()
            if tok is None:
                break
            if tok == '{':
                depth += 1
            elif tok == '}':
                if depth == 0:
                    break
                depth -= 1
            out.append(tok)
        return out

    def seq(self, stop=frozenset(), single=False):
        nodes = []
        while True:
            tok = self.peek()
            if tok is None or tok in stop:
                break
            if tok in ('^', '_'):
                self.take()
                arg = Node('row', kids=self.group())
                base = nodes.pop() if nodes else Node('sym', '')
                if base.kind == 'bigop' or base.kind == 'func' and base.value == 'lim':
                    pass
                if tok == '^':
                    base.sup = arg
                else:
                    base.sub = arg
                nodes.append(base)
                if single:
                    break
                continue
            nodes.append(self.atom())
            if single and self.peek() not in ('^', '_'):
                break
        return nodes

    def atom(self):
        tok = self.take()
        if tok == '{':
            kids = self.seq(stop={'}'})
            self.take()
            return Node('row', kids=kids)
        if tok.startswith('\\') and len(tok) > 1:
            name = tok[1:]
            if name in ('frac', 'dfrac', 'tfrac'):
                return Node('frac', name, [Node('row', kids=self.group()), Node('row', kids=self.group())])
            if name == 'sqrt':
                index = None
                if self.peek() == '[':
                    self.take()
                    index = Node('row', kids=self.seq(stop={']'}))
                    self.take()
                n = Node('sqrt', kids=[Node('row', kids=self.group())])
                n.sup = index
                return n
            if name == 'left':
                d = self.take()
                d = {'\\{': '{', '\\|': '|', '\\langle': '<'}.get(d, d)
                kids = self.seq(stop={'\\right'})
                self.take()
                r = self.take()
                r = {'\\}': '}', '\\|': '|', '\\rangle': '>'}.get(r, r)
                return Node('delim', d + r, kids)
            if name in ('text', 'mathrm', 'textrm', 'mbox', 'textbf'):
                words = ' '.join(''.join(self.raw_group()).split())
                return Node('text', self._text_source())
            if name == 'ce':
                self.raw_group()
                sub = Parser(ce_to_tex(self._text_source()))
                return Node('row', kids=sub.parse())
            if name in ('boxed', 'underline', 'overline', 'bar', 'vec', 'hat', 'dot', 'ddot', 'cancel',
                        'tilde', 'mathbf', 'bm', 'mathbb', 'operatorname'):
                g = self.group()
                if name in ('mathbf', 'bm', 'mathbb'):
                    return Node('row', kids=g)
                if name == 'operatorname':
                    return Node('func', ''.join(k.value for k in g))
                return Node('accent', name, [Node('row', kids=g)])
            if name == 'begin':
                env = ''.join(self.raw_group())
                rows, row, cell = [], [], []
                while True:
                    tok = self.peek()
                    if tok is None:
                        break
                    if tok == '\\end':
                        self.take()
                        self.raw_group()
                        break
                    if tok == '&':
                        self.take()
                        row.append(Node('row', kids=cell))
                        cell = []
                        continue
                    if tok == '\\\\':
                        self.take()
                        row.append(Node('row', kids=cell))
                        rows.append(row)
                        row, cell = [], []
                        continue
                    cell.extend(self.seq(stop={'&', '\\\\', '\\end'}))
                row.append(Node('row', kids=cell))
                rows.append(row)
                return Node('matrix', env, [Node('row', kids=r) for r in rows])
            if name in ('int', 'iint', 'oint', 'sum', 'prod'):
                return Node('bigop', {'int': '∫', 'iint': '∫∫', 'oint': '∫', 'sum': 'Σ', 'prod': 'Π'}[name])
            if name in FUNCS:
                return Node('func', name)
            if name in GREEK:
                return Node('sym', GREEK[name])
            if name in SYMBOLS:
                return Node('sym', SYMBOLS[name])
            if name in ('quad', 'qquad', ',', ';', ':', '!', ' ', 'enspace'):
                return Node('space', {'quad': 2.2, 'qquad': 4.4, ',': 0.35, ';': 0.6, ':': 0.5,
                                      '!': -0.3, ' ': 0.5, 'enspace': 1.1}[name])
            if name == '\\':
                return Node('newline')
            if name in ('{', '}'):
                return Node('sym', name)
            return Node('sym', name)
        return Node('sym', {'-': '−', '*': '×', "'": '′'}.get(tok, tok))

    def _text_source(self):
        """Recover the exact text of the last braced group from the raw string (keeps spaces)."""
        # tokens lose spaces; find the group by counting braces in the raw source
        return self._last_text.pop(0) if getattr(self, '_last_text', None) else ''

    def parse(self):
        # pre-extract \text{...} and \ce{...} bodies so spaces survive
        self._last_text = []
        for m in re.finditer(r'\\(text|mathrm|textrm|mbox|textbf|ce)\s*\{', self.raw):
            depth, j = 1, m.end()
            while j < len(self.raw) and depth:
                depth += {'{': 1, '}': -1}.get(self.raw[j], 0)
                j += 1
            self._last_text.append(self.raw[m.end():j - 1])
        return self.seq()


def ce_to_tex(s):
    """``\\ce{CH3COO- + H+ -> CH3COOH}`` -> TeX with subscripts, charges and arrows."""
    s = s.replace('<=>', ' \\rightleftharpoons ').replace('->', ' \\rightarrow ').replace('<-', ' \\leftarrow ')
    out = []
    for part in s.split(' '):
        if not part:
            continue
        if part.startswith('\\') or part in ('+', '='):
            out.append(part)
            continue
        if re.fullmatch(r'\((aq|s|l|g)\)', part):
            out.append('\\text{' + part + '}')
            continue
        coef = re.match(r'^(\d+(?:\.\d+)?|\d+/\d+)(?=[A-Z(\[])', part)
        lead = ''
        if coef:
            lead, part = coef.group(1), part[coef.end():]
        state = ''
        sm = re.search(r'\((aq|s|l|g)\)$', part)
        if sm:
            state, part = sm.group(0), part[:sm.start()]
        charge = ''
        cm = re.search(r'(\^?)(\d*[+-])$', part)
        if cm and (cm.group(1) or len(part) > len(cm.group(0))):
            charge, part = cm.group(2), part[:cm.start()]
        body = re.sub(r'(?<=[A-Za-z)\]])(\d+)', r'_{\1}', part)
        tex = lead + body
        if charge:
            tex += '^{' + charge.replace('-', '−') + '}'
        if state:
            tex += '\\,_{\\text{' + state + '}}'
        out.append(tex)
    return ' '.join(out)


# ---------------------------------------------------------------------- boxes
@dataclass
class Box:
    width: float
    ascent: float
    descent: float
    strokes: list = field(default_factory=list)   # positioned in box coords
    kind: str = 'ord'                             # ord | bin | rel | open | close | punct | op

    def shifted(self, dx, dy):
        return [s + np.array([dx, dy]) for s in self.strokes]


def _wobbly(points, rng, amp):
    """Hand-drawn version of a straight polyline: resample, bow slightly, add tremor."""
    pts = np.asarray(points, float)
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    L = np.r_[0, np.cumsum(seg)]
    if L[-1] <= 0:
        return pts
    n = max(int(L[-1] / 0.25), 4)
    u = np.linspace(0, L[-1], n)
    q = np.c_[np.interp(u, L, pts[:, 0]), np.interp(u, L, pts[:, 1])]
    d = pts[-1] - pts[0]
    nrm = np.array([-d[1], d[0]]) / (np.linalg.norm(d) + 1e-9)
    t = u / L[-1]
    bow = rng.normal(0, amp) * np.sin(np.pi * t)
    tremor = sum(rng.normal(0, amp * 0.25) * np.sin(2 * np.pi * (k * t + rng.random())) for k in (2, 3, 5))
    q += np.outer(bow + tremor, nrm)
    return q


class MathSetter:
    def __init__(self, hand, key='m'):
        self.hand = hand
        self.xh = hand.profile.x_height * hand.profile.glyph_scale
        self.key = key
        self._n = 0

    def rng(self):
        self._n += 1
        return np.random.default_rng(_h(self.key, self._n, self.hand.profile.seed))

    def _glyph_box(self, text, scale, kind='ord'):
        self._n += 1
        ink = self.hand.glyphs(text, key=f'{self.key}:{self._n}', scale=scale)
        return Box(ink.width, max(ink.ascent, 0.3 * self.xh * scale), ink.descent, list(ink.strokes), kind)

    def _ink_box(self, ink: Ink, kind='ord'):
        return Box(ink.width, ink.ascent, ink.descent, list(ink.strokes), kind)

    # -- public ------------------------------------------------------------
    def layout(self, src: str, scale=1.0, display=True) -> Box:
        nodes = Parser(src).parse()
        return self.row(nodes, scale, display)

    def layout_lines(self, src: str, scale=1.0):
        """Split on top-level ``\\\\``; each line may contain one ``&`` alignment point."""
        lines, depth, cur = [], 0, ''
        i = 0
        while i < len(src):
            if src.startswith('\\begin', i):
                depth += 1
            if src.startswith('\\end', i):
                depth -= 1
            if depth == 0 and src.startswith('\\\\', i):
                lines.append(cur)
                cur = ''
                i += 2
                continue
            cur += src[i]
            i += 1
        lines.append(cur)
        out = []
        for ln in lines:
            if '&' in ln and '\\begin' not in ln:
                left, right = ln.split('&', 1)
                out.append((self.layout(left, scale), self.layout(right, scale)))
            else:
                out.append((None, self.layout(ln, scale)))
        return out

    # -- layout of node sequences ----------------------------------------------
    def row(self, nodes, scale, display=True):
        boxes = []
        run = ''

        def flush():
            nonlocal run
            if run:
                boxes.append(self._glyph_box(run, scale))
                run = ''

        for i, n in enumerate(nodes):
            plain = n.kind == 'sym' and n.sup is None and n.sub is None and n.value not in BIN | REL | PUNCT | OPEN | CLOSE
            if plain and len(n.value) == 1 and (n.value.isalnum() or n.value in '.′' or n.value in GREEK.values()):
                run += n.value
                continue
            flush()
            boxes.append(self.node(n, scale, display, prev=boxes[-1] if boxes else None))
        flush()
        return self.hpack(boxes, scale)

    def hpack(self, boxes, scale):
        xh = self.xh * scale
        x, strokes, asc, desc = 0.0, [], 0.0, 0.0
        prev = None
        for b in boxes:
            gap = 0.12 * xh
            if (prev is not None and prev.kind == 'open') or b.kind == 'close':
                gap = -0.12 * xh      # handwritten brackets hug their contents
            elif b.kind == 'open' and prev is not None and prev.kind == 'ord':
                gap = 0.05 * xh
            if b.kind == 'rel' or (prev is not None and prev.kind == 'rel'):
                gap = 0.75 * xh
            elif b.kind == 'bin' and prev is not None and prev.kind not in ('open', 'rel', 'bin', 'punct'):
                gap = 0.55 * xh
            elif prev is not None and prev.kind == 'bin' and prev._binary:
                gap = 0.55 * xh
            elif prev is not None and prev.kind == 'punct':
                gap = 0.55 * xh
            elif b.kind == 'op' or (prev is not None and prev.kind == 'op'):
                gap = 0.4 * xh
            if prev is None:
                gap = 0.0
            if b.kind == 'bin':
                b._binary = prev is not None and prev.kind not in ('open', 'rel', 'bin', 'punct', 'op')
                if not b._binary and prev is not None and prev.kind not in ('rel', 'punct'):
                    gap = 0.12 * xh
            x += gap
            strokes += b.shifted(x, 0)
            x += b.width
            asc, desc = max(asc, b.ascent), max(desc, b.descent)
            prev = b
        return Box(x, asc, desc, strokes)

    def node(self, n, scale, display, prev=None):
        xh = self.xh * scale
        k = n.kind
        if k == 'sym':
            v = n.value
            kind = 'bin' if v in BIN else 'rel' if v in REL else 'punct' if v in PUNCT else \
                'open' if v in OPEN else 'close' if v in CLOSE else 'ord'
            base = self._glyph_box(v, scale, kind)
            if kind == 'bin':
                base._binary = True
        elif k == 'func':
            base = self._glyph_box(n.value, scale, 'op')
        elif k == 'row':
            base = self.row(n.kids, scale, display)
        elif k == 'space':
            base = Box(n.value * xh, 0, 0)
        elif k == 'text':
            toks = n.value.split()
            inks = self.hand.words(toks, keys=[f'{self.key}:t{self._n}:{j}' for j in range(len(toks))])
            self._n += 1
            gap = self.hand.profile.word_space * self.hand.profile.x_height
            bx = []
            for j, ink in enumerate(inks):
                bx.append(self._ink_box(ink))
            x, strokes, asc, desc = 0.0, [], 0.0, 0.0
            for j, b in enumerate(bx):
                strokes += [s * scale for s in b.shifted(x / scale, 0)] if scale != 1 else b.shifted(x, 0)
                x += b.width * scale + gap * scale
                asc, desc = max(asc, b.ascent * scale), max(desc, b.descent * scale)
            base = Box(max(x - gap * scale, 0), asc, desc, strokes)
        elif k == 'frac':
            base = self.frac(n, scale, display)
        elif k == 'sqrt':
            base = self.sqrt(n, scale, display)
        elif k == 'delim':
            base = self.delim(n, scale, display)
        elif k == 'accent':
            base = self.accent(n, scale, display)
        elif k == 'matrix':
            base = self.matrix(n, scale, display)
        elif k == 'bigop':
            base = self.bigop(n, scale, display)
            return base
        elif k == 'newline':
            base = Box(0, 0, 0)
        else:
            base = Box(0, 0, 0)
        if n.sup is not None or n.sub is not None:
            base = self.scripts(base, n.sup, n.sub, scale, display)
        return base

    def scripts(self, base, sup, sub, scale, display):
        xh = self.xh * scale
        s2 = scale * 0.66
        strokes = list(base.strokes)
        w = base.width
        asc, desc = base.ascent, base.descent
        x = w + 0.08 * xh
        wid = 0
        if sup is not None:
            b = self.row(sup.kids, s2, False)
            shift = max(0.95 * xh, base.ascent - 0.45 * xh) + b.descent
            strokes += b.shifted(x, -shift)
            asc = max(asc, shift + b.ascent)
            wid = max(wid, b.width)
        if sub is not None:
            b = self.row(sub.kids, s2, False)
            shift = max(0.35 * xh, base.descent + 0.1 * xh) + 0.0
            strokes += b.shifted(x, shift)
            desc = max(desc, shift + b.descent)
            wid = max(wid, b.width)
        out = Box(x + wid, asc, desc, strokes, base.kind)
        if hasattr(base, '_binary'):
            out._binary = base._binary
        return out

    def frac(self, n, scale, display):
        xh = self.xh * scale
        s2 = scale * (0.92 if display and n.value != 'tfrac' else 0.85)
        num = self.row(n.kids[0].kids, s2, False)
        den = self.row(n.kids[1].kids, s2, False)
        axis = 0.62 * xh
        pad = 0.25 * xh
        w = max(num.width, den.width) + 2 * pad
        gap = 0.32 * xh
        strokes = []
        strokes += num.shifted((w - num.width) / 2, -axis - gap - num.descent)
        strokes += den.shifted((w - den.width) / 2, -axis + gap + den.ascent)
        rng = self.rng()
        y = -axis + rng.normal(0, 0.03 * xh)
        strokes.append(_wobbly([[0.02 * xh, y], [w - 0.02 * xh, y + rng.normal(0, 0.05 * xh)]], rng, 0.04 * xh))
        return Box(w, axis + gap + num.descent + num.ascent, -axis + gap + den.ascent + den.descent, strokes)

    def sqrt(self, n, scale, display):
        xh = self.xh * scale
        body = self.row(n.kids[0].kids, scale, display)
        top = body.ascent + 0.3 * xh
        bot = body.descent + 0.1 * xh
        x0 = 0.0
        hook = 0.45 * xh
        rng = self.rng()
        start = 0.15 * xh
        if n.sup is not None:
            idx = self.row(n.sup.kids, scale * 0.55, False)
            start = idx.width * 0.7
        pts = [[start, -0.45 * xh], [start + 0.18 * xh, -0.55 * xh], [start + hook, bot],
               [start + hook + 0.35 * xh, -top], [start + hook + 0.55 * xh + body.width + 0.2 * xh, -top - 0.05 * xh]]
        strokes = [_wobbly(pts[:3], rng, 0.02 * xh), _wobbly(pts[2:4], rng, 0.03 * xh), _wobbly(pts[3:], rng, 0.04 * xh)]
        strokes += body.shifted(start + hook + 0.5 * xh, 0)
        if n.sup is not None:
            strokes += idx.shifted(0, -0.75 * xh)
        return Box(start + hook + 0.55 * xh + body.width + 0.3 * xh, top + 0.1 * xh, bot, strokes)

    def _stretch_delim(self, ch, asc, desc, xh, rng, left=True):
        h = asc + desc
        if h < 1.9 * xh and ch in '()[]|':
            b = self._glyph_box(ch, 1.0 * (self.xh and (xh / self.xh)), 'open' if left else 'close')
            return b
        w = 0.45 * xh + 0.07 * h
        top, bot = -asc, desc
        if ch in '()':
            t = np.linspace(0, 1, 28)
            bow = np.sin(np.pi * t) ** 0.8
            x = (w * 0.9 - w * 0.7 * bow) if ch == '(' else (w * 0.1 + w * 0.7 * bow)
            y = top + t * h
            x = x + rng.normal(0, 0.02 * xh) * np.sin(2 * np.pi * t)
            s = [np.c_[x, y]]
        elif ch in '[]':
            xa, xb = (w * 0.3, w * 0.85) if ch == '[' else (w * 0.7, w * 0.15)
            s = [np.array([[xb, top], [xa, top + 0.02 * xh], [xa, bot], [xb, bot - 0.02 * xh]])]
        elif ch == '|':
            s = [_wobbly([[w / 2, top], [w / 2, bot]], rng, 0.03 * xh)]
        elif ch in '{}':
            m = (top + bot) / 2
            sg = 1 if ch == '{' else -1
            cx = w * 0.5
            s = [np.array([[cx + sg * w * 0.35, top], [cx, top + 0.15 * h], [cx, m - 0.08 * h],
                           [cx - sg * w * 0.35, m], [cx, m + 0.08 * h], [cx, bot - 0.15 * h], [cx + sg * w * 0.35, bot]])]
            s = [self._smooth(s[0])]
        else:
            return Box(0, 0, 0)
        return Box(w, asc, desc, s, 'open' if left else 'close')

    @staticmethod
    def _smooth(p, n=40):
        p = np.asarray(p, float)
        t = np.linspace(0, len(p) - 1, n)
        from scipy.interpolate import CubicSpline
        cs = CubicSpline(np.arange(len(p)), p, bc_type='natural')
        return cs(t)

    def delim(self, n, scale, display):
        xh = self.xh * scale
        body = self.row(n.kids, scale, display)
        asc = max(body.ascent + 0.15 * xh, 1.05 * xh)
        desc = max(body.descent + 0.15 * xh, 0.3 * xh)
        rng = self.rng()
        L = self._stretch_delim(n.value[0], asc, desc, xh, rng, True) if n.value[0] != '.' else Box(0, 0, 0)
        R = self._stretch_delim(n.value[1], asc, desc, xh, rng, False) if n.value[1:2] not in ('.', '') else Box(0, 0, 0)
        g = 0.15 * xh
        strokes = list(L.strokes) + body.shifted(L.width + g, 0) + R.shifted(L.width + 2 * g + body.width, 0)
        return Box(L.width + 2 * g + body.width + R.width, max(asc, L.ascent), max(desc, L.descent), strokes)

    def accent(self, n, scale, display):
        xh = self.xh * scale
        body = self.row(n.kids[0].kids, scale, display)
        rng = self.rng()
        s = list(body.strokes)
        w, asc, desc = body.width, body.ascent, body.descent
        name = n.value
        y = -asc - 0.25 * xh
        if name in ('overline', 'bar'):
            s.append(_wobbly([[0, y], [w, y]], rng, 0.03 * xh))
            asc += 0.35 * xh
        elif name == 'vec':
            s.append(_wobbly([[0.05 * w, y], [w, y]], rng, 0.02 * xh))
            s.append(np.array([[w - 0.3 * xh, y - 0.18 * xh], [w, y], [w - 0.3 * xh, y + 0.18 * xh]]))
            asc += 0.45 * xh
        elif name == 'hat':
            s.append(np.array([[w * 0.2, y + 0.1 * xh], [w * 0.5, y - 0.2 * xh], [w * 0.8, y + 0.1 * xh]]))
            asc += 0.45 * xh
        elif name == 'tilde':
            t = np.linspace(0, 1, 16)
            s.append(np.c_[w * (0.15 + 0.7 * t), y - 0.1 * xh * np.sin(2 * np.pi * t)])
            asc += 0.4 * xh
        elif name in ('dot', 'ddot'):
            xs = [w / 2] if name == 'dot' else [w * 0.35, w * 0.65]
            for x in xs:
                s.append(np.array([[x, y]]))
            asc += 0.3 * xh
        elif name == 'underline':
            yy = desc + 0.25 * xh
            s.append(_wobbly([[-0.1 * xh, yy], [w + 0.1 * xh, yy]], rng, 0.04 * xh))
            desc += 0.35 * xh
        elif name == 'cancel':
            s.append(_wobbly([[0, desc], [w, -asc]], rng, 0.03 * xh))
        elif name == 'boxed':
            p = 0.35 * xh
            pts = np.array([[-p, -asc - p], [w + p, -asc - p], [w + p, desc + p], [-p, desc + p], [-p * 0.6, -asc - p * 1.2]])
            s = [list_shift for list_shift in body.shifted(p, 0)]
            pts[:, 0] += p
            s.append(_wobbly(pts[:2], rng, 0.05 * xh))
            s.append(_wobbly(pts[1:3], rng, 0.05 * xh))
            s.append(_wobbly(pts[2:4], rng, 0.05 * xh))
            s.append(_wobbly(pts[3:5], rng, 0.05 * xh))
            return Box(w + 2.4 * p, asc + p * 1.3, desc + p * 1.3, s)
        return Box(w, asc, desc, s, body.kind)

    def matrix(self, n, scale, display):
        xh = self.xh * scale
        rows = [[self.row(c.kids, scale * 0.95, False) for c in r.kids] for r in n.kids]
        ncol = max(len(r) for r in rows)
        colw = [max((r[j].width for r in rows if j < len(r)), default=0) for j in range(ncol)]
        rowh = [max(c.ascent for c in r) + max(c.descent for c in r) for r in rows]
        gapx, gapy = 1.2 * xh, 0.6 * xh
        H = sum(rowh) + gapy * (len(rows) - 1)
        axis = 0.62 * xh
        top = -axis - H / 2
        strokes, y = [], top
        for r, h in zip(rows, rowh):
            a = max(c.ascent for c in r)
            x = 0.0
            for j, c in enumerate(r):
                strokes += c.shifted(x + (colw[j] - c.width) / 2, y + a)
                x += colw[j] + gapx
            y += h + gapy
        W = sum(colw) + gapx * (ncol - 1)
        inner = Box(W, -top, top + H, strokes)
        d = {'pmatrix': '()', 'bmatrix': '[]', 'vmatrix': '||', 'matrix': '..', 'cases': '{.'}.get(n.value, '()')
        rng = self.rng()
        asc, desc = inner.ascent + 0.2 * xh, inner.descent + 0.2 * xh
        L = self._stretch_delim(d[0], asc, desc, xh, rng, True) if d[0] != '.' else Box(0, 0, 0)
        R = self._stretch_delim(d[1], asc, desc, xh, rng, False) if d[1] != '.' else Box(0, 0, 0)
        g = 0.25 * xh
        s = list(L.strokes) + inner.shifted(L.width + g, 0) + R.shifted(L.width + 2 * g + W, 0)
        return Box(L.width + 2 * g + W + R.width, asc, desc, s)

    def bigop(self, n, scale, display):
        xh = self.xh * scale
        big = (2.0 if n.value.startswith('∫') else 1.7) if display else 1.3
        sym = self._glyph_box(n.value, scale * big, 'op')
        # centre the operator on the maths axis
        axis = 0.62 * xh
        mid = (sym.ascent - sym.descent) / 2
        dy = mid - axis
        strokes = [s + [0, dy] for s in sym.strokes]
        asc, desc = sym.ascent - dy, sym.descent + dy
        w = sym.width
        lim_scale = scale * 0.62
        extra = []
        if n.value.startswith('∫'):
            # limits to the right, as people write them
            x = w + 0.05 * xh
            ww = 0
            if n.sup is not None:
                b = self.row(n.sup.kids, lim_scale, False)
                extra += b.shifted(x + 0.25 * xh, -asc + b.ascent + 0.05 * xh)
                ww = max(ww, b.width + 0.25 * xh)
            if n.sub is not None:
                b = self.row(n.sub.kids, lim_scale, False)
                extra += b.shifted(x - 0.1 * xh, desc + b.ascent * 0.35)
                desc += b.ascent * 0.35 + b.descent
                ww = max(ww, b.width - 0.1 * xh)
            return Box(x + ww + 0.1 * xh, asc, desc, strokes + extra, 'op')
        if n.sup is not None:
            b = self.row(n.sup.kids, lim_scale, False)
            extra += b.shifted((w - b.width) / 2, -asc - 0.15 * xh - b.descent)
            asc += b.ascent + b.descent + 0.2 * xh
            w = max(w, b.width)
        if n.sub is not None:
            b = self.row(n.sub.kids, lim_scale, False)
            extra += b.shifted((sym.width - b.width) / 2, desc + 0.15 * xh + b.ascent)
            desc += b.ascent + b.descent + 0.2 * xh
            w = max(w, b.width)
        return Box(w, asc, desc, strokes + extra, 'op')
