# TASK PACKET — Outset-cutout styled illustration for `np02-front-bottom 02.svg`
**Packet id:** packet-2026-06-17-space-np02-front-bottom-02 (rev2 — validated method)
**Mode:** dry_run_first: true (report plan + confirm the geometry report matches this packet before generating)
**Budget:** generate ~6–8 source raws; pick the best by EYE. Same defect twice on the same setup → STOP, report.

## Authorization
- May create + edit: everything under `tasks/space-np02-front-bottom-02/**` (you create this dir).
- May run: `scripts/subgen.py --health`, `scripts/svg_geometry_report.py`, `scripts/outset_cutouts.py`,
  `scripts/build_trueaspect_base.py`, `scripts/geom_adherence_test.py` (nano image-gen).
- Commit / push: no.
- Anything not listed = NOT authorized → report "AUTHORIZED BOUNDARY REACHED" and stop.

## Operating mode
Work autonomously until complete or a stop rule fires. Ground every claim in a tool result
from THIS run; never report a step you didn't execute. NEVER judge an opening from a metric
number alone — LOOK at the raw with your own vision. If your last line is a promise, do it first.

## TWO HARD RULES (user-confirmed — do not violate)
1. **Never ruin a good raw.** The raw may or may not be the final deliverable — but you must
   NEVER destroy or degrade it. Keep every `raw.png` untouched as a separate first-class file.
   Do NOT run `exact_bevel_composite.py` / produce an `exact.png` that overwrites or supersedes
   a good raw — that re-seat step carves openings + paints bevel bands + erases nearby hardware
   and visibly DEGRADES it. For this task the best raw IS the intended result; any further step
   must be non-destructive to the raw.
2. **Outset the cutouts via the SVG, not the prompt.** Painted cutouts drift; the empty
   paper-white area must be LARGER than the true cutout so the real die-cut always lands in
   empty paper. Do this by buffering the SVG cutouts outward (pixels in the contract base),
   NOT by asking the model in prose (prompt-only outset is unreliable — it oversizes or
   merges openings). The real cut still uses the ORIGINAL SVG.

## Context
- Goal: ONE bright watercolor space control-panel illustration whose CUTOUTS are clean empty
  paper with a generous outset margin, in the reference style, fitting `np02-front-bottom 02.svg`.
- Why: a panel in the Screenery "space" collection. Cuts are real die-cuts (hence the outset
  drift-safety); style must match the cobalt watercolor reference set.
- Sibling reference (the proven, user-accepted run): `tasks/space-np01-front-bottom-01/`
  — read `experiments-outset/OUTSET-COMPARISON.md` and look at
  `experiments-outset/OUTSET-A-o30-s1/raw.png` (the kept result) before starting.
- Skill: `skills/svg-geometry-style-illustration/SKILL.md` → "Validated Lessons" section.

## Target identity
- Source SVG: `/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/space/svg-exports/np02-front-bottom 02.svg`
- Style references (copy from the sibling task):
  - `tasks/space-np01-front-bottom-01/refs/ChatGPT Image Jun 9, 2026, 11_17_34 PM.png`
  - `tasks/space-np01-front-bottom-01/refs/ChatGPT Image Jun 9, 2026, 11_19_45 PM.png`
- Geometry of np02-02 (CONFIRM with the report; differs from np01-02's 3-hex layout):
  viewBox `789.66 x 2622.39` (~1:3.32). **TWO openings**:
  - ONE round knob/port (~x449–591, y1142–1284) — upper-middle, RIGHT of panel center.
  - ONE long tapered curved vertical slot (~x447–592, y1386–2438) — LOWER half, BELOW the
    knob, narrowing downward. Top edge has the small V-notch. Same opening vocabulary as
    np01-front-bottom 01 (1 circle + 1 slot), positions/orientation differ.

## Operation — exact steps
Run from repo root. `T=tasks/space-np02-front-bottom-02`.

**0. Health:** `python3 scripts/subgen.py --health` → expect `{'openai':'ok','nano':'ok'}`. nano down → STOP.

**1. Scaffold:**
```
mkdir -p $T/{source,refs,experiments-outset,outputs/generated,prompts,RESULTS}
cp "/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/space/svg-exports/np02-front-bottom 02.svg" "$T/source/template.svg"
cp tasks/space-np01-front-bottom-01/refs/*.png $T/refs/
```

**2. Geometry report (gate):**
`python3 scripts/svg_geometry_report.py $T/source/template.svg --out $T/svg-geometry-report.md`
— confirm 2 inner openings (1 circle + 1 long slot). If count/kinds differ from this packet → STOP and ask.

**3. OUTSET the cutouts (the key step):**
`python3 scripts/outset_cutouts.py $T/source/template.svg --out $T/source/template-outset30.svg --outset 30`
Default outset = **30** user-units (user-confirmed pick on the sibling panel). Verify with a
geometry report on the outset SVG that each opening's bounds grew by ~30 on every side and the
outer contour is unchanged.

**4. Build the contract base from the OUTSET SVG (= "image 1"):**
`python3 scripts/build_trueaspect_base.py --svg $T/source/template-outset30.svg --out $T/outputs/generated/np02-fb-02-base-outset30-1440x2560.png`
— OPEN it: the two grey holes should be enlarged and sit where the report says (knob above, slot below, right-of-center).

**5. Write the layout-contract prompt** `$T/prompts/BoN-nano-letterbox-02.md`.
Start from `tasks/space-np01-front-bottom-01/prompts/BoN-nano-letterbox-01.md` (closest
sibling — same 1-circle+1-slot vocabulary) and edit ONLY the LAYOUT CONTRACT bullets to
np02-02's arrangement: panel height ≈ 3.3× width; ONE round port upper-middle toward the
RIGHT; ONE long tapered slot in the LOWER half below the knob, narrowing downward; V-notch in
the top edge. Keep the STYLE / OPENINGS / DO-NOT blocks verbatim (panel-independent). Do NOT
add prose outset instructions beyond a mild "keep hardware clear of the openings" — the outset
is already baked into the base. The reference IMAGES are the single source of truth for the
look and are passed as attachments.

**6. Generate ~6–8 source raws (nano, serial, race-safe):**
Copy `tasks/space-np01-front-bottom-01/experiments-outset/_outset_test.sh` as a template (or
the simpler per-cell loop in `_o30_more.sh`); repoint `T`, base = the outset30 base, prompt =
your np02-02 prompt, svg = `template-outset30.svg`. Each cell: `geom_adherence_test.py
--model nanobanana --map BASE --prompt PROMPT --refs ref1 ref2 --svg SVG --outdir $T/experiments-outset`.

**7. PICK the best raw by EYE.** Criteria: both openings are clean empty paper, each FULLY
enclosed by its own bevel rim (no painted top/edge poking past the rim), generous even outset
margin all around, openings stay SEPARATE (not merged), bright cobalt + colorful tick-marked
controls + clean white bg + white side margins matching the references. A single bad raw (slot
top overlap, oversize, merge) is variance — regenerate a few more and pick a clean one. Do NOT
post-process a bad raw.

**8. Promote** the chosen raw to `$T/RESULTS/` and copy ALL result raws into the central
folder `tasks/space-np01-front-bottom-02/RESULTS/Images/` prefixed `np02-02__<id>__raw.png`.

## Acceptance criteria
- PRIMARY deliverable = the best `raw.png`. No `exact.png` / re-seat used.
- Both cutouts: clean empty paper, fully bevel-enclosed, separate, with a visible outset
  margin (cut-safe under drift). Verified by EYE.
- Style matches the references (bright, colorful, tick-marked knobs, clean white bg + margins).
- Only `tasks/space-np02-front-bottom-02/**` (+ central Images copies) touched.

## Exclusions
- Do NOT run `exact_bevel_composite.py` or any re-seat as the deliverable path.
- Do NOT modify `scripts/**` or other task dirs.
- Do NOT drive `codex`/`agy` by hand — only via `geom_adherence_test.py` / `subgen.py`.
- Do NOT outset via prompt prose; do NOT post-process a bad raw.

## Evidence to return (REQUIRED)
1. Paths created (the task dir tree + central Images copies).
2. Commands run + key output quoted: `subgen --health`, geometry report (orig + outset),
   `outset_cutouts.py`, `build_trueaspect_base.py`, the generation driver.
3. The chosen raw + 2–3 alternates, with a sentence each on what you SEE (openings clean,
   bevel-enclosed, margin present, style match) — vision, not metrics.
4. Self-report: which raw won and why; any defects seen and how many regens it took; uncertainties.

## If ambiguous
- Geometry report differs from this packet (count/kind/position) → STOP and ask.
- After ~8 raws none has both openings clean + bevel-enclosed + separate → report the best,
  show the defect, ask whether to raise/lower `--outset` or regenerate. Same setup failing the
  same way twice → STOP.

## Return report — head it "READY FOR JUDGING" (never "done/verified")
Steps taken · commands verbatim + why · decisions at ambiguities + assumptions · attempts
abandoned (approach→outcome→why) · which raw chosen + why (what you SAW) · uncertainties/
deviations · final state (path to chosen raw + central copies).
