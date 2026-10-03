# Modernization Plan

Goal (from the original README's "Contribute" section): *package this, and otherwise make it look more like a usable software project and less like research code.*

Status: **plan only — no code changes yet.** Written 2026-10-04.

---

## 1. Current state assessment

The repo is ~2,000 lines of Python, a 44 MB pretrained checkpoint (`checkpoints/model-17900.*`) and 28 style-priming files (`styles/*.npy`). Last upstream commit: February 2020.

| Problem | Where | Impact |
|---|---|---|
| Pinned to `tensorflow==1.6.0`; uses `tf.contrib`, `tf.placeholder`, `tf.Session`, `variable_scope` | `requirements.txt`, `rnn.py`, `rnn_cell.py`, `tf_utils.py`, `tf_base_model.py` | **Cannot install on any modern Python** (TF 1.6 supports Python ≤ 3.6). This is the blocker. |
| No package structure; all modules at top level | repo root | README admits `Hand` must be imported from `demo.py`. |
| Inference coupled to training | `demo.py` `Hand.__init__` | Writing text constructs the full training model with ~20 hardcoded training hyperparameters (learning rates, patiences, batch sizes). |
| Paths relative to the working directory | `'styles/style-{}-strokes.npy'`, `'checkpoints'` | Breaks unless run from the repo root. |
| No CLI | — | Only usable by editing `demo.py`. |
| No tests; dead CI | `.travis.yml` | Travis only runs flake8 against Python 2.7 / 3.6. |
| No LICENSE file | repo root (same upstream) | Blocks a clean PyPI release; needs a decision. |
| Validation mixed into `write()` | `demo.py` | Ad-hoc `ValueError`s for line length (75) and charset. |

## 2. Recommended approach: characterize, then strangle in phases

This is not a pure tidy-up — the ML backend must be replaced. So capture the original behaviour first and verify every subsequent change against it.

### Phase 0 — Capture an oracle (one-time, legacy environment)

Run the original code untouched in a throwaway container (`python:3.6` + `tensorflow==1.6.0`) and use it to:

1. **Export the checkpoint weights** to a framework-neutral format (`.npz` or safetensors), keyed by variable name.
2. **Record golden outputs** for regression tests:
   - Deterministic: mixture-density / attention parameters for fixed inputs under teacher forcing (exact numeric comparison possible).
   - Stochastic: a handful of fixed-seed samples (for visual sanity checks, not exact comparison).

After this phase, TF 1.6 is never needed again, and the 44 MB TF checkpoint is no longer needed at runtime.

### Phase 1 — Port inference to a modern backend

The model is small: 3 × LSTM(400) with Gaussian-window attention (10 components) and a mixture-density output (20 components).

- Re-implement **only the sampling path** (`rnn_free_run` + `LSTMAttentionCell`) and load the exported weights.
- Verify against the Phase 0 deterministic outputs (tight numeric tolerance).
- Training code: either keep it frozen under `legacy/` or port it as a separate, later task.

Backend choice (**open decision**, see §4): PyTorch vs. NumPy-only.

### Phase 2 — Package it

- `src/handwriting_synthesis/` layout + `pyproject.toml`, managed with `uv`.
- Ship weights + styles as package data, loaded via `importlib.resources` (no CWD dependence). Optionally fetch weights from a release asset / Hugging Face Hub instead of keeping them in git.
- Clean public API:
  ```python
  from handwriting_synthesis import Hand
  Hand().write("out.svg", ["Hello world"], styles=[9], biases=[0.75])
  ```
  with an inference-only config — no training hyperparameters.
- Separate modules: `model` (network), `sampling`, `styles`, `render` (SVG), `text` (alphabet/validation).
- CLI:
  ```
  handwrite "Hello world" -o out.svg --style 9 --bias 0.75 --color black --width 2
  ```
- Type hints, `ruff`, structured exceptions instead of ad-hoc `ValueError`s, `logging` instead of `print`.

### Phase 3 — Project hygiene

- `pytest` suite driven by the Phase 0 golden outputs, plus unit tests for text validation and SVG rendering.
- GitHub Actions (lint + tests on current Python versions) replacing `.travis.yml`.
- README rewritten around `pip install` + CLI + API; move the lyric demos to `examples/`.
- LICENSE resolved (see §4), CHANGELOG, version tag / PyPI release.

### Phase 4 (optional) — Features

The original author's second wish: richer drawing and animation. Once rendering is its own module this is straightforward — e.g. animated SVG (pen-stroke reveal via `stroke-dashoffset`), PNG/PDF export, per-line layout options, a small web demo.

## 3. Rejected alternatives

| Option | Why not |
|---|---|
| Package as-is with TF 1.6 pinned, or ship only a Docker image | Fast, but still research code in a box; nobody can `pip install` it on a current Python. |
| Migrate to TF2 via `tf.compat.v1` | Smaller diff, but keeps a huge dependency, still requires rewriting the `contrib` pieces, and checkpoint variable names change anyway — roughly the same effort as a port for a worse result. |

## 4. Open decisions

1. **Backend:** PyTorch (familiar, easy to extend/retrain) or NumPy-only (tiny install, inference only)?
2. **Training:** port it too, or keep the original under `legacy/` as reference?
3. **Weights distribution:** keep in git (simple, 44 MB) or download on first use (lighter repo/package)?
4. **License:** upstream (sjvasquez/handwriting-synthesis) has no license file. Ask upstream to add one before publishing to PyPI; until then keep this as a personal fork.

## 5. Execution notes

- The Phase 1 port is self-contained and well-specified once Phase 0 exists — a good candidate to delegate to a Codex sub-agent.
- Work on feature branches per phase; the golden-output tests are the merge gate for each.
