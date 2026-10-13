"""Engine tests: python3 -m unittest discover -s tests  (from the repo root)."""
import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from hwsynth.export import Scene, to_pdf, to_svg  # noqa: E402
from hwsynth.glyphs import GlyphPen, glyph_table  # noqa: E402
from hwsynth.hand import PROFILES, Hand, is_neural_word  # noqa: E402
from hwsynth.layoutkit import tokens  # noqa: E402
from hwsynth.mathtype import MathSetter, Parser, ce_to_tex  # noqa: E402
from hwsynth.model import Network  # noqa: E402


class ModelTest(unittest.TestCase):
    def test_weights_shapes(self):
        net = Network()
        self.assertEqual(net.w['k1'].shape, (476, 1600))
        self.assertEqual(net.w['kg'].shape, (400, 121))

    def test_sampling_is_seeded_and_batch_independent(self):
        net = Network()
        a = net.sample(['hello'], style=9, bias=1.0, seeds=[7])[0]
        b = net.sample(['world', 'hello'], style=9, bias=1.0, seeds=[3, 7])[1]
        np.testing.assert_array_equal(a.offsets, b.offsets)
        self.assertGreater(len(a.offsets), 20)


class GlyphTest(unittest.TestCase):
    def test_maths_symbols_exist(self):
        t = glyph_table()
        for ch in '0123456789+=−×÷±≤≥≠≈→⇒⇌√∫Σαβθλμπσ∞()[]':
            self.assertIn(ch, t, ch)

    def test_glyph_pen_deterministic(self):
        pen = GlyphPen()
        a = pen.write('3x + 2', 2.0, np.random.default_rng(1))
        b = pen.write('3x + 2', 2.0, np.random.default_rng(1))
        for p, q in zip(a.strokes, b.strokes):
            np.testing.assert_array_equal(p, q)


class MathTest(unittest.TestCase):
    def test_scripts_attach_to_bigop(self):
        n = Parser(r'\int_0^2 x\,dx').parse()
        self.assertEqual(n[0].kind, 'bigop')
        self.assertEqual(n[0].sub.kids[0].value, '0')
        self.assertEqual(n[0].sup.kids[0].value, '2')

    def test_ce(self):
        self.assertEqual(ce_to_tex('CH3COO- + H+ -> CH3COOH'),
                         'CH_{3}COO^{−} + H^{+} \\rightarrow CH_{3}COOH')

    def test_fraction_is_taller_than_its_parts(self):
        hand = Hand(PROFILES['student'], verify=False, cache_dir=tempfile.mkdtemp())
        ms = MathSetter(hand, 't')
        flat, frac = ms.layout('x'), ms.layout(r'\frac{x}{2}')
        self.assertGreater(frac.ascent + frac.descent, 1.8 * (flat.ascent + flat.descent))


class LayoutTest(unittest.TestCase):
    def test_routing(self):
        self.assertTrue(is_neural_word('gradient,'))
        self.assertFalse(is_neural_word('3x'))
        self.assertFalse(is_neural_word('Zero'))     # Z is not in the network alphabet

    def test_tokens_split_words_and_maths(self):
        t = tokens('so $x = 2$, then numbers[i]')
        kinds = [k[0] for k in t]
        self.assertEqual(kinds, ['word', 'math', 'word', 'word'])
        self.assertEqual(t[1][1], 'x = 2,')           # punctuation glued to the maths
        self.assertEqual(t[3][1], ['numbers', '[i]'])


class ExportTest(unittest.TestCase):
    def test_pdf_is_valid_and_deterministic(self):
        def make():
            sc = Scene()
            sc.add_rule([[0, 20], [210, 20]])
            sc.text.append((10, 10, 9, 'Question (a) 2 × 3', '#333333', False))
            ink = GlyphPen().write('y = 3x²', 3.0, np.random.default_rng(0))
            sc.add_ink([s + [20, 40] for s in ink.strokes], 'ballpoint', seed=1)
            return to_pdf([sc, sc])
        a, b = make(), make()
        self.assertEqual(hashlib.sha256(a).hexdigest(), hashlib.sha256(b).hexdigest())
        with tempfile.NamedTemporaryFile(suffix='.pdf') as f:
            f.write(a)
            f.flush()
            info = subprocess.run(['pdfinfo', f.name], capture_output=True, text=True)
            if info.returncode == 0:
                self.assertIn('Pages:          2', info.stdout)
        self.assertIn('<svg', to_svg(Scene()))


class CheckpointTest(unittest.TestCase):
    def test_reader_matches_exported_weights(self):
        sys.path.insert(0, str(ROOT / 'tools'))
        from export_checkpoint import read_checkpoint
        t = read_checkpoint(str(ROOT / 'checkpoints' / 'model-17900'))
        w = np.load(ROOT / 'hwsynth' / 'data' / 'weights.npz')
        np.testing.assert_array_equal(t['rnn/gmm/weights'], w['rnn/gmm/weights'])


if __name__ == '__main__':
    unittest.main()
