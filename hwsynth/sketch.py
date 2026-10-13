"""Hand-drawn diagrams: shapes, graphs, tables and labels, as pen strokes.

A ``Sketch`` collects strokes in a local box (mm, origin top-left, y down).
Every primitive is drawn the way a person draws it: lines bow slightly and
overshoot, circles do not quite close, curves are traced in a few strokes.
Coordinates may be given in data units once ``axes`` has been called.

Spec form (used by document builders) is a list of ``{kind: args}`` dicts; see
``Sketch.from_spec``.
"""
from __future__ import annotations

import math

import numpy as np

from .mathtype import MathSetter, _wobbly
from .hand import _h

SAFE = {k: getattr(np, k) for k in ('sin', 'cos', 'tan', 'exp', 'log', 'sqrt', 'abs', 'pi', 'e',
                                     'arctan', 'tanh', 'sinh', 'cosh', 'minimum', 'maximum', 'where')}
SAFE['ln'] = np.log


def _inside(pts, poly):
    """Even-odd point-in-polygon test for many points."""
    x, y = pts[:, 0], pts[:, 1]
    inside = np.zeros(len(pts), dtype=bool)
    for (x1, y1), (x2, y2) in zip(poly, np.roll(poly, -1, axis=0)):
        cond = (y1 > y) != (y2 > y)
        xi = (x2 - x1) * (y - y1) / ((y2 - y1) + 1e-12) + x1
        inside ^= cond & (x < xi)
    return inside


class Sketch:
    def __init__(self, hand, width, height, key='sk', pen=None):
        self.hand, self.w, self.h, self.key = hand, float(width), float(height), key
        self.strokes = {}        # pen name -> strokes
        self.default_pen = pen or 'ballpoint'
        self._n = 0
        self.ms = MathSetter(hand, key=key + ':m')
        self.map = None          # data -> mm transform
        self.xh = hand.profile.x_height

    # ------------------------------------------------------------------ util
    def rng(self):
        self._n += 1
        return np.random.default_rng(_h(self.key, self._n, self.hand.profile.seed))

    def P(self, p):
        p = np.asarray(p, float)
        return self.map(p) if self.map is not None else p

    def add(self, strokes, pen=None):
        self.strokes.setdefault(pen or self.default_pen, []).extend(strokes)

    # ------------------------------------------------------------ primitives
    def line(self, a, b, pen=None, overshoot=0.3, dashed=False, data=True):
        a, b = (self.P(a), self.P(b)) if data else (np.asarray(a, float), np.asarray(b, float))
        rng = self.rng()
        d = b - a
        L = np.linalg.norm(d)
        if L < 1e-6:
            return
        u = d / L
        a2 = a - u * rng.uniform(0, overshoot) * 0.5
        b2 = b + u * rng.uniform(0, overshoot)
        if dashed:
            n = max(int(L / 2.2), 1)
            segs = []
            for i in range(n):
                t0, t1 = i / n, (i + 0.55) / n
                segs.append(_wobbly([a + d * t0, a + d * t1], rng, 0.05))
            self.add(segs, pen)
        else:
            self.add([_wobbly([a2, b2], rng, min(0.35, 0.012 * L + 0.05))], pen)

    def polyline(self, pts, pen=None, closed=False):
        pts = [self.P(p) for p in pts]
        if closed:
            pts = pts + [pts[0]]
        for a, b in zip(pts[:-1], pts[1:]):
            self.line(a, b, pen=pen, overshoot=0.25, data=False)

    def path(self, pts, pen=None, smooth=True, closed=False, data=True):
        pts = np.array([self.P(p) for p in pts]) if data else np.asarray(pts, float)
        if closed:
            pts = np.vstack([pts, pts[:1]])
        if smooth and len(pts) >= 3:
            from scipy.interpolate import CubicSpline
            t = np.r_[0, np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))]
            keep = np.r_[True, np.diff(t) > 1e-9]
            pts, t = pts[keep], t[keep]
            cs = CubicSpline(t, pts, bc_type='periodic' if closed and np.allclose(pts[0], pts[-1]) else 'natural')
            tt = np.linspace(0, t[-1], max(int(t[-1] / 0.3), 8))
            pts = cs(tt)
        rng = self.rng()
        n = len(pts)
        tt = np.linspace(0, 1, n)
        wob = sum(rng.normal(0, 0.12) * np.sin(2 * np.pi * (k * tt + rng.random())) for k in (1, 2, 3))
        t = np.gradient(pts, axis=0)
        nrm = np.c_[-t[:, 1], t[:, 0]] / (np.linalg.norm(t, axis=1, keepdims=True) + 1e-9)
        pts = pts + nrm * wob[:, None]
        # long curves are drawn in a couple of strokes, as a hand would
        L = np.sum(np.linalg.norm(np.diff(pts, axis=0), axis=1))
        pieces = 1 if L < 60 else 2
        cuts = np.linspace(0, n - 1, pieces + 1).astype(int)
        out = []
        for i in range(pieces):
            a, b = cuts[i], min(cuts[i + 1] + 1, n)
            out.append(pts[a:b])
        self.add(out, pen)

    def circle(self, c, r, pen=None, ry=None, start=None, fill_dot=False):
        c = self.P(c)
        rng = self.rng()
        ry = r if ry is None else ry
        if fill_dot:
            self.add([np.array([c])], pen)
            return
        a0 = rng.uniform(0, 2 * np.pi) if start is None else start
        sweep = 2 * np.pi * rng.uniform(1.02, 1.08)
        t = np.linspace(a0, a0 + sweep, max(int(2 * np.pi * max(r, ry) / 0.35), 24))
        k = np.linspace(0, 1, len(t))
        rr = 1 + 0.03 * np.sin(2 * t + rng.uniform(0, 6)) + 0.015 * k
        self.add([np.c_[c[0] + r * rr * np.cos(t), c[1] + ry * rr * np.sin(t)]], pen)

    def arrow(self, a, b, pen=None, head=2.0, double=False, data=True):
        A, B = (self.P(a), self.P(b)) if data else (np.asarray(a, float), np.asarray(b, float))
        self.line(A, B, pen=pen, overshoot=0.0, data=False)
        self._head(A, B, head, pen)
        if double:
            self._head(B, A, head, pen)

    def _head(self, A, B, head, pen):
        rng = self.rng()
        u = (B - A) / (np.linalg.norm(B - A) + 1e-9)
        n = np.array([-u[1], u[0]])
        sp = rng.uniform(0.45, 0.55)
        p1 = B - u * head + n * head * sp
        p2 = B - u * head - n * head * sp
        self.add([np.array([p1, B + u * 0.1, p2])], pen)

    def curly(self, a, b, bend=0.35, pen=None, head=1.6, half=False, data=True):
        """Curly (mechanism) arrow from ``a`` to ``b``, bowing to the left by ``bend``."""
        A, B = (self.P(a), self.P(b)) if data else (np.asarray(a, float), np.asarray(b, float))
        d = B - A
        n = np.array([-d[1], d[0]])
        C = (A + B) / 2 + n * bend
        t = np.linspace(0, 1, 40)[:, None]
        pts = (1 - t) ** 2 * A + 2 * (1 - t) * t * C + t ** 2 * B
        self.path(pts, pen=pen, smooth=False, data=False)
        u = (pts[-1] - pts[-4]) / (np.linalg.norm(pts[-1] - pts[-4]) + 1e-9)
        nn = np.array([-u[1], u[0]])
        if half:
            self.add([np.array([B - u * head + nn * head * 0.6, B])], pen)
        else:
            self.add([np.array([B - u * head + nn * head * 0.5, B, B - u * head - nn * head * 0.5])], pen)

    def rect(self, a, b, pen=None, data=True):
        a, b = self.P(a), self.P(b)
        self.polyline([a, [b[0], a[1]], b, [a[0], b[1]]], pen=pen, closed=True) if self.map is None else \
            self._rect_mm(a, b, pen)

    def _rect_mm(self, a, b, pen):
        m, self.map = self.map, None
        self.polyline([a, [b[0], a[1]], b, [a[0], b[1]]], pen=pen, closed=True)
        self.map = m

    def hatch(self, poly, spacing=1.5, angle=45, pen=None):
        poly = np.array([self.P(p) for p in poly])
        x0, y0 = poly.min(axis=0)
        x1, y1 = poly.max(axis=0)
        th = math.radians(angle)
        d = np.array([math.cos(th), math.sin(th)])
        nrm = np.array([-d[1], d[0]])
        span = np.linalg.norm([x1 - x0, y1 - y0])
        c = np.array([(x0 + x1) / 2, (y0 + y1) / 2])
        segs = []
        for k in np.arange(-span, span, spacing):
            p0 = c + nrm * k - d * span
            ts = np.linspace(0, 2 * span, int(2 * span / 0.2))
            pts = p0 + np.outer(ts, d)
            inside = _inside(pts, poly)
            if inside.any():
                idx = np.where(inside)[0]
                runs = np.split(idx, np.where(np.diff(idx) > 1)[0] + 1)
                for r in runs:
                    if len(r) > 2:
                        segs.append((pts[r[0]], pts[r[-1]]))
        m, self.map = self.map, None
        for a, b in segs:
            self.line(a, b, pen=pen, overshoot=0.0, data=False)
        self.map = m

    # ---------------------------------------------------------------- labels
    def label(self, at, text, pen=None, anchor='left', scale=0.9, math=None, data=True):
        """Write ``text`` at a point. ``$...$`` -> maths; otherwise prose words."""
        p = self.P(at) if data else np.asarray(at, float)
        box = self.text_box(text, scale, math)
        dx = {'left': 0, 'center': -box.width / 2, 'right': -box.width}[anchor if anchor in ('left', 'center', 'right') else 'left']
        dy = 0.0
        if anchor in ('above',):
            dx, dy = -box.width / 2, -1.0
        if anchor in ('below',):
            dx, dy = -box.width / 2, box.ascent + 1.0
        if anchor == 'middle':
            dx, dy = -box.width / 2, (box.ascent - box.descent) / 2
        self.add(box.shifted(p[0] + dx, p[1] + dy), pen)
        return box

    def text_box(self, text, scale=0.9, math=None):
        from .layoutkit import text_line_box
        return text_line_box(self.hand, self.ms, text, scale=scale, key=f'{self.key}:l{self._n}')

    def leader(self, a, b, text, pen=None, anchor='left'):
        """Label line from a feature ``a`` to a label placed at ``b``."""
        self.line(a, b, pen=pen, overshoot=0.0)
        B = self.P(b)
        side = 'left' if anchor == 'left' else 'right'
        self.label(B + np.array([1.2 if side == 'left' else -1.2, 1.0]), text, pen=pen,
                   anchor=side, data=False)

    # ------------------------------------------------------------------ axes
    def axes(self, x, y, box=None, xlabel=None, ylabel=None, xticks=None, yticks=None, origin_label=True,
             pen=None, arrows=True, grid=False):
        """Set a data->mm mapping and draw the axes. ``box`` = [x0, y0, x1, y1] in mm."""
        x0, y0, x1, y1 = box or [10, 4, self.w - 4, self.h - 8]
        (dx0, dx1), (dy0, dy1) = x, y
        sx = (x1 - x0) / (dx1 - dx0)
        sy = (y1 - y0) / (dy1 - dy0)
        self.map = lambda p: np.array([x0 + (p[..., 0] - dx0) * sx, y1 - (p[..., 1] - dy0) * sy]).T \
            if np.ndim(p) > 1 else np.array([x0 + (p[0] - dx0) * sx, y1 - (p[1] - dy0) * sy])
        ox = min(max(0, dx0), dx1)
        oy = min(max(0, dy0), dy1)
        a, b = self.P([dx0, oy]), self.P([dx1, oy])
        c, d = self.P([ox, dy0]), self.P([ox, dy1])
        (self.arrow if arrows else self.line)(a, b + [2, 0], pen=pen, data=False) if arrows else self.line(a, b, pen=pen, data=False)
        (self.arrow if arrows else self.line)(c, d - [0, 2], pen=pen, data=False) if arrows else self.line(c, d, pen=pen, data=False)
        for t in (xticks or []):
            p = self.P([t, oy])
            self.line(p + [0, -0.8], p + [0, 0.8], pen=pen, overshoot=0, data=False)
            self.label(p + [0, 1.2], f'${t:g}$' if isinstance(t, (int, float)) else str(t), pen=pen,
                       anchor='below', scale=0.7, data=False)
        for t in (yticks or []):
            p = self.P([ox, t])
            self.line(p + [-0.8, 0], p + [0.8, 0], pen=pen, overshoot=0, data=False)
            lb = self.text_box(f'${t:g}$' if isinstance(t, (int, float)) else str(t), 0.7)
            self.add(lb.shifted(p[0] - 1.6 - lb.width, p[1] + lb.ascent / 2), pen)
        if xlabel:
            self.label(b + [-1, -2.2], xlabel, pen=pen, anchor='right', scale=0.8, data=False)
        if ylabel:
            self.label(d + [1.8, 1.5], ylabel, pen=pen, anchor='left', scale=0.8, data=False)
        if origin_label and dx0 <= 0 <= dx1 and dy0 <= 0 <= dy1:
            o = self.P([0, 0])
            self.label(o + [-2.6, 3.4], '$O$', pen=pen, scale=0.7, data=False)

    def plot(self, f, x, pen=None, n=120, label=None, label_at=None, clip=None):
        xs = np.linspace(x[0], x[1], n)
        ys = eval(f, {'__builtins__': {}}, dict(SAFE, x=xs)) if isinstance(f, str) else f(xs)
        ys = np.broadcast_to(ys, xs.shape).astype(float)
        if clip is not None:
            ok = (ys >= clip[0]) & (ys <= clip[1])
            xs, ys = xs[ok], ys[ok]
        self.path(np.c_[xs, ys], pen=pen, smooth=False)
        if label:
            at = label_at or [xs[-1], ys[-1]]
            self.label(self.P(at) + [1.0, -0.6], label, pen=pen, scale=0.8, data=False)

    def point(self, p, label=None, pen=None, cross=True, offset=(1.2, -1.2)):
        q = self.P(p)
        if cross:
            s = 0.9
            self.line(q + [-s, -s], q + [s, s], pen=pen, overshoot=0, data=False)
            self.line(q + [-s, s], q + [s, -s], pen=pen, overshoot=0, data=False)
        else:
            self.circle(q, 0.5, pen=pen, fill_dot=False) if False else self.add([np.array([q])], pen)
        if label:
            self.label(q + np.array(offset), label, pen=pen, scale=0.75, data=False)

    # ----------------------------------------------------------------- table
    def table(self, rows, col_widths=None, row_h=None, at=(0, 0), pen=None, header=True):
        """Hand-drawn grid with handwritten cells. ``rows`` = list of lists of strings."""
        ncol = max(len(r) for r in rows)
        boxes = [[self.text_box(c, 0.9) if c else None for c in r] for r in rows]
        if col_widths is None:
            col_widths = [max((b.width for r in boxes for b in ([r[j]] if j < len(r) and r[j] else []))
                              , default=6) + 4 for j in range(ncol)]
        row_h = row_h or max(2.6 * self.xh + 1.2, max((b.ascent + b.descent for r in boxes for b in r if b),
                                                      default=0) + 2.4)
        x0, y0 = at
        W, H = sum(col_widths), row_h * len(rows)
        m, self.map = self.map, None
        for i in range(len(rows) + 1):
            self.line([x0, y0 + i * row_h], [x0 + W, y0 + i * row_h], pen=pen, overshoot=0.6)
        x = x0
        for j in range(ncol + 1):
            self.line([x, y0], [x, y0 + H], pen=pen, overshoot=0.6)
            if j < ncol:
                x += col_widths[j]
        for i, r in enumerate(boxes):
            x = x0
            for j, b in enumerate(r):
                if b is not None:
                    by = y0 + i * row_h + row_h / 2 + (b.ascent - b.descent) / 2
                    self.add(b.shifted(x + (col_widths[j] - b.width) / 2, by), pen)
                x += col_widths[j]
        self.map = m
        return W, H

    # ------------------------------------------------------------------ spec
    @classmethod
    def from_spec(cls, hand, spec, key='sk', pen='ballpoint', pens=None):
        """Build from a dict: ``{width, height, items: [{kind: args}, ...]}``."""
        sk = cls(hand, spec.get('width', 80), spec.get('height', 50), key=key, pen=pen)
        for item in spec.get('items', []):
            (kind, args), = item.items()
            args = dict(args) if isinstance(args, dict) else {'_': args}
            if 'pen' in args and pens:
                args['pen'] = pens.get(args['pen'], args['pen'])
            if kind == 'axes':
                sk.axes(**args)
            elif kind == 'plot':
                sk.plot(**args)
            elif kind == 'line':
                pts = args.pop('_', None) or args.pop('points')
                sk.polyline(pts, pen=args.get('pen')) if len(pts) > 2 else sk.line(*pts, pen=args.get('pen'),
                                                                                    dashed=args.get('dashed', False))
            elif kind == 'dashed':
                pts = args.pop('_', None) or args.pop('points')
                for a, b in zip(pts[:-1], pts[1:]):
                    sk.line(a, b, pen=args.get('pen'), dashed=True)
            elif kind == 'polygon':
                pts = args.pop('_', None) or args.pop('points')
                sk.polyline(pts, pen=args.get('pen'), closed=True)
            elif kind == 'path':
                pts = args.pop('_', None) or args.pop('points')
                sk.path(pts, pen=args.get('pen'), smooth=args.get('smooth', True), closed=args.get('closed', False))
            elif kind == 'circle':
                sk.circle(args['at'], args['r'], pen=args.get('pen'), ry=args.get('ry'))
            elif kind == 'arrow':
                pts = args.pop('_', None) or args.pop('points')
                sk.arrow(pts[0], pts[1], pen=args.get('pen'), double=args.get('double', False),
                         head=args.get('head', 2.0))
            elif kind == 'curly':
                sk.curly(args['from'], args['to'], bend=args.get('bend', 0.35), pen=args.get('pen'),
                         half=args.get('half', False))
            elif kind == 'rect':
                pts = args.pop('_', None) or args.pop('points')
                sk.rect(pts[0], pts[1], pen=args.get('pen'))
            elif kind == 'label':
                sk.label(args['at'], args['text'], pen=args.get('pen'), anchor=args.get('anchor', 'left'),
                         scale=args.get('scale', 0.9))
            elif kind == 'leader':
                sk.leader(args['from'], args['to'], args['text'], pen=args.get('pen'),
                          anchor=args.get('anchor', 'left'))
            elif kind == 'point':
                sk.point(args['at'], label=args.get('label'), pen=args.get('pen'),
                         offset=tuple(args.get('offset', (1.2, -1.2))))
            elif kind == 'hatch':
                sk.hatch(args['points'], spacing=args.get('spacing', 1.5), angle=args.get('angle', 45),
                         pen=args.get('pen'))
            elif kind == 'table':
                sk.table(args['rows'], col_widths=args.get('col_widths'), row_h=args.get('row_h'),
                         at=tuple(args.get('at', (0, 0))), pen=args.get('pen'))
            elif kind == 'unmap':
                sk.map = None
            else:
                raise ValueError(f'unknown sketch item {kind!r}')
        return sk
