"""Build the handwriting review artifact (HTML + page images) from out/index.json."""
import html
import json
import shutil
import sys
from pathlib import Path

from PIL import Image

OUT = Path('/home/han/repos/handwriting-synthesis/integrations/revisionlibrary/out')
ART = Path(sys.argv[1])
ROUND = sys.argv[2] if len(sys.argv) > 2 else 'Round 1'
(ART / 'img').mkdir(parents=True, exist_ok=True)
(ART / 'pdf').mkdir(parents=True, exist_ok=True)
index = json.loads((OUT / 'index.json').read_text())

HANDS = {'student': 'Student, quick print', 'student-neat': 'Student, neat', 'student-quick': 'Student, fast',
         'teacher': 'Teacher model answer', 'ipad': 'iPad, Apple Pencil'}
PAPERS = {'lined': 'Lined A4', 'narrow': 'Narrow lined', 'squared': '5 mm squared', 'ipad-grid': 'iPad grid',
          'ipad-dots': 'iPad dot grid', 'plain': 'Plain', 'exam': 'Exam answer lines'}

cards = []
files = []
for row in index:
    imgs = []
    for png in row['png']:
        im = Image.open(OUT / png).convert('RGB')
        im.thumbnail((1240, 1754))
        name = png.replace('.png', '.jpg')
        im.save(ART / 'img' / name, quality=84, optimize=True)
        imgs.append(name)
        files.append(f'img/{name}')
    shutil.copy(OUT / row['pdf'], ART / 'pdf' / row['pdf'])
    files.append(f"pdf/{row['pdf']}")
    pages = ''.join(
        f'<button class="page" data-full="img/{n}" aria-label="Open page {i + 1} full size">'
        f'<img src="img/{n}" alt="Handwritten page {i + 1} of {html.escape(row["title"] or "")}" loading="lazy"></button>'
        for i, n in enumerate(imgs))
    num = row['id'][:2]
    cards.append(f'''
<article class="card" id="s{num}" data-id="{row['id']}" data-subject="{html.escape(row['subject'] or '')}">
  <div class="pages">{pages}</div>
  <div class="meta">
    <p class="num">Sample {num}</p>
    <h2>{html.escape((row['title'] or '').split(' - ', 1)[-1])}</h2>
    <p class="subj">{html.escape(row['subject'] or '')}</p>
    <p class="src">{html.escape(row['source'] or '')}</p>
    <div class="chips"><span>{PAPERS.get(row['paper'], row['paper'])}</span><span>{HANDS.get(row['hand'], row['hand'])}</span><span>{row['pages']} page{'s' if row['pages'] > 1 else ''}</span></div>
    <a class="pdf" href="pdf/{row['pdf']}" target="_blank" rel="noopener">Open the PDF</a>
    <form class="fb" data-id="{row['id']}">
      <fieldset><legend>Looks hand-written?</legend>
        <label><input type="radio" name="real-{num}" value="yes" id="real-{num}-y">Yes</label>
        <label><input type="radio" name="real-{num}" value="almost" id="real-{num}-a">Almost</label>
        <label><input type="radio" name="real-{num}" value="no" id="real-{num}-n">No</label></fieldset>
      <fieldset><legend>Easy to read?</legend>
        <label><input type="radio" name="read-{num}" value="yes" id="read-{num}-y">Yes</label>
        <label><input type="radio" name="read-{num}" value="almost" id="read-{num}-a">Mostly</label>
        <label><input type="radio" name="read-{num}" value="no" id="read-{num}-n">No</label></fieldset>
      <fieldset><legend>Answer correct and complete?</legend>
        <label><input type="radio" name="right-{num}" value="yes" id="right-{num}-y">Yes</label>
        <label><input type="radio" name="right-{num}" value="no" id="right-{num}-n">Spotted an error</label></fieldset>
      <label class="note" for="note-{num}">What should change?</label>
      <textarea id="note-{num}" rows="3" placeholder="e.g. the x in line 3 looks like an r; fractions too small; prefer the iPad look"></textarea>
      <div class="row"><button type="submit">Save feedback</button><span class="status" aria-live="polite"></span></div>
    </form>
  </div>
</article>''')

subjects = sorted({r['subject'] for r in index if r['subject']})
filters = ''.join(f'<button class="f" data-s="{html.escape(s)}">{html.escape(s)}</button>' for s in subjects)

page = f'''<title>Handwritten Answer Samples</title>
<style>
/* Layout: one review column per sample (page image left, feedback right), stacked; overall questions first. */
:root {{
  --paper: #f3f4f6; --sheet: #ffffff; --ink: #1b2a4a; --ink-soft: #4a5876; --rule: #d5dbe6;
  --accent: #2350c8; --mark: #c8202f; --chip: #e7ebf3;
  --display: "Kalam", "Segoe Print", "Bradley Hand", cursive;
  --body: "Source Sans 3", "Segoe UI", system-ui, sans-serif;
  --mono: "JetBrains Mono", ui-monospace, monospace;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --paper: #12161f; --sheet: #1b2130; --ink: #e6eaf3; --ink-soft: #a9b3c8; --rule: #2e3648;
  --accent: #7ea0ff; --mark: #ff6b78; --chip: #262e40; color-scheme: dark }} }}
:root[data-theme="dark"] {{
  --paper: #12161f; --sheet: #1b2130; --ink: #e6eaf3; --ink-soft: #a9b3c8; --rule: #2e3648;
  --accent: #7ea0ff; --mark: #ff6b78; --chip: #262e40; color-scheme: dark }}
body {{ background: var(--paper); color: var(--ink); font-family: var(--body); font-size: 16px; line-height: 1.5; }}
.wrap {{ max-width: 1180px; margin: 0 auto; padding-inline: 16px; padding-block: 28px 64px; display: grid; gap: 28px; }}
header h1 {{ font-family: var(--display); font-weight: 700; font-size: clamp(30px, 5vw, 46px); line-height: 1.1; margin: 0; text-wrap: balance; }}
header p {{ max-width: 68ch; margin: 10px 0 0; color: var(--ink-soft); }}
header .round {{ font-family: var(--mono); font-size: 12px; letter-spacing: .06em; text-transform: uppercase; color: var(--mark); margin: 0 0 6px; }}
.overall {{ background: var(--sheet); border: 1px solid var(--rule); border-radius: 10px; padding: 20px; display: grid; gap: 14px; }}
.overall h2 {{ margin: 0; font-size: 20px; }}
.grid2 {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 14px; }}
.filters {{ display: flex; flex-wrap: wrap; gap: 8px; position: sticky; top: env(safe-area-inset-top, 0px); background: var(--paper); padding-block: 10px; z-index: 2; }}
.f {{ font: 13px var(--body); border: 1px solid var(--rule); background: var(--sheet); color: var(--ink); border-radius: 999px; padding: 5px 12px; cursor: pointer; }}
.f[aria-pressed="true"] {{ background: var(--accent); color: var(--sheet); border-color: var(--accent); }}
.card {{ display: grid; grid-template-columns: minmax(0, 1.25fr) minmax(0, 1fr); gap: 22px; background: var(--sheet); border: 1px solid var(--rule); border-radius: 10px; padding: 18px; }}
@media (max-width: 820px) {{ .card {{ grid-template-columns: minmax(0, 1fr); }} }}
.pages {{ display: grid; gap: 10px; }}
.page {{ padding: 0; border: 1px solid var(--rule); background: #fff; cursor: zoom-in; border-radius: 4px; overflow: hidden; }}
.page img {{ display: block; width: 100%; height: auto; }}
.meta {{ display: grid; gap: 8px; align-content: start; min-width: 0; }}
.num {{ font-family: var(--mono); font-size: 12px; color: var(--mark); margin: 0; letter-spacing: .06em; text-transform: uppercase; }}
.meta h2 {{ font-size: 22px; line-height: 1.25; margin: 0; text-wrap: balance; }}
.subj {{ margin: 0; font-weight: 600; }}
.src {{ margin: 0; color: var(--ink-soft); font-size: 14px; }}
.chips {{ display: flex; flex-wrap: wrap; gap: 6px; }}
.chips span {{ background: var(--chip); border-radius: 4px; padding: 2px 8px; font-size: 13px; }}
.pdf {{ color: var(--accent); font-weight: 600; font-size: 14px; }}
fieldset {{ border: 0; padding: 0; margin: 0; display: flex; flex-wrap: wrap; gap: 6px 14px; align-items: center; }}
legend {{ font-weight: 600; font-size: 14px; padding: 0; margin-bottom: 4px; width: 100%; }}
fieldset label {{ display: inline-flex; gap: 6px; align-items: center; font-size: 14px; cursor: pointer; }}
.fb {{ display: grid; gap: 12px; border-top: 1px solid var(--rule); padding-top: 12px; margin-top: 4px; }}
.note {{ font-weight: 600; font-size: 14px; }}
textarea {{ width: 100%; box-sizing: border-box; font: 15px var(--body); color: var(--ink); background: var(--paper); border: 1px solid var(--rule); border-radius: 6px; padding: 8px; resize: vertical; }}
.row {{ display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }}
button[type="submit"] {{ font: 600 14px var(--body); background: var(--accent); color: var(--sheet); border: 0; border-radius: 6px; padding: 8px 16px; cursor: pointer; }}
button:focus-visible, .f:focus-visible, textarea:focus-visible, input:focus-visible {{ outline: 2px solid var(--accent); outline-offset: 2px; }}
.status {{ font-size: 13px; color: var(--ink-soft); }}
.lb {{ position: fixed; inset: 0; background: rgba(10, 14, 22, .86); display: grid; place-items: start center; overflow: auto; z-index: 10; padding: 16px; }}
.lb img {{ max-width: min(1240px, 100%); height: auto; background: #fff; }}
.lb button {{ position: fixed; top: calc(env(safe-area-inset-top, 0px) + 12px); right: 16px; font: 600 14px var(--body); border: 0; border-radius: 6px; padding: 8px 14px; background: var(--sheet); color: var(--ink); cursor: pointer; }}
.offline {{ font-size: 13px; color: var(--mark); }}
</style>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Kalam:wght@700&family=Source+Sans+3:wght@400;600&family=JetBrains+Mono:wght@500&display=swap">
<div class="wrap">
<header>
  <p class="round">{ROUND} · 20 samples · Revision Library mock-bank questions</p>
  <h1>Handwritten answer samples</h1>
  <p>Every page below was drawn by the new deterministic pipeline: prose by the handwriting network, maths and symbols by the pen engine, diagrams by hand-drawn sketch primitives, with mark-scheme codes in the margin. Rebuilding gives byte-identical PDFs. Tap a page to see it full size. Rate each sample and say what should change; your answers are saved here and read straight back into the next round.</p>
</header>
<section class="overall" aria-labelledby="ov">
  <h2 id="ov">Overall</h2>
  <form class="fb" data-id="_overall">
    <div class="grid2">
      <fieldset><legend>Which writer looks most real?</legend>
        <label><input type="radio" name="o-hand" value="student" id="o-hand-1">Student, quick print (01, 07, 08, 12, 15)</label>
        <label><input type="radio" name="o-hand" value="student-neat" id="o-hand-2">Student, neat (09, 13, 17, 20)</label>
        <label><input type="radio" name="o-hand" value="student-quick" id="o-hand-3">Student, fast (02, 11, 16)</label>
        <label><input type="radio" name="o-hand" value="teacher" id="o-hand-4">Teacher (04, 06, 18)</label>
        <label><input type="radio" name="o-hand" value="ipad" id="o-hand-5">iPad (03, 05, 10, 14, 19)</label></fieldset>
      <fieldset><legend>Writing size</legend>
        <label><input type="radio" name="o-size" value="smaller" id="o-size-1">Smaller</label>
        <label><input type="radio" name="o-size" value="right" id="o-size-2">About right</label>
        <label><input type="radio" name="o-size" value="bigger" id="o-size-3">Bigger</label></fieldset>
      <fieldset><legend>Mark codes in the margin (M1, A1)</legend>
        <label><input type="radio" name="o-marks" value="keep" id="o-marks-1">Keep</label>
        <label><input type="radio" name="o-marks" value="ticks" id="o-marks-2">Add ticks too</label>
        <label><input type="radio" name="o-marks" value="drop" id="o-marks-3">Leave them out</label></fieldset>
      <fieldset><legend>Printed question at the top</legend>
        <label><input type="radio" name="o-q" value="keep" id="o-q-1">Keep</label>
        <label><input type="radio" name="o-q" value="drop" id="o-q-2">Handwriting only</label></fieldset>
    </div>
    <label class="note" for="o-note">Anything else for the next round?</label>
    <textarea id="o-note" rows="3" placeholder="What looks fake, what to prioritise next"></textarea>
    <div class="row"><button type="submit">Save overall feedback</button><span class="status" aria-live="polite"></span></div>
  </form>
</section>
<nav class="filters" aria-label="Filter by subject"><button class="f" data-s="" aria-pressed="true">All</button>{filters}</nav>
{''.join(cards)}
<p class="offline" id="offline" hidden>Feedback cannot be saved in this view. Reply in the terminal instead, quoting the sample number.</p>
</div>
<script>
(function () {{
  const forms = [...document.querySelectorAll('form.fb')];
  function fill(form, d) {{
    if (!d) return;
    for (const [k, v] of Object.entries(d.choices || {{}})) {{
      const el = form.querySelector('input[name="' + k + '"][value="' + v + '"]');
      if (el) el.checked = true;
    }}
    const ta = form.querySelector('textarea');
    if (ta && typeof d.note === 'string' && !ta.value) ta.value = d.note;
    const st = form.querySelector('.status');
    if (st && d.savedAt) st.textContent = 'Saved ' + new Date(d.savedAt).toLocaleString();
  }}
  let db = null;
  forms.forEach(function (form) {{
    form.addEventListener('submit', async function (ev) {{
      ev.preventDefault();
      const st = form.querySelector('.status');
      if (!db) {{ st.textContent = 'Saving is not available here: reply in the terminal.'; return; }}
      const choices = {{}};
      form.querySelectorAll('input[type=radio]:checked').forEach(function (r) {{ choices[r.name] = r.value; }});
      const note = (form.querySelector('textarea') || {{}}).value || '';
      st.textContent = 'Saving...';
      try {{
        await db.collection('feedback').doc(form.dataset.id).set({{ choices: choices, note: note, savedAt: new Date().toISOString(), round: {json.dumps(ROUND)} }});
        st.textContent = 'Saved ' + new Date().toLocaleString();
      }} catch (e) {{ st.textContent = 'Could not save (' + (e && e.code || 'error') + '). Try again or reply in the terminal.'; }}
    }});
  }});
  (async function () {{
    try {{ db = window.claude ? await window.claude.use('db') : null; }} catch (e) {{ db = null; }}
    if (!db) {{ document.getElementById('offline').hidden = false; return; }}
    try {{
      const snap = await db.collection('feedback').get();
      const byId = {{}};
      snap.docs.forEach(function (d) {{ byId[d.id] = d.data(); }});
      forms.forEach(function (f) {{ fill(f, byId[f.dataset.id]); }});
    }} catch (e) {{}}
  }})();
  // subject filter
  const fbtn = [...document.querySelectorAll('.f')];
  fbtn.forEach(function (b) {{ b.addEventListener('click', function () {{
    fbtn.forEach(function (x) {{ x.setAttribute('aria-pressed', String(x === b)); }});
    document.querySelectorAll('.card').forEach(function (c) {{ c.hidden = !!b.dataset.s && c.dataset.subject !== b.dataset.s; }});
  }}); }});
  // lightbox
  document.querySelectorAll('.page').forEach(function (p) {{ p.addEventListener('click', function () {{
    const lb = document.createElement('div'); lb.className = 'lb'; lb.setAttribute('role', 'dialog');
    lb.innerHTML = '<button type="button">Close</button><img alt="Full-size page">';
    lb.querySelector('img').src = p.dataset.full;
    const close = function () {{ lb.remove(); document.removeEventListener('keydown', esc); }};
    const esc = function (e) {{ if (e.key === 'Escape') close(); }};
    lb.querySelector('button').addEventListener('click', close);
    lb.addEventListener('click', function (e) {{ if (e.target === lb) close(); }});
    document.addEventListener('keydown', esc);
    document.body.appendChild(lb); lb.querySelector('button').focus();
  }}); }});
}})();
</script>
'''
(ART / 'index.html').write_text(page)
(ART / 'files.json').write_text(json.dumps(files))
print(len(index), 'samples,', len(files), 'files')
