# Revision Library handwritten answer sheets

Turns a question and its mark scheme into a PDF that looks written by hand: by a
student with a ballpoint on lined or squared paper, by a teacher writing a model
answer, or on an iPad. The handwriting engine is the separate `hwsynth` package
in this repo; this folder only knows about answer sheets.

```
python3 -m integrations.revisionlibrary.build                    # all samples -> out/*.pdf
python3 -m integrations.revisionlibrary.build samples/09-*.md --png
python3 -m integrations.revisionlibrary.build --set hand=teacher --set paper=ipad-grid samples/01-*.md
python3 -m unittest discover -s tests                            # engine + integration tests
```

The first build of a sheet samples every new word from the network (roughly
1-2 minutes a page on this machine). Every chosen word is cached
(`$HWSYNTH_CACHE`, default `~/.cache/hwsynth`), so later builds take well under
a second and are byte-identical. Change a sentence and only the new words are
sampled.

## The answer-sheet format

One Markdown-like file per question, YAML front matter then blocks separated by
blank lines. See the docstring of `answersheet.py` for the full grammar.

| Block | Written as |
|---|---|
| `## Q4 (a)` | a handwritten, underlined label |
| a paragraph | wrapped handwriting; `$...$` is inline maths; `**word**` is underlined |
| `$$ ... $$` | display maths; `\\` starts a new line, `&` aligns lines on that point |
| `{M1 A1}` at the end of a block | marks in the margin in the marker pen, level with the block's last line |
| `> text` | a teacher's comment in the marker pen |
| `::: sketch {width, height}` | a hand-drawn diagram (YAML list of items, see `hwsynth/sketch.py`) |
| `::: table` | a hand-drawn grid with handwritten cells (`|` rows) |
| `::: code` | pseudocode, indentation kept (4 spaces = one level) |
| `---` | page break |

Front matter keys: `id`, `title`, `subject`, `source`, `marks`, `question` (printed
at the top), `paper`, `hand`, `hand_overrides`, `pen`, `marker`, `score` (ringed in
the marker pen at the end), `footer`, `seed`, `scale`.

## Everything is configurable

| Knob | Where | Values |
|---|---|---|
| paper | `paper:` | `lined`, `narrow`, `squared`, `ipad-grid`, `ipad-dots`, `plain`, `exam` (`PAPERS` in `answersheet.py`; `paper_overrides` changes pitch, margins, colours) |
| writer | `hand:` | `student`, `student-neat`, `student-quick`, `teacher`, `ipad` (`PROFILES` in `hwsynth/hand.py`) |
| size and spacing | `hand_overrides:` | `x_height` (mm), `word_space`, `baseline_wander`, `slant`, `jitter`, `glyph_scale` |
| neatness | `hand_overrides.bias` | higher is neater and less varied (0.6 to 1.6) |
| network style | `hand_overrides.style` | 0-12; `tools/style_benchmark.py` ranks them for legibility |
| pen | `pen:` / `marker:` | `ballpoint`, `ballpoint-black`, `gel`, `teacher-red`, `pencil-ipad`, `ipad-blue`, `ipad-red` (`PENS` in `hwsynth/ink.py`) |
| maths letters | `hand_overrides.glyph_font` | single-stroke font for digits and symbols (`EMSAllure`, `EMSFelix`, `EMSReadability`) |
| variation | `seed:` | any int: a different but equally deterministic sheet |

## How a page is made

1. **Words**: alphabetic prose goes to the neural network (a NumPy port of Graves'
   handwriting model). Each word is sampled K times from one seed, read back by OCR
   and checked letter by letter for size; the best is kept. Words nobody writes
   cleanly get a second, neater round. The letter `x`, which the network writes
   badly, is redrawn by the glyph pen inside the word.
2. **Maths and symbols**: digits, variables, operators, Greek and arrows are drawn
   by the glyph pen (OFL single-stroke fonts plus hand-authored glyphs), slanted and
   jittered to match the hand, and laid out by `hwsynth/mathtype.py`
   (fractions, roots, scripts, matrices, integrals, `\ce{}` chemistry).
3. **Diagrams and tables**: `hwsynth/sketch.py` draws axes, curves, shapes, arrows,
   curly arrows, hatching and grids with pen wobble, overshoot and unclosed circles.
4. **Page**: words and boxes are placed on the paper's rules with small line slopes,
   start jitter and baseline wander; marks go in the margin.
5. **Ink**: every centreline is outlined by a pen model (speed thinning, end taper,
   pressure wobble) and written to a deterministic vector PDF.

## Iterating on quality

- Look at `out/*.png` (`--png`), change one knob with `--set`, rebuild: cached words
  make it instant.
- A wrongly written word: bump that sheet's `seed`, or raise `bias` in
  `hand_overrides`; delete its cache file to resample just it.
- A hand that writes a letter badly everywhere: add the letter to the profile's
  `repair` list.
- Engine changes that alter sampling bump `ENGINE_VERSION` in `hwsynth/writer.py`,
  which invalidates the word cache.

## From a question PDF and mark scheme to a handwritten PDF

The renderer is deterministic and free to run. The one step that needs judgement is
turning a mark scheme into a worked answer in this format:

1. Extract the question and the mark-scheme lines (`pdftotext -layout` on the paper,
   or the bank JSON: `prompt`, `markScheme`, `finalAnswer` in the site's
   `public/mock-paper-question-bank-*.json`).
2. Write the answer sheet: one block per marking point, its mark code in braces.
   For bank questions this is a mechanical mapping and can be scripted; for prose or
   diagram answers it is a single short LLM call per question, cached as the `.md`
   file, after which every re-render costs nothing.
3. Build. The `.md` file is the reviewable, version-controlled source of truth.

Licensing: the samples use Revision Library's own mock-bank questions. Board papers are
not reproduced (see the site's past-papers hosting rule).
