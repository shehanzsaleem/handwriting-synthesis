"""Build handwritten answer sheets.

    python -m integrations.revisionlibrary.build                 # every sample -> out/
    python -m integrations.revisionlibrary.build samples/03-*.md --png
    python -m integrations.revisionlibrary.build --set hand=teacher --set paper=ipad-grid FILE

Neural word samples are cached (``$HWSYNTH_CACHE``, default ~/.cache/hwsynth),
so a rebuild only re-runs layout and is byte-identical.
"""
from __future__ import annotations

import argparse
import glob
import json
import subprocess
import sys
import time
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

from integrations.revisionlibrary.answersheet import Composer, parse  # noqa: E402
from hwsynth.export import to_pdf  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('files', nargs='*', help='answer-sheet .md files (default: samples/*.md)')
    ap.add_argument('--out', default=str(HERE / 'out'))
    ap.add_argument('--png', action='store_true', help='also write PNG previews (needs pdftoppm)')
    ap.add_argument('--dpi', type=int, default=110)
    ap.add_argument('--set', action='append', default=[], metavar='KEY=VALUE',
                    help='override front matter, e.g. hand=teacher, paper=squared, hand_overrides.x_height=2.6')
    ap.add_argument('--cache', default=None)
    args = ap.parse_args(argv)
    files = args.files or sorted(glob.glob(str(HERE / 'samples' / '*.md')))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    index = []
    for f in files:
        t0 = time.time()
        meta, blocks = parse(f)
        for kv in args.set:
            k, v = kv.split('=', 1)
            v = yaml.safe_load(v)
            if '.' in k:
                a, b = k.split('.', 1)
                meta.setdefault(a, {})[b] = v
            else:
                meta[k] = v
        pages = Composer(meta, cache_dir=args.cache).compose(blocks)
        stem = meta.get('id', Path(f).stem)
        pdf = out / f'{stem}.pdf'
        pdf.write_bytes(to_pdf(pages, title=meta.get('title', stem)))
        pngs = []
        if args.png:
            subprocess.run(['pdftoppm', '-r', str(args.dpi), '-png', str(pdf), str(out / stem)], check=True)
            pngs = sorted(p.name for p in out.glob(f'{stem}-*.png'))
        dt = time.time() - t0
        index.append({'id': stem, 'title': meta.get('title'), 'subject': meta.get('subject'),
                      'source': meta.get('source'), 'paper': meta.get('paper'), 'hand': meta.get('hand'),
                      'pages': len(pages), 'pdf': pdf.name, 'png': pngs, 'seconds': round(dt, 1)})
        print(f'{stem}: {len(pages)} page(s) in {dt:.1f}s -> {pdf}')
    (out / 'index.json').write_text(json.dumps(index, indent=1))


if __name__ == '__main__':
    main()
