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

ENGINE_VERSION = 'hwsynth-2'
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

    # -- sampling ----------------------------------------------------------
    def _seed_for(self, text, variant=0):
        h = hashlib.sha256(f'{self.seed}|{self.style}|{self.bias}|{text}|{variant}'.encode()).digest()
        return int.from_bytes(h[:8], 'little')

    def _choose(self, text, samples):
        best = None
        for i, s in enumerate(samples):
            if len(s.offsets) < 3:
                continue
            ink = to_ink(s, self.x_height)
            # reject runaway samples: absurd width for the character count
            per_char = ink.width / max(len(text), 1)
            sane = 0.25 * self.x_height < per_char < 3.2 * self.x_height and ink.ascent < 4.5 * self.x_height
            read = self._reader.read(ink) if (self.verify and self._reader) else ''
            dist = (_lev(_canon(read), _canon(text)) / max(len(_canon(text)), 1)) if read or self.verify else 0.0
            if not self._reader or not self._reader.ocr:
                dist = 0.0
            score = dist + (0 if sane else 10) + i * 1e-3   # earlier candidate wins ties
            if best is None or score < best[0]:
                best = (score, Choice(s, read, dist))
            if self.verify and self._reader and self._reader.ocr and dist == 0 and sane:
                break
        return best[1]

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
                for j, (t, v) in enumerate(group):
                    c = self._choose(t, samples[j * K:(j + 1) * K])
                    self._store(t, v, c)
                    out[(t, v)] = c
        return [to_ink(out[j].sample, self.x_height) for j in jobs]

    def report(self, texts, variant=0):
        return [(t, self._load(t, variant).read if self._load(t, variant) else None) for t in texts]
