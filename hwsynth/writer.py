"""Write words with the network: seeded best-of-K sampling, an OCR legibility gate and a disk cache.

The network occasionally writes the wrong letter. For every word we draw K
candidates from one seeded generator, read each back with OCR (if
``rapidocr_onnxruntime`` is installed) and keep the one that reads closest to the
intended text. The choice is cached on disk, so a rebuild is instant and
byte-identical.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .model import Network, Sample, SUPPORTED
from .strokes import Ink, to_ink

ENGINE_VERSION = 'hwsynth-3'
_LOOKALIKE = str.maketrans({'0': 'o', 'O': 'o', '1': 'l', 'I': 'l', '|': 'l', 'i': 'l', '!': 'l',
                            '5': 's', 'S': 's', 'Z': 'z', '×': 'x', 'X': 'x', 'C': 'c', 'V': 'v',
                            'W': 'w', 'U': 'u', 'K': 'k', 'P': 'p', 'Y': 'y', "'": '', '"': '',
                            ' ': '', '.': '', ',': ''})


def _canon(s):
    return s.translate(_LOOKALIKE).lower()


def _lev(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


class _Reader:
    """Optional OCR used only to rank candidates."""

    def __init__(self):
        try:
            from rapidocr_onnxruntime import RapidOCR
            self.ocr = RapidOCR()
        except Exception:  # pragma: no cover - OCR is optional
            self.ocr = None

    def read(self, ink: Ink) -> str:
        if self.ocr is None:
            return ''
        import cv2
        px = 12.0  # pixels per mm
        pad = 12
        h = int((ink.ascent + ink.descent) * px) + 2 * pad
        w = int(ink.width * px) + 2 * pad
        img = np.full((max(h, 32), max(w, 32), 3), 255, np.uint8)
        for s in ink.strokes:
            p = ((s + [0.0, ink.ascent]) * px + pad).astype(np.int32)
            if len(p) == 1:
                cv2.circle(img, tuple(p[0]), 1, (0, 0, 0), -1, cv2.LINE_AA)
            else:
                cv2.polylines(img, [p], False, (0, 0, 0), 3, cv2.LINE_AA)
        res, _ = self.ocr(img)
        if not res:
            return ''
        res = sorted(res, key=lambda r: r[0][0][0])   # [box, text, score], left to right
        return ''.join(r[1] for r in res)


SHORT = set('acemnorsuvwxz')
TALL = set('bdfhklt') | set('ABCDEFGHIJKLMNOPRSTUVWY0123456789')
DROP = set('gjpqy')
WIDE = set('mwMW')
ROUND = set('aoexdgqpbcs')


def shape_penalty(ink: Ink, text: str, xh: float) -> float:
    """Count letters whose drawn size does not fit their class (capital-sized 's', squashed 'x')."""
    bad = 0.0
    for ch, hs, vs in zip(text, ink.char_spans, ink.char_vspans):
        if ch == ' ' or ch not in SHORT | TALL | DROP:
            continue
        if hs is None or vs is None:
            bad += 1.0                    # the letter was never really written
            continue
        w = (hs[1] - hs[0]) / xh
        top, bot = -vs[0] / xh, vs[1] / xh
        if ch in SHORT and top > 1.45:
            bad += 1.0
        if ch in TALL and top < 1.2:
            bad += 0.7
        if ch in DROP and bot < 0.35:
            bad += 0.7
        if ch in WIDE and w < 0.7:
            bad += 0.7
        if ch in ROUND | {'x'} and w < 0.32:
            bad += 0.7
    return bad


@dataclass
class Choice:
    sample: Sample
    read: str
    distance: float


class Writer:
    def __init__(self, style=9, bias=0.9, x_height=2.4, candidates=6, verify=True,
                 cache_dir=None, seed=0):
        self.style, self.bias, self.x_height = style, float(bias), float(x_height)
        self.candidates, self.seed = int(candidates), int(seed)
        self.verify = verify
        self.cache = Path(cache_dir or os.environ.get('HWSYNTH_CACHE', Path.home() / '.cache' / 'hwsynth'))
        self.cache.mkdir(parents=True, exist_ok=True)
        self._net = None
        self._reader = None
        self._unit = None

    # -- cache -------------------------------------------------------------
    def _key(self, text, variant=0):
        raw = json.dumps([ENGINE_VERSION, text, variant, self.style, self.bias, self.seed, self.candidates,
                          bool(self.verify)])
        return hashlib.sha256(raw.encode()).hexdigest()[:24]

    def _load(self, text, variant=0):
        f = self.cache / (self._key(text, variant) + '.npz')
        if f.exists():
            z = np.load(f)
            return Choice(Sample(z['offsets'], z['char_index'], text), str(z['read']), float(z['distance']))
        return None

    def _store(self, text, variant, c: Choice):
        f = self.cache / (self._key(text, variant) + '.npz')
        tmp = f.with_suffix('.tmp.npz')
        np.savez(tmp, offsets=c.sample.offsets, char_index=c.sample.char_index,
                 read=np.array(c.read), distance=np.array(c.distance))
        os.replace(tmp, f)

    # -- calibration ---------------------------------------------------------
    CALIBRATION = ['the quick brown fox jumps over a lazy dog', 'we measure the size of this writing once',
                   'some more ordinary words in a row']

    def unit_scale(self):
        """mm per network unit for this style, from a few long calibration lines (cached)."""
        if self._unit is not None:
            return self._unit
        f = self.cache / f'calib-{ENGINE_VERSION}-{self.style}-{self.bias}.json'
        if f.exists():
            xh_units = json.loads(f.read_text())['x_height_units']
        else:
            if self._net is None:
                self._net = Network()
            samples = self._net.sample(self.CALIBRATION, style=self.style, bias=self.bias,
                                       seeds=[11, 12, 13])
            # with x_height_mm = 1 the returned ink is measured in network x-heights
            xs = []
            for smp in samples:
                ink = to_ink(smp, 1.0)
                raw = to_ink(smp, 1.0, unit_scale=1.0)
                xs.append(raw.width / max(ink.width, 1e-9))
            xh_units = float(np.median(xs))
            f.write_text(json.dumps({'x_height_units': xh_units}))
        self._unit = self.x_height / xh_units
        return self._unit

    # -- sampling ----------------------------------------------------------
    def _seed_for(self, text, variant=0):
        h = hashlib.sha256(f'{self.seed}|{self.style}|{self.bias}|{text}|{variant}'.encode()).digest()
        return int.from_bytes(h[:8], 'little')

    def _choose(self, text, samples):
        """Rank candidates: OCR distance + letter-shape penalty; earliest wins ties."""
        best = None
        have_ocr = bool(self.verify and self._reader and self._reader.ocr)
        letters = sum(c.isalpha() for c in text)
        for i, s in enumerate(samples):
            if len(s.offsets) < 3:
                continue
            ink = to_ink(s, self.x_height, unit_scale=self.unit_scale())
            per_char = ink.width / max(len(text.strip()), 1)
            sane = 0.25 * self.x_height < per_char < 3.2 * self.x_height and ink.ascent < 4.5 * self.x_height
            read = self._reader.read(ink) if have_ocr and letters >= 3 else ''
            dist = (_lev(_canon(read), _canon(text)) / max(len(_canon(text)), 1)) if read or (have_ocr and letters >= 3) else 0.0
            shape = shape_penalty(ink, text, self.x_height)
            score = dist + 0.25 * shape + (0 if sane else 10) + i * 1e-4
            if best is None or score < best[0]:
                best = (score, Choice(s, read, dist))
            if dist == 0 and shape == 0 and sane and (have_ocr or letters < 3):
                break
        return best

    def write_many(self, texts, variants=None):
        """Return one ``Ink`` per text (every char must be in the network alphabet).

        ``variants`` (one int per text) selects distinct, individually cached
        renderings of the same word, so a repeated word is not a carbon copy.
        """
        variants = list(variants) if variants is not None else [0] * len(texts)
        jobs = list(zip(texts, variants))
        out = {}
        todo = []
        for t, v in dict.fromkeys(jobs):
            bad = set(t) - SUPPORTED
            if bad:
                raise ValueError(f'unsupported characters {sorted(bad)} in {t!r}')
            c = self._load(t, v)
            if c is None:
                todo.append((t, v))
            else:
                out[(t, v)] = c
        if todo:
            if self._net is None:
                self._net = Network()
            if self.verify and self._reader is None:
                self._reader = _Reader()
            # batch words of similar length together; K candidates per word, one seed per row
            todo.sort(key=lambda q: len(q[0]))
            K = self.candidates
            per_batch = max(1, 60 // K)
            for b in range(0, len(todo), per_batch):
                group = todo[b:b + per_batch]
                rows = [t for t, _ in group for _ in range(K)]
                seeds = [self._seed_for(t, v) + k for t, v in group for k in range(K)]
                samples = self._net.sample(rows, style=self.style, bias=self.bias, seeds=seeds)
                retry = []
                for j, (t, v) in enumerate(group):
                    score, c = self._choose(t, samples[j * K:(j + 1) * K])
                    if score > 0.12:
                        retry.append((t, v, score, c))
                    else:
                        self._store(t, v, c)
                        out[(t, v)] = c
                if retry:
                    # escalate: a second, larger round at a neater bias for words nobody wrote cleanly
                    K2 = 2 * K
                    rows = [t for t, _, _, _ in retry for _ in range(K2)]
                    seeds = [self._seed_for(t, v) + 1000 + k for t, v, _, _ in retry for k in range(K2)]
                    more = self._net.sample(rows, style=self.style, bias=self.bias + 0.5, seeds=seeds)
                    for j, (t, v, score, c) in enumerate(retry):
                        score2, c2 = self._choose(t, more[j * K2:(j + 1) * K2])
                        pick = c2 if score2 + 0.02 < score else c
                        self._store(t, v, pick)
                        out[(t, v)] = pick
        u = self.unit_scale()
        return [to_ink(out[j].sample, self.x_height, unit_scale=u) for j in jobs]

    def report(self, texts, variant=0):
        return [(t, self._load(t, variant).read if self._load(t, variant) else None) for t in texts]
