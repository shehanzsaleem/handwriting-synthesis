# 14 October ongoing work (paused for shutdown)

Paused on the owner's request at about 01:00 on 2026-10-14, mid-way through the four-task brief
(handwriting PDFs, UI consistency audit, weekly inbox/requests/DMARC review, final consolidation).
Everything is committed and pushed. Nothing important lived only in /tmp.

## Task 0: branch consolidation: DONE (no changes needed)
- Site, worksheets, dashboard, growth and marketing repos: every repo was on `staging` with no unmerged
  side branches. `main` in the dashboard and growth repos is ahead only by release merge commits with
  zero unique diff. The site's `staging` is 173 commits ahead of `main` (the next Saturday release); that was left alone.

## Task 1: handwriting synthesis: IN PROGRESS (engine done, 9/20 pages rendered)
Repo `~/repos/handwriting-synthesis`, branch `staging` (pushed; last commit a66d914 plus this doc).

Built:
- `tools/export_checkpoint.py` reads the TF1 checkpoint without TensorFlow -> `hwsynth/data/weights.npz`.
- `hwsynth/` is the reusable engine. It holds:
  - the NumPy port of the Graves model (`model.py`): per-row seeds and cached priming;
  - best-of-K word sampling with OCR ranking, a letter-shape penalty, an escalation round and a disk cache (`writer.py`, cache in `~/.cache/hwsynth`, which survives a reboot);
  - per-style size calibration;
  - the glyph pen for maths, digits and symbols (`glyphs.py`: OFL EMS fonts normalised to their real x-heights, plus hand-authored Greek, arrows and relations);
  - the maths typesetter (`mathtype.py`: LaTeX subset plus `\ce{}`);
  - sketches (`sketch.py`: axes, curves, arrows, curly arrows, tables, hatching);
  - wrapping (`layoutkit.py`), pen outlines (`ink.py`) and the deterministic SVG/PDF writer (`export.py`).
- `integrations/revisionlibrary/` is the answer-sheet format, paper templates, margin marks and the build CLI. See its README.
- 20 sample specs in `integrations/revisionlibrary/samples/`, all from Revision Library mock-bank questions,
  answers checked by hand. Subjects: A-level Maths x4, Further Maths x4, Biology x3, Chemistry x3, GCSE CS x3,
  Physics, Economics, GCSE English.
- Tests: `python3 -m unittest discover -s tests`. They were written but NOT yet run.

Rendered so far (`integrations/revisionlibrary/out/`, gitignored): 01-09. The build of 10-20 was stopped
mid-way; cached words are kept, so restarting resumes cheaply.

Fixes made after the last render, not yet seen on a page:
- decimal points were invisible ("0.5" showed as "05"); dots are now firm dabs (`ink.py`);
- font x-heights normalised, so print letters in formulae were 1.6x too tall before;
- table rows given more padding.

Known issues still open:
- The network cannot write "x" (e.g. "oxygen" came out "oiygen"). An in-word x repair was added
  (`replace_letters`, `HandProfile.repair='x'`) but has not been seen on a page yet.
- Prose size versus maths size differs per style. Re-check after the font normalisation and tune
  `neural_scale` per profile if needed.
- Stray letters now and then ("of" came out "ofo"). Raise `candidates` or check OCR on two-letter words.
- `tools/style_benchmark.py` was killed after style 0 (16/24 words exact). Rerun on styles 3, 5, 7, 8, 9, 11, 12
  with `OMP_NUM_THREADS=4` so it does not starve the builds, then pick the profile styles from it.

To resume:
1. `cd ~/repos/handwriting-synthesis && python3 -m unittest discover -s tests`
2. `python3 -m integrations.revisionlibrary.build --png`. This rebuilds all 20 and writes `out/index.json` for all of them.
   Run only ONE heavy job at a time: two numpy jobs plus Codex pushed the load to 32 on 12 cores.
3. Review the pages, fix, rebuild.
4. Make the review page: `python3 tools/make_review_artifact.py <scratch>/art "Round 1"`. It writes index.html,
   img/ and pdf/. Publish it with the Artifact tool: `files` = files.json, capabilities `{db:{}, user:{}}`;
   feedback lands in db collection `feedback`. Open it in the owner's browser and ask for feedback (the owner's
   explicit request). Then read the feedback with ArtifactData `list` on `feedback`.

## Tasks 2 and 3: dashboard recurring tasks: IN PROGRESS (Codex WIP, untested)
Repo `~/repos/revisionlibrary/revisionlibrary-dashboard`, branch `ops-audits-inbox-2026-10-14`, worktree
`.claude/worktrees/ops-audits`, WIP commit f91163a (pushed). Spec: `.codex-brief.md` in that worktree.
Codex was stopped mid-run, so the gate (`yarn typecheck && yarn test:unit && yarn lint`) has NOT been run.

What the spec does:
- **New `ui-consistency` review, every 3 days.**
  - Visual consistency only: typography, spacing, colours, buttons, cards, layouts, navigation, components and responsiveness.
  - Uses the same method as the 2026-10-12 audit: the `ui-consistency-audit` skill at 390 and 1440 px, against dev server 3123 or 3000.
  - The site's `docs/projects/ui-audit-2026-10-12.md` decisions are the rulebook. A regression against them is fixed directly; a new inconsistency goes to an artifact and the owner's questions.
- **Existing `app-qa` refocused on UX and usability.**
  - Same id, cookie and schedule.
  - Journeys may start on public pages, and common actions are completed end to end.
  - Visual consistency is explicitly out of scope and handed to the UI audit.
  - "layout" is replaced by "flows" in the fix list.
- **New `inbox-weekly` review, Fridays 21:00 London.**
  - The ledger lives in `dashboard_task_state` row `inbox-weekly:ledger` (baseline jsonb), so no new table and no migration.
  - `lib/inboxLedger.ts` and `scripts/inbox-ledger.mjs` hold it. Deadline = receipt + 7 days, with an overdue / due-in-48h panel.
  - Request reply tracking goes in `topic_requests.meta.reply`. Replies are Gmail DRAFTS only, written after a production 200 check, never twice.
  - DMARC parsing: `lib/dmarc.ts` and `scripts/dmarc-report.mjs` (xml, gz, zip).
  - The prompt is written for Claude Code plus Claude in Chrome signed into BOTH Workspace mailboxes. The Gmail connector in Claude Code is a different account with no DMARC mail, checked 2026-10-14.

To resume: in that worktree, review `git show f91163a --stat`, run the gate, finish what is missing per the
brief, then commit for real (the version hook bumps) and merge into dashboard `staging` only. Never merge to `main`.

## Task 4: final consolidation and report: NOT STARTED
After 1-3: merge `ops-audits-inbox-2026-10-14` into dashboard `staging` and delete the branch and worktree; the
handwriting repo already works on `staging`. Then give the owner the summary the brief asks for.
