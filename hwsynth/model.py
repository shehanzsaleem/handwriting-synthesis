"""NumPy inference for the Graves handwriting synthesis network.

A faithful port of the sampling path of ``rnn.py`` / ``rnn_cell.py``
(3 x LSTM(400), a 10-component Gaussian attention window over the characters,
a 20-component bivariate mixture density output). No TensorFlow needed: the
weights come from ``data/weights.npz`` (see ``tools/export_checkpoint.py``).

Sampling is driven by a ``numpy.random.Generator``, so the same text, style,
bias and seed always produce the same strokes.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np

DATA = Path(__file__).parent / 'data'

ALPHABET = [
    '\x00', ' ', '!', '"', '#', "'", '(', ')', ',', '-', '.',
    '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';',
    '?', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K',
    'L', 'M', 'N', 'O', 'P', 'R', 'S', 'T', 'U', 'V', 'W', 'Y',
    'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l',
    'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x',
    'y', 'z',
]
CHAR_INDEX = {c: i for i, c in enumerate(ALPHABET)}
SUPPORTED = frozenset(ALPHABET[1:])
LSTM = 400
ATTN_K = 10
MIX_K = 20


def encode(text: str) -> np.ndarray:
    return np.array([CHAR_INDEX[c] for c in text] + [0], dtype=np.int64)


def _sigmoid(x):
    return 0.5 * (1.0 + np.tanh(0.5 * x))


def _softplus(x):
    return np.logaddexp(0.0, x)


@lru_cache(maxsize=1)
def _weights():
    w = {k: v.astype(np.float32) for k, v in np.load(DATA / 'weights.npz').items()}
    p = 'rnn/LSTMAttentionCell/'
    return {
        'k1': w[p + 'lstm_cell/kernel'], 'b1': w[p + 'lstm_cell/bias'],
        'k2': w[p + 'lstm_cell_1/kernel'], 'b2': w[p + 'lstm_cell_1/bias'],
        'k3': w[p + 'lstm_cell_2/kernel'], 'b3': w[p + 'lstm_cell_2/bias'],
        'ka': w[p + 'attention/weights'], 'ba': w[p + 'attention/biases'],
        'kg': w['rnn/gmm/weights'], 'bg': w['rnn/gmm/biases'],
    }


@lru_cache(maxsize=64)
def load_style(style: int):
    strokes = np.load(DATA / 'styles' / f'style-{style}-strokes.npy')
    chars = np.load(DATA / 'styles' / f'style-{style}-chars.npy').tobytes().decode('utf-8')
    return strokes.astype(np.float64), chars


def _lstm(x, h, c, kernel, bias):
    z = np.concatenate([x, h], axis=1) @ kernel + bias
    i, j, f, o = np.split(z, 4, axis=1)
    c = _sigmoid(f + 1.0) * c + _sigmoid(i) * np.tanh(j)
    return _sigmoid(o) * np.tanh(c), c


@dataclass
class Sample:
    """One generated line: pen offsets and the character each point was writing."""
    offsets: np.ndarray      # (n, 3): dx, dy, end-of-stroke
    char_index: np.ndarray   # (n,): index into ``text`` attended to at each point (-1 = before text)
    text: str


class Network:
    """Batched free-running sampler."""

    def __init__(self):
        self.w = _weights()
        self._prime_cache = {}

    def _step(self, x, s, onehot, mask):
        w = self.w
        h1, c1 = _lstm(np.concatenate([s['w'], x], axis=1), s['h1'], s['c1'], w['k1'], w['b1'])
        a = _softplus(np.concatenate([s['w'], x, h1], axis=1) @ w['ka'] + w['ba'])
        alpha, beta, kappa = np.split(a, 3, axis=1)
        kappa = s['kappa'] + kappa / 25.0
        beta = np.maximum(beta, 0.01)
        u = np.arange(onehot.shape[1])[None, None, :]
        phi = np.sum(alpha[:, :, None] * np.exp(-np.square(kappa[:, :, None] - u) / beta[:, :, None]), axis=1)
        win = np.einsum('bu,buc->bc', phi * mask, onehot)
        h2, c2 = _lstm(np.concatenate([x, h1, win], axis=1), s['h2'], s['c2'], w['k2'], w['b2'])
        h3, c3 = _lstm(np.concatenate([x, h2, win], axis=1), s['h3'], s['c3'], w['k3'], w['b3'])
        return {'h1': h1, 'c1': c1, 'h2': h2, 'c2': c2, 'h3': h3, 'c3': c3,
                'kappa': kappa, 'w': win, 'phi': phi}

    def _emit(self, s, bias, rngs):
        z = s['h3'] @ self.w['kg'] + self.w['bg']
        pis, sig, rho, mu, es = np.split(z, np.cumsum([MIX_K, 2 * MIX_K, MIX_K, 2 * MIX_K]), axis=1)
        pis = pis * (1.0 + bias[:, None])
        sig = sig - bias[:, None]
        pis = np.exp(pis - pis.max(axis=1, keepdims=True))
        pis /= pis.sum(axis=1, keepdims=True)
        pis = np.where(pis < 0.01, 0.0, pis)
        pis /= pis.sum(axis=1, keepdims=True)
        sig = np.maximum(np.exp(sig), 1e-4)
        rho = np.clip(np.tanh(rho), 1e-8 - 1.0, 1.0 - 1e-8)
        es = np.clip(_sigmoid(es[:, 0]), 1e-8, 1.0 - 1e-8)
        es = np.where(es < 0.01, 0.0, es)
        b = len(bias)
        u = np.stack([g.random(4) for g in rngs])          # 4 uniforms per row per step
        k = np.minimum((np.cumsum(pis, axis=1) < u[:, :1]).sum(axis=1), MIX_K - 1)
        rows = np.arange(b)
        s1, s2, r = sig[rows, k], sig[rows, MIX_K + k], rho[rows, k]
        rad = np.sqrt(-2.0 * np.log(np.maximum(u[:, 1], 1e-12)))
        n1, n2 = rad * np.cos(2 * np.pi * u[:, 2]), rad * np.sin(2 * np.pi * u[:, 2])
        out = np.zeros((b, 3), dtype=np.float32)
        out[:, 0] = mu[rows, k] + s1 * n1
        out[:, 1] = mu[rows, MIX_K + k] + s2 * (r * n1 + np.sqrt(1.0 - r * r) * n2)
        out[:, 2] = (u[:, 3] < es).astype(np.float32)
        return out

    def _primed(self, style, umax):
        """State after reading the style's priming strokes (cached per style).

        The original primes with the attention window over priming text + target
        text; the window never reaches the target text while priming, so priming
        over the priming text alone gives the same state and lets us cache it.
        """
        key = style
        if key not in self._prime_cache:
            z = {k: np.zeros((1, LSTM), dtype=np.float32) for k in ('h1', 'c1', 'h2', 'c2', 'h3', 'c3')}
            z.update(kappa=np.zeros((1, ATTN_K), dtype=np.float32),
                     w=np.zeros((1, len(ALPHABET)), dtype=np.float32))
            if style is not None:
                strokes, chars = load_style(style)
                q = encode(chars + ' ')
                oh = np.zeros((1, len(q), len(ALPHABET)), dtype=np.float32)
                oh[0, np.arange(len(q)), q] = 1.0
                m = np.ones((1, len(q)), dtype=np.float32)
                for t in range(len(strokes)):
                    z = self._step(strokes[t:t + 1].astype(np.float32), z, oh, m)
                z.pop('phi')
            self._prime_cache[key] = z
        st = dict(self._prime_cache[key])
        st['phi'] = np.zeros((1, umax), dtype=np.float32)
        return st

    def sample(self, texts, style=None, bias=0.75, seeds=0, max_steps_per_char=40):
        """Generate one line per entry of ``texts``.

        ``seeds`` is one int per row (or a single int for all rows). Each row has
        its own generator, so a row's output does not depend on what else is in
        the batch.
        """
        n = len(texts)
        if np.isscalar(seeds):
            seeds = [seeds] * n
        rngs = [np.random.default_rng(int(q)) for q in seeds]
        prefix = load_style(style)[1] + ' ' if style is not None else ''
        seqs = [encode(prefix + t) for t in texts]
        lengths = np.array([len(q) for q in seqs])
        umax = lengths.max()
        onehot = np.zeros((n, umax, len(ALPHABET)), dtype=np.float32)
        mask = np.zeros((n, umax), dtype=np.float32)
        for i, q in enumerate(seqs):
            onehot[i, np.arange(len(q)), q] = 1.0
            mask[i, :len(q)] = 1.0
        primed = self._primed(style, umax)
        s = {k: np.repeat(v, n, axis=0) for k, v in primed.items()}
        biases = np.full(n, float(bias), dtype=np.float32)
        if style is not None:
            x = self._emit(s, biases, rngs)
        else:
            x = np.tile(np.array([[0.0, 0.0, 1.0]], dtype=np.float32), (n, 1))
        out = [[] for _ in range(n)]
        idx = [[] for _ in range(n)]
        limits = [max_steps_per_char * len(t) + 20 for t in texts]
        # after the attention reaches the end, let the pen finish the word (t-bars, i-dots)
        # for ``tail`` steps, then stop at the next pen lift
        tail = 14
        reached = [None] * n
        offset = len(prefix)
        active = np.arange(n)            # rows still writing; finished rows leave the batch
        while len(active):
            s = self._step(x, s, onehot[active], mask[active])
            char_at = np.argmax(s['phi'], axis=1)
            nxt = self._emit(s, biases[active], [rngs[i] for i in active])
            keep = []
            for j, i in enumerate(active):
                out[i].append(x[j].copy())
                idx[i].append(char_at[j] - offset)
                final = char_at[j] >= lengths[i] - 1
                past = char_at[j] >= lengths[i]
                if final and reached[i] is None:
                    reached[i] = len(out[i])
                stop = past or len(out[i]) >= limits[i]
                if reached[i] is not None and nxt[j, 2] == 1.0 and len(out[i]) - reached[i] >= tail:
                    stop = True
                if reached[i] is not None and len(out[i]) - reached[i] >= 4 * tail:
                    stop = True
                if not stop:
                    keep.append(j)
            keep = np.array(keep, dtype=np.int64)
            active = active[keep]
            s = {k: v[keep] for k, v in s.items()}
            x = nxt[keep]
        samples = []
        for i, t in enumerate(texts):
            off = np.array(out[i])
            ci = np.clip(np.array(idx[i]), -1, len(t))   # len(t) = after the last character
            samples.append(Sample(off, ci, t))
        return samples
