"""Turn raw network samples into clean, measured ink.

``Ink`` holds strokes in millimetres with the baseline at y = 0 (y grows
downwards, like SVG/PDF-after-flip), plus per-character x extents, so layout code
can place a written word exactly like a typeset box.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.signal import savgol_filter

from .model import Sample

DESCENDERS = set('gjpqy,;')
ASCENDERS = set('bdfhklt!?"\'#()0123456789ABCDEFGHIJKLMNOPRSTUVWY')
XHEIGHT = set('acemnorsuvwxz')


@dataclass
class Ink:
    strokes: list            # list of (n, 2) float arrays, mm, baseline y = 0, y down
    width: float             # advance width (mm)
    ascent: float            # top of ink above baseline (positive mm)
    descent: float           # bottom of ink below baseline (positive mm)
    char_spans: list = field(default_factory=list)  # (x0, x1) per character, mm
    text: str = ''

    def translated(self, dx, dy):
        return [s + np.array([dx, dy]) for s in self.strokes]


def _split(offsets):
    xy = np.cumsum(offsets[:, :2], axis=0)
    xy[:, 1] *= -1.0                         # network y is up; ink y is down
    ends = np.where(offsets[:, 2] == 1)[0]
    out, start = [], 0
    for e in list(ends) + [len(xy) - 1]:
        if e + 1 - start >= 1:
            out.append((start, e + 1))
        start = e + 1
    return xy, out


def _smooth(p):
    if len(p) >= 7:
        return np.c_[savgol_filter(p[:, 0], 7, 3, mode='nearest'),
                     savgol_filter(p[:, 1], 7, 3, mode='nearest')]
    return p


def to_ink(sample: Sample, x_height_mm: float) -> Ink:
    """Clean a sample, find its baseline and x-height from the attention map, scale to mm."""
    off = sample.offsets.copy()
    off[0, :2] = 0.0
    ci = sample.char_index
    text = sample.text
    # the first point is the pen lifting off the priming line: drop it
    off, ci = off[1:], ci[1:]
    xy, spans = _split(off)
    # drop strays: single points before the first character and pen marks while 'writing' a space
    keep_spans = []
    for a, b in spans:
        idx = ci[a:b]
        real = [(0 <= k < len(text)) and text[k] != ' ' for k in idx]
        if not any(real) and all(k < 0 for k in idx):
            continue          # pen marks before the first character: priming leftovers
        if b - a <= 2 and not any(real):
            continue
        keep_spans.append((a, b))
    spans = keep_spans or spans

    # de-slant the whole line: fit a straight line through the per-character bottoms
    def char_points(cls):
        return np.array([i for i in range(len(xy)) if 0 <= ci[i] < len(text) and text[ci[i]] in cls])

    base_idx = char_points(XHEIGHT | ASCENDERS - set('()"\'#!?'))
    if len(base_idx) < 4:
        base_idx = np.arange(len(xy))
    # baseline: per character, take the lowest point (largest y), then fit a line
    bottoms = []
    for k in sorted(set(ci[base_idx])):
        pts = xy[base_idx][ci[base_idx] == k]
        if len(pts):
            j = np.argmax(pts[:, 1])
            bottoms.append(pts[j])
    bottoms = np.array(bottoms)
    if len(bottoms) >= 3:
        slope, icpt = np.polyfit(bottoms[:, 0], bottoms[:, 1], 1)
        slope = float(np.clip(slope, -0.15, 0.15))
        icpt = float(np.median(bottoms[:, 1] - slope * bottoms[:, 0]))
    elif len(bottoms):
        slope, icpt = 0.0, float(np.median(bottoms[:, 1]))
    else:
        slope, icpt = 0.0, float(xy[:, 1].max())
    xy = xy.copy()
    xy[:, 1] -= slope * xy[:, 0] + icpt      # baseline -> y = 0

    xh_idx = char_points(XHEIGHT)
    if len(xh_idx) >= 4:
        tops = []
        for k in sorted(set(ci[xh_idx])):
            pts = xy[xh_idx][ci[xh_idx] == k]
            tops.append(-pts[:, 1].min())
        xh = float(np.median(tops))
    else:
        # digits / capitals only: they are ~1.45 x-heights tall
        tall = char_points(ASCENDERS)
        xh = float(-xy[tall, 1].min() / 1.45) if len(tall) else float(-xy[:, 1].min())
    xh = max(xh, 1e-3)
    scale = x_height_mm / xh
    xy *= scale
    x0 = min(xy[a:b, 0].min() for a, b in spans)
    xy[:, 0] -= x0

    # strokes made after the attention left the word are kept only if they come back over
    # the word (t-bars, i-dots); anything trailing off to the right is the network rambling on
    real_pts = [xy[a:b][(ci[a:b] >= 0) & (ci[a:b] < len(text))] for a, b in spans]
    real_pts = [p for p in real_pts if len(p)]
    if real_pts:
        right = np.vstack(real_pts)[:, 0].max()
        kept = []
        for a, b in spans:
            after = np.all(ci[a:b] >= len(text))
            if after and xy[a:b, 0].min() > right - 0.2 * x_height_mm:
                continue
            kept.append((a, b))
        spans = kept or spans
    strokes = []
    for a, b in spans:
        p = _smooth(xy[a:b])
        if len(p) >= 2 or (len(p) == 1):
            strokes.append(p)
    pts = np.vstack(strokes)
    char_spans = []
    for k in range(len(text)):
        m = ci == k
        if m.any() and text[k] != ' ':
            char_spans.append((float(xy[m, 0].min()), float(xy[m, 0].max())))
        else:
            char_spans.append(None)
    return Ink(strokes=strokes, width=float(pts[:, 0].max()), ascent=float(-pts[:, 1].min()),
               descent=float(max(pts[:, 1].max(), 0.0)), char_spans=char_spans, text=text)
