"""Scenes and exporters (SVG, PDF) with no third-party dependencies.

A ``Scene`` is one page in millimetres (origin top-left, y down) holding:

* ink: stroke centrelines + a ``Pen`` (outlined at export time);
* rules: thin printed lines (ruled paper, grids, boxes);
* dots: printed dot grids;
* text: printed (typeset) text in Helvetica, for question headers.

The PDF writer emits deterministic bytes: same scene -> same file.
"""
from __future__ import annotations

import zlib
from dataclasses import dataclass, field

import numpy as np

from .ink import PENS, Pen, outline

MM = 72.0 / 25.4


@dataclass
class Scene:
    width: float = 210.0
    height: float = 297.0
    background: str = '#ffffff'
    ink: list = field(default_factory=list)     # (strokes, Pen, seed)
    rules: list = field(default_factory=list)   # (points (n,2), colour, width_mm, opacity, dash)
    rects: list = field(default_factory=list)   # (x, y, w, h, fill)
    dots: list = field(default_factory=list)    # (points (n,2), colour, radius_mm)
    text: list = field(default_factory=list)    # (x, y, size_pt, string, colour, bold)

    def add_ink(self, strokes, pen='ballpoint', seed=0):
        pen = PENS[pen] if isinstance(pen, str) else pen
        self.ink.append(([np.asarray(s, float) for s in strokes if len(s)], pen, int(seed)))

    def add_rule(self, pts, colour='#9ec1e6', width=0.2, opacity=1.0, dash=None):
        self.rules.append((np.asarray(pts, float), colour, width, opacity, dash))

    def outlines(self):
        """Yield (polygon, Pen) for every ink stroke."""
        for strokes, pen, seed in self.ink:
            rng = np.random.default_rng(seed)
            for s in strokes:
                yield outline(s, pen, rng), pen


def _hex(c):
    c = c.lstrip('#')
    return tuple(int(c[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def _f(v):
    s = '%.3f' % v
    s = s.rstrip('0').rstrip('.') if '.' in s else s
    return '0' if s in ('-0', '') else s


# ------------------------------------------------------------------------ SVG
def to_svg(scene: Scene) -> str:
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{_f(scene.width)}mm" height="{_f(scene.height)}mm" '
           f'viewBox="0 0 {_f(scene.width)} {_f(scene.height)}">',
           f'<rect width="{_f(scene.width)}" height="{_f(scene.height)}" fill="{scene.background}"/>']
    for x, y, w, h, fill in scene.rects:
        out.append(f'<rect x="{_f(x)}" y="{_f(y)}" width="{_f(w)}" height="{_f(h)}" fill="{fill}"/>')
    for pts, col, r in scene.dots:
        out.append(''.join(f'<circle cx="{_f(p[0])}" cy="{_f(p[1])}" r="{_f(r)}" fill="{col}"/>' for p in pts))
    for pts, col, w, op, dash in scene.rules:
        d = 'M' + ' L'.join(f'{_f(p[0])},{_f(p[1])}' for p in pts)
        da = f' stroke-dasharray="{" ".join(_f(v) for v in dash)}"' if dash else ''
        out.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="{_f(w)}" stroke-opacity="{_f(op)}"{da}/>')
    for x, y, size, s, col, bold in scene.text:
        esc = s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        out.append(f'<text x="{_f(x)}" y="{_f(y)}" font-family="Helvetica, Arial, sans-serif" '
                   f'font-size="{_f(size / MM)}" fill="{col}"{" font-weight=\"bold\"" if bold else ""}>{esc}</text>')
    by_pen = {}
    for poly, pen in scene.outlines():
        by_pen.setdefault(pen, []).append('M' + ' L'.join(f'{_f(p[0])},{_f(p[1])}' for p in poly) + 'Z')
    for pen, paths in by_pen.items():
        out.append(f'<path d="{"".join(paths)}" fill="{pen.color}" fill-opacity="{_f(pen.opacity)}" fill-rule="nonzero"/>')
    out.append('</svg>')
    return '\n'.join(out)


# ------------------------------------------------------------------------ PDF
def _pdf_text(s):
    b = s.encode('cp1252', errors='replace')
    return b.replace(b'\\', b'\\\\').replace(b'(', b'\\(').replace(b')', b'\\)')


def _page_stream(scene: Scene) -> bytes:
    H = scene.height
    ops = []
    P = lambda x, y: f'{_f(x * MM)} {_f((H - y) * MM)}'
    r, g, b = _hex(scene.background)
    ops.append(f'{_f(r)} {_f(g)} {_f(b)} rg 0 0 {_f(scene.width * MM)} {_f(H * MM)} re f')
    for x, y, w, h, fill in scene.rects:
        r, g, b = _hex(fill)
        ops.append(f'{_f(r)} {_f(g)} {_f(b)} rg {P(x, y + h)} {_f(w * MM)} {_f(h * MM)} re f')
    for pts, col, rad in scene.dots:
        r, g, b = _hex(col)
        ops.append(f'{_f(r)} {_f(g)} {_f(b)} rg')
        for p in pts:
            ops.append(f'{P(p[0] - rad, p[1] + rad)} {_f(2 * rad * MM)} {_f(2 * rad * MM)} re f')
    for pts, col, w, op, dash in scene.rules:
        r, g, b = _hex(col)
        gs = '/GA%d gs ' % int(round(op * 100)) if op < 1 else ''
        d = f'[{" ".join(_f(v * MM) for v in dash)}] 0 d ' if dash else '[] 0 d '
        path = ' '.join((f'{P(*p)} m' if i == 0 else f'{P(*p)} l') for i, p in enumerate(pts))
        ops.append(f'q {gs}{d}{_f(r)} {_f(g)} {_f(b)} RG {_f(w * MM)} w 1 J 1 j {path} S Q')
    for poly, pen in scene.outlines():
        r, g, b = _hex(pen.color)
        gs = '/GA%d gs ' % int(round(pen.opacity * 100)) if pen.opacity < 1 else ''
        path = ' '.join((f'{P(*p)} m' if i == 0 else f'{P(*p)} l') for i, p in enumerate(poly))
        ops.append(f'q {gs}{_f(r)} {_f(g)} {_f(b)} rg {path} h f Q')
    for x, y, size, s, col, bold in scene.text:
        r, g, b = _hex(col)
        font = '/F2' if bold else '/F1'
        ops.append(('BT %s %s Tf %s %s %s rg %s Td (' % (font, _f(size), _f(r), _f(g), _f(b), P(x, y))).encode()
                   .decode('latin-1') + _pdf_text(s).decode('latin-1') + ') Tj ET')
    return '\n'.join(ops).encode('latin-1')


def to_pdf(scenes, title='Handwritten answers') -> bytes:
    """Write one or more scenes as a multi-page PDF (deterministic bytes)."""
    if isinstance(scenes, Scene):
        scenes = [scenes]
    objs = []

    def add(body: bytes) -> int:
        objs.append(body)
        return len(objs)

    alphas = sorted({int(round(op * 100)) for s in scenes for (_, _, _, op, _) in s.rules if op < 1} |
                    {int(round(pen.opacity * 100)) for s in scenes for (_, pen, _) in s.ink if pen.opacity < 1})
    f1 = add(b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>')
    f2 = add(b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>')
    gs_ids = {a: add(f'<< /Type /ExtGState /ca {a / 100:.2f} /CA {a / 100:.2f} >>'.encode()) for a in alphas}
    gs = ' '.join(f'/GA{a} {i} 0 R' for a, i in gs_ids.items())
    res = add(f'<< /Font << /F1 {f1} 0 R /F2 {f2} 0 R >> /ExtGState << {gs} >> >>'.encode())
    pages_id = len(objs) + 1 + 2 * len(scenes)  # reserved after page/content pairs
    kids = []
    for s in scenes:
        data = zlib.compress(_page_stream(s), 9)
        c = add(b'<< /Length %d /Filter /FlateDecode >>\nstream\n' % len(data) + data + b'\nendstream')
        p = add(f'<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 {_f(s.width * MM)} {_f(s.height * MM)}] '
                f'/Resources {res} 0 R /Contents {c} 0 R >>'.encode())
        kids.append(p)
    assert add(f'<< /Type /Pages /Kids [{" ".join(f"{k} 0 R" for k in kids)}] /Count {len(kids)} >>'.encode()) == pages_id
    info = add(b'<< /Title (' + _pdf_text(title) + b') /Producer (hwsynth) >>')
    cat = add(f'<< /Type /Catalog /Pages {pages_id} 0 R >>'.encode())
    out = bytearray(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n')
    offsets = []
    for i, body in enumerate(objs, 1):
        offsets.append(len(out))
        out += b'%d 0 obj\n' % i + body + b'\nendobj\n'
    xref = len(out)
    out += b'xref\n0 %d\n0000000000 65535 f \n' % (len(objs) + 1)
    for o in offsets:
        out += b'%010d 00000 n \n' % o
    out += b'trailer\n<< /Size %d /Root %d 0 R /Info %d 0 R >>\nstartxref\n%d\n%%%%EOF\n' % (len(objs) + 1, cat, info, xref)
    return bytes(out)
