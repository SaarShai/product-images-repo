# PIPELINE — SVG → exact-geometry styled illustration

The staged, repeatable system that turns a user SVG template into a styled
illustration that fits the EXACT contour + cutouts, verified by
`scripts/svg_geometry_check.py`, with a pluggable structure-locked generation
backend so the winning method drops in without rewiring the loop.

## Why staged (the evidence)

Measured on `tasks/space-np01-front-bottom-02/` (4 openings, watercolor space
panel), every pure-prompt subscription route FAILs the mechanical gate:

| run | backend | mean_iou | max painted_frac | outside_frac | verdict |
|---|---|---|---|---|---|
| E5-bestof-1 | gpt-image best-of-N | 0.436 | 0.543 | 0.077 | FAIL |
| E1-filled-contract | gpt-image, filled base + preserve list | 0.371 | 0.519 | 0.084 | FAIL |
| E11-filled-freeredraw | gpt-image, free redraw (ablation) | 0.006 | 0.998 | 0.082 | FAIL |
| E2-filled-nano | Nano Banana | 0.000 | 1.000 | 0.066 | FAIL |
| HYB / `exact_bevel_composite.py` | model art + code-seated openings | →1.0 by construction | →0.0 | →0.0 | PASS |

Reading: prompt-only geometry control tops out ≈0.44 IoU and **never** clears
the hole-bleed tolerance; geometry must arrive as **pixels** (a control map /
filled base) and even then no single call locks placement (RESEARCH-SYNTHESIS
headline). The only routes that PASS the exact gate are (a) a structure-locked
generator scored by best-of-N until a candidate clears, or (b) the deterministic
`exact_bevel_composite.py` backstop. The pipeline therefore separates
**structure** (locked, verified) from **style** (model-owned) and makes the
generation backend a **pluggable interface** so the winner of the T1/T3/T6 race
slots into the same loop.

## The pluggable generation backend (the swap point)

Every stage is fixed EXCEPT Stage 3. The backend is a clean interface so the
winning method is the only thing that changes:

```
backend.generate(control_map, filled_base, style_packet, prompt, n, out_dir) -> [candidate.png, ...]
```

| backend id | how it locks structure | style source | exactness | status |
|---|---|---|---|---|
| `diffusers-controlnet` | SD + lineart/canny ControlNet conditioned on `svg_to_controlmap.py` output | prompt + (optional IPAdapter) | high (cond-scale locks edges) | T1, `controlnet_gen.py` exists |
| `comfyui` | ControlNet + IPAdapter graph, same control map | IPAdapter from style packet | high | T4, external graph |
| `gpt-image-refine` | filled base + restyle-only preserve list, best-of-N | reference attachments | medium (≈0.44 IoU ceiling) | T3b, `geom_adherence_test.py` |
| `hybrid-bevel` | model art, then `exact_bevel_composite.py` re-seats openings at exact SVG coords | model art + illustrated bevel ring | **exact by construction** | T2, `exact_bevel_composite.py` exists — **the backstop** |

Backend contract (all four already conform via existing scripts):
- **input**: `control_map.png` (from Stage 2a), `filled_base.png` (Stage 2b),
  `style_packet/` dir, a prompt file, `n` (candidate count), `out_dir`.
- **output**: ≥1 `candidate.png` written to `out_dir`, one per requested N.
- **no geometry claim**: a backend MUST NOT assert exact fit; Stage 5 is the
  only authority on geometry. (Mirrors the skill's "a mechanical pass is not
  approval".)
- the loop calls the backend by id; swapping the winner = changing one
  `--backend` flag, not the loop.

## Stages

Each stage: **input → output → tool/script → gate** (the gate is what must hold
before the next stage runs).

### Stage 1 — Parse + role-classify the SVG
- **input**: user SVG template (`source/template.svg`).
- **output**: `svg-geometry-report.md`, filled `template-manifest.json`
  (outer_contours / paintable_regions / internal_cutouts / keep_clear_zones /
  no_focal_motif_zones), labelled role-preview PNG.
- **tool**: `scripts/svg_classify.py <svg> --write-manifest --report R.md --preview P.png`
  (parser = `scripts/svg_geometry.py`).
- **gate**: `python3 scripts/svg_classify.py --check tasks/<task>/template-manifest.json`
  exits 0 (status set, `outer_contours` non-empty). A human eyeballs the preview
  and sets `status: approved` before any generation. **No later stage may run on
  an un-classified template.**

### Stage 2a — Control map (structure conditioning)
- **input**: classified SVG + manifest.
- **output**: `controlmap-lineart-WxH.png` (exact contour + every cutout as crisp
  strokes, white field; canny variant = inverted), at a pixel box matching the
  SVG aspect so it maps 1:1 to the verifier.
- **tool**: `scripts/svg_to_controlmap.py SVG --out MAP.png --width 512 --style lineart|canny`.
- **gate**: map non-empty; its viewBox→px mapping equals the
  `svg_geometry_check.py` mapping (same affine) so lines land where the verifier
  measures. (Asserted once in `pipeline_run.py` self-check.)

### Stage 2b — Filled base (for prompt-only backends)
- **input**: classified SVG + manifest.
- **output**: `genmap-filled.png` — outer contour + paintable filled neutral,
  openings as **solid** mid-grey discs at exact px (NOT line-art holes; the
  filled-beats-lineart lesson, RESEARCH rank #1).
- **tool**: `scripts/svg_classify.py SVG --map MAP.png` (negative-space map) →
  extend to a filled base. *(map exists; filled-disc variant is a NEW small
  script, see "New scripts".)*
- **gate**: every opening present as a solid region at its manifest bbox
  (overlay check). Only required when the chosen backend is `gpt-image-refine`.

### Stage 3 — STRUCTURE-LOCKED generation (pluggable backend)
- **input**: control map (2a) + filled base (2b, if used) + style packet +
  prompt + `n`.
- **output**: `cand_001.png … cand_NNN.png` in the round dir.
- **tool**: `scripts/pipeline_run.py --backend <id> --n N …` dispatches to the
  selected backend (`controlnet_gen.py` / ComfyUI client / `geom_adherence_test.py`
  generator / `exact_bevel_composite.py`). **NEW thin dispatcher.**
- **gate**: N images produced (non-empty, correct canvas/aspect). Liveness only —
  geometry is NOT judged here. A backend that produces 0 images is a hard fail
  the loop counts as a wasted round.

### Stage 4 — Auto-register candidate
- **input**: each raw candidate.
- **output**: candidate copied into the round dir with metadata; panel bbox
  auto-detected from the non-white region (same convention as
  `geom_adherence_test.auto_bbox`).
- **tool**: `scripts/register_result.py` / `auto_bbox` (both exist).
- **gate**: bbox detected (non-white region present); else the candidate is
  blank and dropped.

### Stage 5 — EXACT-SVG verify (the bottleneck)
- **input**: registered candidate + bbox + authoritative SVG.
- **output**: `metrics.json` per candidate (`mean_iou`, per-hole `painted_frac`,
  `outside_frac`, overall) + overlay PNG.
- **tool**: `scripts/svg_geometry_check.py CAND --svg SVG --bbox L,T,R,B
  --json-out m.json --out-overlay o.png` (exists). **Run by a separate scoring
  actor, never the generator** (`geom_adherence_test.py` already separates them).
- **gate**: this is THE loop gate (see `LOOP.spec`): `mean_iou ≥ 0.85`
  **AND** `max painted_frac ≤ 0.03` **AND** `outside_frac ≤ 0.02`.

### Stage 6 — Select / refine loop
- **input**: all candidate `metrics.json` in the round.
- **output**: the accepted candidate, OR a stronger next-round prompt /
  cond-scale bump, OR escalation to the `hybrid-bevel` backstop after the budget.
- **tool**: `scripts/pipeline_run.py` loop driver (ranks by `mean_iou` then
  `max painted_frac`, regenerates failures with a restated preserve list / higher
  ControlNet `--cond-scale`). **NEW driver — implements `LOOP.spec`.**
- **gate**: STOP when a candidate passes Stage-5 gate (accept) OR `N`=6 rounds
  exhausted → fall back to `hybrid-bevel` (exact by construction) so the pipeline
  always yields a geometry-passing deliverable.

### Stage 7 — Style judge + deliverable
- **input**: the geometry-accepted candidate + references + style packet.
- **output**: final artwork-only + overlay/clean-line exports under
  `outputs/final/`, judge verdict note.
- **tool**: `scripts/export_svg_template_fit.py … --require-pass`, then the
  `svg-template-review-judge` skill (a SEPARATE actor, inspects images, returns
  ACCEPT / LOCAL PATCH / PROMPT RESTART / BLOCKED).
- **gate**: geometry already PASSED at Stage 5; the judge gates **style** only.
  A geometry PASS is never style approval (skill anti-pattern: "calling a metric
  PASS production approval").

## Flow

```
SVG ─▶ [1 classify] ─▶ manifest+roles ─┬─▶ [2a control map] ─┐
        gate: --check                   └─▶ [2b filled base] ─┤
                                                              ▼
                                       [3 BACKEND.generate × N]   ◀── pluggable: controlnet|comfyui|gpt-image-refine|hybrid-bevel
                                                              │
                                                 [4 register + auto-bbox]
                                                              │
                                  [5 svg_geometry_check.py]  ◀── SEPARATE verifier actor
                                          metrics.json
                                                              │
                          ┌────── pass gate? ──── yes ───▶ [7 style judge] ─▶ deliverable
                          │           no
                          └─▶ [6 refine: stronger prompt / +cond-scale / regen] ─▶ back to [3]
                                          │  budget N=6 exhausted
                                          └─▶ [hybrid-bevel backstop] ─▶ exact by construction ─▶ [7]
```

## Where this plugs into the `svg-geometry-style-illustration` skill

The skill is the right **orchestration** spine; this pipeline hardens its loose
middle. Mapping:

- **Skill §2 (Geometry Agent: SVG → safe map)** — REPLACE the prose "produce a
  geometry report + roughs" with the mechanical Stage 1 + 2a/2b: `svg_classify.py
  --write-manifest --check` (gate) and `svg_to_controlmap.py`. Same outputs, now
  gated and deterministic.
- **Skill §4 (Choose the creative pass: Elements-First / Whole-Panel-Redraw)** —
  AUGMENT with Stage 3's pluggable backend. The redraw stops being "ask an image
  agent to redraw" and becomes "call the structure-locked backend with the
  control map / filled base" — the geometry no longer rides on prose.
- **Skill §5 (Exact SVG export and cleanup)** — AUGMENT: insert Stage 5
  (`svg_geometry_check.py` IoU/paint/outside gate) BEFORE export. The skill
  already says "a mechanical pass is not approval"; this names the exact gate and
  its thresholds, and adds the best-of-N select/refine **loop** the skill's §5 is
  missing.
- **Skill §6 (Review judge)** — KEEP unchanged as Stage 7. It now runs only after
  the geometry gate has passed, so the judge spends its attention on style, not
  re-checking geometry by eye.
- **New cross-cutting rule for the skill**: geometry is owned by Stages 1/2/5
  (code), style by Stages 3/7 (model + judge). The `hybrid-bevel` backstop
  guarantees the skill can always return a geometry-passing deliverable even when
  every pure-model round misses tolerance.

## Minimal new scripts to make it runnable end-to-end

Most of the pipeline already exists (`svg_geometry.py`, `svg_classify.py`,
`svg_to_controlmap.py`, `controlnet_gen.py`, `exact_bevel_composite.py`,
`geom_adherence_test.py`, `svg_geometry_check.py`, `register_result.py`,
`export_svg_template_fit.py`). The minimal NEW set:

1. **`scripts/pipeline_run.py`** — the loop driver implementing `LOOP.spec`:
   dispatches Stage 3 to a `--backend {controlnet|comfyui|gpt-image-refine|hybrid-bevel}`,
   runs Stage 4→5 per candidate, ranks by `mean_iou` then `max painted_frac`,
   stops on accept or `--max-iterations 6`, escalates to `hybrid-bevel` on budget
   exhaustion, writes a per-run ledger (iteration count, pass rate, failure
   reasons, cost — the loop-engineering "instrument before you scale" data).
   This is the ONE genuinely new component; everything else it calls exists.
2. **`scripts/make_filled_base.py`** (small) — Stage 2b: extend the existing
   negative-space `--map` render to draw openings as **solid mid-grey discs** at
   exact px (filled-beats-lineart). ~30 lines reusing `svg_classify.extract_shapes`.
3. **`scripts/backend_interface.py`** (thin) — the `generate(...)` adapter so all
   four backends share one signature and `pipeline_run.py` selects by id. Wraps
   the existing per-backend scripts; no new generation logic.

No new generation models or verifiers are needed — the verifier
(`svg_geometry_check.py`) and the exact backstop (`exact_bevel_composite.py`)
already exist; the new work is the driver that wires generator→verifier into the
closed loop below.

## Loop gate thresholds (full spec in `LOOP.spec`)

- **`mean_iou ≥ 0.85`** — accept threshold for opening-placement fidelity.
- **`max painted_frac ≤ 0.03`** — no opening more than 3% painted-over (the
  verifier's own per-hole `--cutout-tol` default).
- **`outside_frac ≤ 0.02`** — ≤2% of panel paint outside the contour (the
  verifier's built-in silhouette tolerance).
- **budget `N=6` rounds**, then escalate to `hybrid-bevel` (exact by
  construction) so a deliverable is guaranteed.

See `LOOP.spec` for justification and `loop_lint.py` validation.
