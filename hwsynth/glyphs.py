"""Procedural pen glyphs for characters the network cannot write well.

The network's alphabet has no ``+ = / * < > [ ]``, no Q/X/Z, no Greek and no
maths symbols, and it writes isolated digits and one-letter variables poorly.
For those we draw single-stroke (centreline) glyphs and give every instance
seeded, smooth human variation, so ``3x`` looks written rather than typeset.

ASCII and a few Latin-1 symbols come from the OFL single-stroke EMS fonts
(``data/fonts``). Everything else is defined below in the same font units:
baseline y = 0, y up, x-height ~ 300, cap/digit height ~ 500, em 1000.
"""
from __future__ import annotations

import html
import re
from functools import lru_cache
from pathlib import Path

import numpy as np

from .strokes import Ink

FONTS = Path(__file__).parent / 'data' / 'fonts'
XH = 300.0   # font units


def _flatten(d):
    """SVG path data (M/L/C only, absolute) -> list of polylines."""
    toks = re.findall(r'[MLC]|-?\d*\.?\d+(?:e-?\d+)?', d)
    out, cur, i, pos = [], None, 0, (0.0, 0.0)
    while i < len(toks):
        t = toks[i]
        if t == 'M':
            pos = (float(toks[i + 1]), float(toks[i + 2]))
            cur = [pos]
            out.append(cur)
            i += 3
        elif t == 'L':
            i += 1
            while i + 1 < len(toks) and toks[i] not in 'MLC':
                pos = (float(toks[i]), float(toks[i + 1]))
                cur.append(pos)
                i += 2
        elif t == 'C':
            i += 1
            while i + 5 < len(toks) + 0 and toks[i] not in 'MLC':
                p0 = np.array(pos)
                p1, p2, p3 = (np.array([float(toks[i + k]), float(toks[i + k + 1])]) for k in (0, 2, 4))
                for u in np.linspace(0, 1, 9)[1:]:
                    q = (1 - u) ** 3 * p0 + 3 * (1 - u) ** 2 * u * p1 + 3 * (1 - u) * u * u * p2 + u ** 3 * p3
                    cur.append((float(q[0]), float(q[1])))
                pos = tuple(p3)
                i += 6
        else:
            i += 1
    return [np.array(p) for p in out if len(p) >= 1]


@lru_cache(maxsize=8)
def load_font(name='EMSFelix'):
    s = (FONTS / f'{name}.svg').read_text()
    default_adv = float(re.search(r'<font [^>]*horiz-adv-x="([\d.]+)"', s).group(1))
    glyphs = {}
    for m in re.finditer(r'<glyph([^>]*)/>', s):
        attrs = m.group(1)
        u = re.search(r'unicode="([^"]*)"', attrs)
        if not u:
            continue
        ch = html.unescape(u.group(1))
        if len(ch) != 1:
            continue
        adv = re.search(r'horiz-adv-x="([\d.]+)"', attrs)
        d = re.search(r' d="([^"]*)"', attrs)
        glyphs[ch] = (float(adv.group(1)) if adv else default_adv, _flatten(d.group(1)) if d else [])
    return glyphs


def _arc(cx, cy, rx, ry, a0, a1, n=24):
    t = np.radians(np.linspace(a0, a1, n))
    return np.c_[cx + rx * np.cos(t), cy + ry * np.sin(t)]


def _P(*pts):
    return np.array(pts, dtype=float)


def _custom():
    """Hand-authored glyphs: name -> (advance, [polylines]) in font units."""
    g = {}
    # Greek (lowercase sits on the baseline, x-height 300)
    g['α'] = (330, [np.vstack([_arc(130, 150, 110, 150, 10, 350, 30)[::-1][:0],
                              _P((300, 290), (250, 120), (190, 20), (120, 0), (50, 40), (30, 150),
                                 (70, 260), (140, 300), (200, 270), (250, 120), (290, 0))])])
    g['β'] = (320, [_P((60, -200), (60, 420), (90, 520), (160, 560), (230, 530), (250, 450), (210, 380),
                       (140, 350), (220, 330), (270, 260), (270, 140), (230, 50), (160, 10), (90, 30), (60, 80))])
    g['γ'] = (300, [_P((20, 290), (80, 290), (160, 60), (170, -80), (140, -200), (110, -110), (180, 60), (270, 290))])
    g['δ'] = (300, [_P((240, 520), (130, 560), (80, 510), (100, 440), (230, 330), (270, 200), (240, 60),
                       (160, 0), (80, 30), (40, 130), (70, 250), (150, 320))])
    g['θ'] = (300, [_arc(150, 250, 115, 250, 90, 450, 36), _P((40, 250), (260, 250))])
    g['λ'] = (310, [_P((50, 540), (110, 520), (170, 380), (290, 0)), _P((160, 330), (20, 0))])
    g['μ'] = (330, [_P((60, 290), (60, -200)),
                    _P((60, 120), (90, 30), (150, 0), (220, 30), (260, 120), (260, 290), (260, 60), (280, 0), (310, 10))])
    g['π'] = (360, [_P((20, 250), (80, 290), (330, 285)), _P((120, 285), (110, 140), (90, 0)),
                    _P((250, 285), (250, 90), (270, 10), (320, 10))])
    g['ρ'] = (300, [_P((60, -200), (60, 150), (90, 250), (160, 295), (230, 260), (260, 160), (230, 50),
                       (160, 0), (90, 30), (60, 80))])
    g['σ'] = (330, [_P((320, 290), (150, 290), (70, 250), (40, 150), (70, 50), (140, 0), (210, 30),
                       (250, 120), (230, 230), (150, 290))])
    g['τ'] = (300, [_P((20, 250), (80, 290), (290, 285)), _P((160, 285), (150, 80), (180, 10), (240, 20))])
    g['φ'] = (340, [_P((170, 420), (170, -200)), _arc(170, 145, 130, 145, 0, 360, 32)])
    g['χ'] = (300, [_P((20, 280), (70, 290), (230, -170), (280, -180)), _P((270, 290), (30, -190))])
    g['ω'] = (380, [_P((70, 290), (30, 150), (60, 30), (120, 0), (170, 50), (190, 150), (210, 50),
                       (260, 0), (320, 30), (350, 150), (310, 290))])
    g['ε'] = (270, [_P((240, 270), (170, 300), (90, 280), (70, 220), (100, 165), (170, 155), (90, 140),
                       (40, 80), (70, 20), (150, 0), (240, 30))])
    g['η'] = (320, [_P((40, 260), (70, 290), (90, 200), (90, 0), (90, 180), (150, 280), (220, 290),
                       (260, 220), (260, -200))])
    g['Δ'] = (460, [_P((230, 500), (30, 0), (430, 0), (230, 500))])
    g['Σ'] = (430, [_P((390, 480), (380, 500), (40, 500), (230, 250), (40, 0), (390, 0), (400, 30))])
    g['Ω'] = (470, [np.vstack([_P((40, 0), (170, 0), (170, 40)), _arc(235, 280, 170, 220, 245, -65, 40)[::1],
                               _P((300, 40), (300, 0), (430, 0))])])
    # operators and relations
    g['≤'] = (420, [_P((360, 420), (60, 280), (360, 140)), _P((60, 70), (360, 70))])
    g['≥'] = (420, [_P((60, 420), (360, 280), (60, 140)), _P((60, 70), (360, 70))])
    g['≠'] = (440, [_P((60, 310), (380, 310)), _P((60, 170), (380, 170)), _P((290, 420), (150, 60))])
    g['≈'] = (440, [_P((60, 300), (130, 345), (220, 300), (310, 255), (380, 300)),
                    _P((60, 170), (130, 215), (220, 170), (310, 125), (380, 170))])
    g['≡'] = (440, [_P((60, 340), (380, 340)), _P((60, 240), (380, 240)), _P((60, 140), (380, 140))])
    g['→'] = (560, [_P((40, 240), (510, 240)), _P((420, 320), (515, 240), (420, 160))])
    g['←'] = (560, [_P((520, 240), (50, 240)), _P((140, 320), (45, 240), (140, 160))])
    g['↔'] = (600, [_P((50, 240), (550, 240)), _P((140, 320), (45, 240), (140, 160)), _P((460, 320), (555, 240), (460, 160))])
    g['⇒'] = (560, [_P((40, 290), (470, 290)), _P((40, 190), (470, 190)), _P((400, 380), (520, 240), (400, 100))])
    g['⇔'] = (620, [_P((120, 290), (500, 290)), _P((120, 190), (500, 190)),
                    _P((180, 380), (50, 240), (180, 100)), _P((440, 380), (570, 240), (440, 100))])
    g['⇌'] = (620, [_P((50, 300), (560, 300), (470, 370)), _P((570, 180), (60, 180), (150, 110))])
    g['↑'] = (300, [_P((150, 0), (150, 520)), _P((70, 430), (150, 525), (230, 430))])
    g['↓'] = (300, [_P((150, 520), (150, 0)), _P((70, 90), (150, -5), (230, 90))])
    g['∞'] = (520, [_P((260, 240), (200, 320), (120, 340), (60, 290), (50, 220), (90, 160), (160, 150),
                       (260, 240), (360, 330), (440, 330), (480, 260), (460, 170), (380, 140), (320, 160), (260, 240))])
    g['√'] = (380, [_P((20, 230), (70, 260), (150, -10), (330, 620))])
    g['∫'] = (300, [_P((270, 640), (230, 690), (180, 680), (150, 600), (150, 0), (130, -150), (80, -200), (30, -160))])
    g['∑'] = g['Σ']
    g['∴'] = (360, [_P((180, 300), (182, 304)), _P((60, 60), (62, 64)), _P((300, 60), (302, 64))])
    g['∵'] = (360, [_P((60, 300), (62, 304)), _P((300, 300), (302, 304)), _P((180, 60), (182, 64))])
    g['∈'] = (380, [_P((330, 420), (200, 420), (100, 370), (60, 240), (100, 110), (200, 60), (330, 60)), _P((70, 240), (300, 240))])
    g['∂'] = (330, [_P((80, 480), (160, 540), (240, 520), (280, 420), (280, 200), (240, 60), (160, 0), (80, 20),
                       (40, 110), (70, 210), (150, 260), (230, 240), (280, 200))])
    g['∇'] = (460, [_P((230, 0), (30, 500), (430, 500), (230, 0))])
    g['·'] = (160, [_P((80, 230), (82, 234))])
    g['′'] = (140, [_P((100, 560), (50, 400))])
    g['−'] = (420, [_P((60, 240), (360, 240))])
    g['∓'] = (420, [_P((60, 420), (360, 420)), _P((210, 360), (210, 80)), _P((60, 230), (360, 230))])
    g['⊥'] = (420, [_P((210, 500), (210, 0)), _P((40, 0), (380, 0))])
    g['∠'] = (440, [_P((400, 460), (40, 0), (420, 0))])
    g['°'] = (220, [_arc(110, 560, 55, 55, 0, 360, 20)])
    g['×'] = (360, [_P((80, 330), (280, 110)), _P((280, 330), (80, 110))])
    g['÷'] = (400, [_P((60, 230), (340, 230)), _P((200, 340), (202, 344)), _P((200, 110), (202, 114))])
    g['+'] = (400, [_P((60, 225), (340, 225)), _P((200, 370), (200, 80))])
    g['✓'] = (420, [_P((30, 230), (140, 60), (170, 20), (400, 500))])
    g['✗'] = (380, [_P((40, 400), (340, 30)), _P((340, 400), (40, 30))])
    return g


PRINT_LETTERS = 'abcdefghijklmnopqrstuvwzABCDEFGHIJKLMNOPQRSTUVWXYZ'


@lru_cache(maxsize=8)
def _normalised(name):
    """A font rescaled so its measured x-height is ``XH`` units.

    The EMS fonts declare x-height 300 but draw it at 356 (Allure) or 485
    (Readability); mixing them unscaled made print letters 1.6x too tall.
    Digits are pulled in a little (``DIGIT_SCALE``: handwritten digits are
    about 1.5 x-heights, not a typeface's 1.8) and capitals are set to
    ``CAP_HEIGHT``.
    """
    g = load_font(name)
    tops = [np.vstack(g[c][1])[:, 1].max() for c in 'acemnorsuvwxz' if c in g and g[c][1]]
    k = XH / float(np.median(tops))
    caps = [np.vstack(g[c][1])[:, 1].max() for c in 'EFHIKLMNTZ' if c in g and g[c][1]]
    kc = CAP_HEIGHT * XH / float(np.median(caps))
    out = {}
    for ch, (adv, polys) in g.items():
        kk = k * DIGIT_SCALE if ch.isdigit() else kc if ch.isupper() else k
        out[ch] = (adv * kk, [p * kk for p in polys])
    return out


DIGIT_SCALE = 0.88
CAP_HEIGHT = 1.45   # capitals, in x-heights


@lru_cache(maxsize=16)
def glyph_table(font='EMSAllure', upper='EMSReadability', print_letters=PRINT_LETTERS):
    """Base font for digits/symbols; ``print_letters`` come from the ``upper`` (print) font.

    Joined-up script letters are hard to read as maths variables (r, s, z) and in
    formulae (CH3COOH), so by default only x and y keep the script forms people
    actually write in maths.
    """
    table = dict(_normalised(font))
    if upper and upper != font:
        up = _normalised(upper)
        for ch in print_letters:
            if ch in up:
                table[ch] = up[ch]
    table.update(_custom())
    # the EMS minus sign is a hyphen; maths minus should be a little longer
    table['-'] = table['−']
    return table


def supported(ch, font='EMSAllure'):
    return ch in glyph_table(font)


def _smooth_noise(rng, n, amp, corr=6):
    """Low-frequency 1-D noise (sum of a few random sinusoids)."""
    t = np.linspace(0, 1, n)
    out = np.zeros(n)
    for k in range(1, 4):
        out += rng.normal(0, amp / k) * np.sin(2 * np.pi * (k * t * n / (corr * 8) + rng.random()))
    return out


class GlyphPen:
    """Writes strings with single-stroke glyphs plus seeded natural variation."""

    def __init__(self, font='EMSAllure', slant_deg=8.0, jitter=1.0, tracking=1.0, upper='EMSReadability',
                 print_letters=PRINT_LETTERS):
        self.font, self.slant = font, float(slant_deg)
        self.jitter, self.tracking = float(jitter), float(tracking)
        self.table = glyph_table(font, upper, print_letters)

    def write(self, text: str, x_height_mm: float, rng: np.random.Generator) -> Ink:
        s = x_height_mm / XH
        shear = np.tan(np.radians(self.slant))
        j = self.jitter
        strokes, spans, x = [], [], 0.0
        drift = 0.0
        for ch in text:
            if ch == ' ':
                x += 0.9 * XH * s * self.tracking
                spans.append(None)
                continue
            adv, polys = self.table.get(ch, self.table['?'])
            sc = 1.0 + rng.normal(0, 0.035 * j)
            rot = np.radians(rng.normal(0, 1.6 * j))
            drift = 0.6 * drift + rng.normal(0, 0.025 * j) * XH
            dx = rng.normal(0, 0.02 * j) * XH
            c, si = np.cos(rot), np.sin(rot)
            x0 = x
            for p in polys:
                q = p.astype(float).copy()
                if len(q) >= 3:
                    # dense resample so the wobble is smooth along the stroke
                    seg = np.linalg.norm(np.diff(q, axis=0), axis=1)
                    L = np.r_[0, np.cumsum(seg)]
                    if L[-1] > 0:
                        m = max(int(L[-1] / 12), len(q))
                        u = np.linspace(0, L[-1], m)
                        q = np.c_[np.interp(u, L, q[:, 0]), np.interp(u, L, q[:, 1])]
                        q[:, 0] += _smooth_noise(rng, m, 5.0 * j)
                        q[:, 1] += _smooth_noise(rng, m, 5.0 * j)
                elif len(q) == 2 and np.linalg.norm(q[1] - q[0]) > 20:
                    # straight strokes get a faint bow, as a hand never draws a ruler line
                    m = 12
                    u = np.linspace(0, 1, m)[:, None]
                    q = q[0] + u * (q[1] - q[0])
                    nrm = np.array([-(q[-1, 1] - q[0, 1]), q[-1, 0] - q[0, 0]])
                    nrm /= np.linalg.norm(nrm) + 1e-9
                    q += np.outer(np.sin(np.pi * u[:, 0]), nrm) * rng.normal(0, 6.0 * j)
                q = q * sc
                q = q @ np.array([[c, si], [-si, c]])
                q[:, 0] += q[:, 1] * shear
                q[:, 0] += x + dx
                q[:, 1] += drift
                strokes.append(np.c_[q[:, 0] * s, -q[:, 1] * s])
            gx = [p[:, 0].min() for p in strokes[-len(polys):]] if polys else [x * s]
            gx1 = [p[:, 0].max() for p in strokes[-len(polys):]] if polys else [x * s]
            spans.append((float(min(gx)), float(max(gx1))))
            x = x0 + adv * self.tracking * (1.0 + rng.normal(0, 0.03 * j))
        if not strokes:
            return Ink([], x * s, 0.0, 0.0, spans, text)
        pts = np.vstack(strokes)
        x_min = min(0.0, float(pts[:, 0].min()))
        strokes = [p - [x_min, 0] for p in strokes]
        spans = [None if sp is None else (sp[0] - x_min, sp[1] - x_min) for sp in spans]
        return Ink(strokes, max(x * s - x_min, float(pts[:, 0].max() - x_min)), float(-pts[:, 1].min()),
                   float(max(pts[:, 1].max(), 0.0)), spans, text)
