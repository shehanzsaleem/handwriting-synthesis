"""``Hand``: the engine's public API.

One hand = one writer. It routes every word to the right engine:

* alphabetic prose words -> the neural network (realistic joined-up writing);
* anything with digits, maths symbols or letters the network lacks (Q, X, Z,
  Greek...) -> the single-stroke glyph pen, slanted and jittered to match.

Everything is seeded: the same profile, text and ``key`` give the same ink.
"""
from __future__ import annotations

import hashlib
import string
from dataclasses import dataclass, field, replace

import numpy as np

from .glyphs import GlyphPen
from .model import SUPPORTED
from .strokes import Ink
from .writer import Writer

PROSE_PUNCT = set('.,;:!?\'"()-')
NEURAL_LETTERS = set(string.ascii_letters) & SUPPORTED


@dataclass(frozen=True)
class HandProfile:
    name: str = 'student'
    style: int = 9              # neural priming style (0-12)
    bias: float = 1.0           # neatness: higher = neater, less varied
    x_height: float = 2.3       # mm
    glyph_font: str = 'EMSAllure'
    glyph_upper: str = 'EMSReadability'
    glyph_scale: float = 1.0    # glyph-pen x-height relative to ``x_height``
    neural_scale: float = 1.25  # network ink is measured to its loop tops; this matches it to the glyphs
    slant: float = 6.0          # degrees, for glyph-pen characters
    jitter: float = 1.0         # glyph-pen variation (0 = font-perfect)
    word_space: float = 1.15    # gap between words, in x-heights
    baseline_wander: float = 0.06  # word-to-word baseline drift, in x-heights
    candidates: int = 6         # best-of-K for neural words
    variants: int = 3           # distinct renderings of a repeated word
    seed: int = 0

    def with_(self, **kw):
        return replace(self, **kw)


PROFILES = {
    'student': HandProfile(),
    'student-neat': HandProfile(name='student-neat', style=5, bias=1.2, slant=4.0),
    'student-quick': HandProfile(name='student-quick', style=7, bias=0.75, slant=8.0, jitter=1.25),
    'teacher': HandProfile(name='teacher', style=11, bias=1.1, slant=10.0, x_height=2.2),
    'ipad': HandProfile(name='ipad', style=3, bias=1.15, slant=3.0, x_height=2.5),
}


def _h(*parts) -> int:
    return int.from_bytes(hashlib.sha256('|'.join(map(str, parts)).encode()).digest()[:8], 'little')


def is_neural_word(token: str) -> bool:
    core = token.strip(''.join(PROSE_PUNCT))
    return (len(core) >= 1 and all(c in NEURAL_LETTERS for c in core)
            and all(c in SUPPORTED for c in token)
            and not (len(core) == 1 and core not in ('a', 'A', 'I')))


@dataclass
class Hand:
    profile: HandProfile = field(default_factory=HandProfile)
    cache_dir: str | None = None
    verify: bool = True

    def __post_init__(self):
        p = self.profile
        self._writer = Writer(style=p.style, bias=p.bias, x_height=p.x_height * p.neural_scale,
                              candidates=p.candidates,
                              verify=self.verify, cache_dir=self.cache_dir, seed=p.seed)
        self._pen = GlyphPen(font=p.glyph_font, slant_deg=p.slant, jitter=p.jitter, upper=p.glyph_upper)
        self._seen: dict[str, int] = {}

    # ------------------------------------------------------------------
    def glyphs(self, text: str, key='', scale=1.0) -> Ink:
        """Write ``text`` with the glyph pen (maths, digits, symbols)."""
        p = self.profile
        rng = np.random.default_rng(_h(p.seed, p.name, text, key))
        return self._pen.write(text, p.x_height * p.glyph_scale * scale, rng)

    def words(self, tokens: list[str], keys=None) -> list[Ink]:
        """Write prose tokens (one Ink per token), batching all neural words in one pass."""
        keys = keys or [''] * len(tokens)
        plan = []
        for tok, key in zip(tokens, keys):
            if is_neural_word(tok):
                n = self._seen.get(tok, 0)
                self._seen[tok] = n + 1
                variant = n % max(self.profile.variants, 1)
                plan.append(('n', tok, variant))
            else:
                plan.append(('g', tok, key))
        neural = list(dict.fromkeys((q[1], q[2]) for q in plan if q[0] == 'n'))
        inks = dict(zip(neural, self._writer.write_many([t for t, _ in neural], [v for _, v in neural])))
        out = []
        for q in plan:
            if q[0] == 'n':
                out.append(inks[(q[1], q[2])])
            else:
                out.append(self.glyphs(q[1], key=q[2]))
        return out

    def slant_hint(self) -> float:
        return self.profile.slant
