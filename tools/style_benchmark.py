"""Rank the network's priming styles by how legibly they write a tricky vocabulary.

    python tools/style_benchmark.py [--styles 0 1 2] [--bias 1.0]

For each style, every word is written with the normal best-of-K selection and
read back by OCR; a style's score is the share of words read back exactly and
the mean edit distance. Results are cached like any other writing.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hwsynth.writer import Writer, _canon, _lev  # noqa: E402

WORDS = ['oxygen', 'exactly', 'maximum', 'expand', 'next', 'quickly', 'zero', 'amazing', 'of', 'the',
         'gradient', 'tangent', 'affinity', 'equation', 'therefore', 'substitute', 'velocity',
         'haemoglobin', 'mechanism', 'algorithm', 'jumps', 'value', 'brown', 'writing']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--styles', type=int, nargs='*', default=list(range(13)))
    ap.add_argument('--bias', type=float, default=1.0)
    args = ap.parse_args()
    rows = []
    for st in args.styles:
        w = Writer(style=st, bias=args.bias, x_height=2.0, candidates=6)
        w.write_many(WORDS)
        exact, dist = 0, 0.0
        bad = []
        for t in WORDS:
            c = w._load(t, 0)
            d = _lev(_canon(c.read), _canon(t)) / max(len(t), 1)
            dist += d
            exact += d == 0
            if d > 0:
                bad.append(f'{t}->{c.read}')
        rows.append({'style': st, 'exact': exact, 'mean_dist': round(dist / len(WORDS), 3), 'misread': bad})
        print(json.dumps(rows[-1]), flush=True)
    rows.sort(key=lambda r: (-r['exact'], r['mean_dist']))
    print('ranking:', [r['style'] for r in rows])


if __name__ == '__main__':
    main()
