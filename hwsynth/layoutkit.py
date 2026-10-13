"""Prose + inline maths -> written line boxes, with word wrapping.

A *token* is a word (written by the network, or the glyph pen if it has digits
or symbols) or an inline ``$...$`` maths box. Words that mix letters and
symbols (``numbers[i]``, ``x-axis``, ``(a)``) are split so the letters still come
from the network and the symbols from the glyph pen.
"""
from __future__ import annotations

import re

import numpy as np

from .hand import _h, is_neural_word
from .mathtype import Box

MATH_RE = re.compile(r'(\$[^$]+\$)')


def _segments(word):
    """Split a word into neural-friendly letter runs and glyph runs."""
    if is_neural_word(word):
        return [word]
    parts = re.findall(r"[A-Za-z]{2,}[.,;:!?']*|[^A-Za-z]+|[A-Za-z]", word)
    out = []
    for p in parts:
        if out and not is_neural_word(p) and not is_neural_word(out[-1]):
            out[-1] += p
        else:
            out.append(p)
    return out


def tokens(text):
    """-> list of ('math', src) | ('word', [segments]) in reading order."""
    out = []
    emphasis = [False]          # **bold** words are underlined, as people do by hand
    for chunk in MATH_RE.split(text):
        if not chunk:
            continue
        if chunk.startswith('$') and chunk.endswith('$') and len(chunk) > 1:
            out.append(('math', chunk[1:-1], chunk))
            continue
        if out and out[-1][0] == 'math' and not chunk[:1].isspace():
            # punctuation written straight after maths ("$x = 2$,") belongs to the maths box
            head = re.match(r'[.,;:!?)]+', chunk)
            if head:
                m = out[-1]
                out[-1] = ('math', m[1] + head.group(0), m[2])
                chunk = chunk[head.end():]
        for w in chunk.split():
            emph = w.startswith('**') or emphasis[0]
            if w.startswith('**'):
                emphasis[0] = True
                w = w[2:]
            if w.endswith('**') or w.rstrip('.,;:!?').endswith('**'):
                emphasis[0] = False
                w = w.replace('**', '')
            if w:
                out.append(('word', _segments(w), w, emph))
    return out


def _gap(hand, scale):
    return hand.profile.word_space * hand.profile.x_height * scale


def build_token_boxes(hand, ms, toks, scale=1.0, key='t'):
    """Write every token; neural words for the whole batch are sampled together."""
    words, where = [], []
    for i, t in enumerate(toks):
        if t[0] == 'word':
            for j, seg in enumerate(t[1]):
                words.append(seg)
                where.append((i, j))
    inks = hand.words(words, keys=[f'{key}:{i}:{j}' for i, j in where]) if words else []
    seg_ink = {w: ink for w, ink in zip(where, inks)}
    boxes = []
    for i, t in enumerate(toks):
        if t[0] == 'math':
            b = ms.layout(t[1], scale=scale, display=False)
            boxes.append(b)
            continue
        x, strokes, asc, desc = 0.0, [], 0.0, 0.0
        for j, seg in enumerate(t[1]):
            ink = seg_ink[(i, j)]
            if j:
                x += 0.12 * hand.profile.x_height * scale
            strokes += [s * scale + [x, 0] for s in ink.strokes]
            x += ink.width * scale
            asc, desc = max(asc, ink.ascent * scale), max(desc, ink.descent * scale)
        if len(t) > 3 and t[3]:
            rng = np.random.default_rng(_h(key, i, 'ul'))
            y = desc + 0.45 * hand.profile.x_height
            strokes.append(np.array([[-0.3, y], [x * 0.5, y + rng.normal(0, 0.15)], [x + 0.4, y + rng.normal(0, 0.2)]]))
            desc = y + 0.2
        boxes.append(Box(x, asc, desc, strokes))
    return boxes


def pack_line(hand, boxes, scale=1.0, key='pl'):
    """Place boxes left to right with natural word gaps and a little baseline wander."""
    rng = np.random.default_rng(_h(key, len(boxes), hand.profile.seed))
    p = hand.profile
    x, strokes, asc, desc = 0.0, [], 0.0, 0.0
    drift = 0.0
    for k, b in enumerate(boxes):
        if k:
            x += _gap(hand, scale) * rng.uniform(0.85, 1.2)
        drift = 0.5 * drift + rng.normal(0, p.baseline_wander * p.x_height * scale)
        strokes += b.shifted(x, drift)
        x += b.width
        asc, desc = max(asc, b.ascent - drift), max(desc, b.descent + drift)
    return Box(x, asc, desc, strokes)


def text_line_box(hand, ms, text, scale=1.0, key='tl'):
    toks = tokens(text)
    return pack_line(hand, build_token_boxes(hand, ms, toks, scale, key), scale, key)


def wrap(hand, ms, text, width, scale=1.0, key='w', first_indent=0.0):
    """Wrap a paragraph into line boxes no wider than ``width`` (mm)."""
    toks = tokens(text)
    boxes = build_token_boxes(hand, ms, toks, scale, key)
    lines, cur, w = [], [], first_indent
    gap = _gap(hand, scale) * 1.05
    for b in boxes:
        need = b.width + (gap if cur else 0)
        if cur and w + need > width:
            lines.append(cur)
            cur, w = [b], b.width
        else:
            cur.append(b)
            w += need
    if cur:
        lines.append(cur)
    return [pack_line(hand, ln, scale, f'{key}:{i}') for i, ln in enumerate(lines)]
