"""Pen models: turn stroke centrelines into filled ink outlines.

A real pen line is not a constant-width vector stroke. Ballpoints thin out on
fast strokes and blob slightly at slow turns; a stylus tapers at both ends with
pressure. Each pen here maps a centreline to a closed outline polygon (mm).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Pen:
    name: str = 'ballpoint'
    width: float = 0.42          # nominal line width, mm
    color: str = '#1b2a4a'       # ink colour
    opacity: float = 0.96
    speed_thinning: float = 0.35 # 0 = constant width; 1 = strong thinning on fast strokes
    taper: float = 0.35          # fraction of width lost at stroke ends
    taper_len: float = 0.9       # mm over which the taper recovers


PENS = {
    'ballpoint': Pen(),
    'ballpoint-black': Pen(name='ballpoint-black', color='#1d1d22', width=0.40),
    'gel': Pen(name='gel', width=0.5, color='#14204a', speed_thinning=0.15, taper=0.2, opacity=0.98),
    'teacher-red': Pen(name='teacher-red', width=0.45, color='#c8202f', speed_thinning=0.25, taper=0.3, opacity=0.95),
    'pencil-ipad': Pen(name='pencil-ipad', width=0.55, color='#1f2430', speed_thinning=0.1, taper=0.75,
                       taper_len=1.6, opacity=1.0),
    'ipad-blue': Pen(name='ipad-blue', width=0.55, color='#2350c8', speed_thinning=0.1, taper=0.75,
                     taper_len=1.6, opacity=1.0),
    'ipad-red': Pen(name='ipad-red', width=0.55, color='#d0312d', speed_thinning=0.1, taper=0.75,
                    taper_len=1.6, opacity=1.0),
}


def _resample(p, step=0.12):
    seg = np.linalg.norm(np.diff(p, axis=0), axis=1)
    L = np.r_[0, np.cumsum(seg)]
    if L[-1] < 1e-6:
        return p[:1], L[:1]
    n = max(int(L[-1] / step) + 1, 2)
    u = np.linspace(0, L[-1], n)
    return np.c_[np.interp(u, L, p[:, 0]), np.interp(u, L, p[:, 1])], u


def outline(stroke: np.ndarray, pen: Pen, rng: np.random.Generator | None = None):
    """Closed polygon (k, 2) for one stroke, or a small disc for a dot."""
    p = np.asarray(stroke, dtype=float)
    if len(p) == 1 or np.ptp(p, axis=0).max() < 0.15:
        c = p.mean(axis=0)
        r = pen.width * 0.62
        t = np.linspace(0, 2 * np.pi, 14, endpoint=False)
        return np.c_[c[0] + r * np.cos(t), c[1] + r * np.sin(t)]
    # speed proxy from the ORIGINAL sampling density: sparse points = fast hand
    seg0 = np.linalg.norm(np.diff(p, axis=0), axis=1)
    L0 = np.r_[0, np.cumsum(seg0)]
    speed0 = np.r_[seg0[:1], seg0]
    q, u = _resample(p)
    speed = np.interp(u, L0, speed0)
    if np.median(speed) > 0:
        speed = speed / (np.median(speed) + 1e-9)
    k = max(3, len(q) // 12)
    speed = np.convolve(np.pad(speed, k, mode='edge'), np.ones(2 * k + 1) / (2 * k + 1), mode='same')[k:-k]
    w = pen.width * (1.0 - pen.speed_thinning * np.clip(speed - 1.0, -0.6, 1.2) * 0.5)
    L = u[-1]
    ramp_in = np.clip(u / pen.taper_len, 0, 1)
    ramp_out = np.clip((L - u) / pen.taper_len, 0, 1)
    w *= 1.0 - pen.taper * (1.0 - np.minimum(ramp_in, ramp_out) ** 0.6)
    if rng is not None:
        w *= 1.0 + 0.05 * np.sin(u * rng.uniform(1.5, 3.0) + rng.uniform(0, 6.3))
    w = np.maximum(w, pen.width * 0.25)
    t = np.gradient(q, axis=0)
    t /= np.linalg.norm(t, axis=1, keepdims=True) + 1e-12
    nrm = np.c_[-t[:, 1], t[:, 0]]
    left = q + nrm * (w[:, None] / 2)
    right = q - nrm * (w[:, None] / 2)
    # round caps
    def cap(c, d, r, n=6):
        a0 = np.arctan2(d[1], d[0])
        ang = a0 + np.linspace(-np.pi / 2, np.pi / 2, n)
        return np.c_[c[0] + r * np.cos(ang), c[1] + r * np.sin(ang)]
    end = cap(q[-1], t[-1], w[-1] / 2)[::-1]
    start = cap(q[0], -t[0], w[0] / 2)[::-1]
    return np.vstack([left, end, right[::-1], start])
