"""Integration tests for the Revision Library answer sheets."""
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from hwsynth.export import to_pdf  # noqa: E402
from integrations.revisionlibrary.answersheet import Composer, parse  # noqa: E402

DOC = """---
id: t
subject: Test
paper: lined
hand: student
question: |
  Solve 2x + 1 = 7.
score: 2/2
---
## Q1

$$ 2x &= 6 \\\\ x &= 3 $$ {M1 A1}

::: table
| $x$ | $3$ |
:::
"""


class AnswerSheetTest(unittest.TestCase):
    def test_parse(self):
        meta, blocks = parse(DOC)
        self.assertEqual(meta['id'], 't')
        self.assertEqual([b.kind for b in blocks], ['label', 'math', 'table'])
        self.assertEqual(blocks[1].marks, ['M1', 'A1'])

    def test_every_sample_parses(self):
        for f in sorted((ROOT / 'integrations' / 'revisionlibrary' / 'samples').glob('*.md')):
            meta, blocks = parse(f)
            self.assertTrue(meta.get('id'), f)
            self.assertTrue(meta.get('question'), f)
            self.assertTrue(blocks, f)

    def test_build_is_byte_identical(self):
        cache = tempfile.mkdtemp()
        meta, blocks = parse(DOC)
        a = to_pdf(Composer(meta, cache_dir=cache).compose(blocks))
        meta, blocks = parse(DOC)
        b = to_pdf(Composer(meta, cache_dir=cache).compose(blocks))
        self.assertEqual(hashlib.sha256(a).hexdigest(), hashlib.sha256(b).hexdigest())


if __name__ == '__main__':
    unittest.main()
