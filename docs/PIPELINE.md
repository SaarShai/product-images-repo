# PIPELINE — the end-to-end lifecycle spine (source of truth)

One image task = one pass through these stages. Stage 0 is universal; stages 1–5
are **conditional** and chosen by the task type decided in Stage 0. Each stage
emits a **reviewable artifact** and passes a **gate** before the next stage runs.
This doc is the index; per-family detail lives in the linked docs.

> Why this exists: work was fragmented across 14 per-family workflow docs and the
> only intake (`scaffold_template_task.py`) assumed an SVG template. Tasks with no
> template (e.g. `berlin-hotel-base`) had no front-of-pipeline plan and went
> reactive for 16 repair waves. The spine forces an upfront plan + reviewable
> gates so the back of the pipeline doesn't explode.

---

## Core laws (apply at every stage — never re-derive)

1. **Reference beats prose.** Drive generation with reference IMAGES (+ geometry),
   never description alone. Missing reference ⇒ generate it as a precursor (1c).
2. **Geometry by construction, not by hope.** Exact layout is locked by SVG raster
   /ControlNet/composite, never by asking a model to paint coordinates.
3. **SVG is coordinate authority.** Overlay aspect, panel widths, cutout positions
   come from the SVG viewBox — not a raster preview.
4. **Metrics lie → vision judge mandatory.** region-IoU/white-IoU are hard gates,
   but a passing number is never acceptance; look at the overlay.
5. **Never ruin a good raw.** Keep best-so-far as a checkpoint; re-seat/composite
   is last resort, gated by non-regression.
6. **Show full-size, all candidates.** Never decide style/sharpness from a low-res
   board. Review every candidate at full res.
7. **Separate generation-mask from blend-mask** for repeated architecture; restore
   protected zones from baseline; outside-mask pixel delta == 0.
8. **Art-first for MOVABLE internal cuts (user-confirmed, cap-juluca 2026-06-24).**
   The panel *silhouette* stays authoritative (law 3), but *movable* internal die-cuts
   (door flaps, repositionable openings) may ADAPT to approved artwork rather than the
   reverse — when the user approves the art, move the cut to the art. Confirm per task;
   never silently relocate a fixed cut. Always run the contour-overlay fit check first
   (Stage 3) so the art-vs-cut deviation is *seen*, not guessed.

---

## STAGE 0 — INTAKE & PLAN  *(universal; the "from scratch" stage)*

**Input:** a description + references (+ optional SVG template + optional base image to edit).
**Does:** classify the task type, extract requirements into a ledger, inventory &
validate references (flag missing ones for 1c), decide which downstream stages
apply, draft the staged plan with per-stage gates.
**Reviewable artifact:** `tasks/<task>/BRIEF.md` (universal brief) + `PLAN.md` (stage plan) + `asset-manifest.json`.
**Gate:** human reviews the plan + reference inventory before any spend.
**Tooling:** `scripts/intake.py` — universal: classifies family (A–F), inventories
inputs (dims), emits BRIEF + PLAN + asset-manifest with only the applicable stages.
`scaffold_template_task.py` remains the template-only legacy path. Also: `requirements-ledger`,
`reference-style-packet` skills.
**Status:** ✓ built+verified 2026-06-24 (all 6 families classify; D/A proven end-to-end).

### Task-type router (decides which stages run)

| Task family | Has geometry? | Stages | Canonical doc/skill |
|---|---|---|---|
| **A. SVG-template / die-cut panel** | yes | 0·1a·1b·2·3·4·5 | `docs/svg-template-illustration-workflow.md`, `svg-geometry-style-illustration` |
| **B. Skyline / multi-panel** | yes | 0·1a·1b·2·3·4·5 | `docs/skyline-template-illustration-workflow.md`, `skyline-template-illustration` |
| **C. Free illustration (no template)** | no | 0·1a·(1c)·2·3·(4) | (uses 2–4 only) |
| **D. Finished-illustration repair/refine** | no | 0·(1a)·4·(3) | `wiki/concepts/mask-bounded-external-redraw-donor.md`, `element-edit` |
| **E. Element-edit (one element, rest byte-exact)** | no | 0·4 | `skills/element-edit/SKILL.md`, `docs/IMPROVED-PIPELINE.md` |
| **F. Upscale / enhance only** | no | 0·4(upscale) | `scripts/upscale.py`, `reupscale.py`, `adaptive_sharpen.py` |

---

## STAGE 1 — CONSTRAINT PREP  *(parallel sub-stages, conditional)*

### 1a. References → Style Packet  *(almost always)*
**Does:** turn raw refs into attachable visual evidence (contact + exemplar sheets).
**Artifact:** `tasks/<task>/style-packet/`.
**Gate:** human confirms the packet captures the actual art style (object vocabulary,
line weight, density, lighting, material — not just palette).
**Tooling:** `scripts/build_reference_style_packet.py`; `reference-style-packet` skill.

### 1b. Geometry  *(template/die-cut tasks only — A, B)*
**Does:** parse SVG → role-classified contract → build the geometry guide image
(grey-body / coordinate-true lineart) fed to the model, + reviewable overlays.
**Artifact:** `svg-geometry-report.md`, `template-manifest.json`, geometry-guide PNG.
**Gate:** guide aspect == panel aspect; cutout coords verified against SVG.
**Tooling:** `svg_geometry_report.py`, `build_trueaspect_base.py`, `outset_cutouts.py`,
`skyline_panel.py`; `svg-template-illustration` skill.
**Open:** unifying exact-geometry + full watercolor style + painted rims in one pass (still open).

### 1c. Generate MISSING references  *(precursor, when needed)*
**Does:** if a needed reference doesn't exist (e.g. a clean full building plate),
generate it FIRST as its own mini-task, then feed it downstream.
**Artifact:** the generated reference image, logged as a ref.
**Gate:** human approves the precursor before it's used as an anchor.

---

## STAGE 2 — GENERATION  *(your "styling")*

**Does:** produce candidates — multi-model × multi-prompt × **≥3 attempts/variant**,
fed with references (1a) + geometry guide (1b). Prioritize multiplicity over one-shot.
**Artifact:** candidate set + labeled contact sheet (full-size links, not just thumbnails).
**Gate:** deterministic (geom_gate, text_gate) → then Stage 3.
**Tooling:** `subgen.py` (OpenAI + Nano Banana), `falgen.py` (Flux Fill/Kontext/Flux.2),
`falbatch.py` (parallel fan-out), `run_matrix.py` (experiment matrix), `scout.py`,
local `controlnet_*` / ComfyUI. Candidate engines per task in Stage-4 routing table.
**Rule:** never put geometry words (SVG, contour, red zone, saloon-arch…) in the prompt.

**PROVEN recipe — Family A architectural watercolor panel (cap-juluca 2026-06-24):**
geometry guide (cream silhouette + element zones, built from real SVG path data via
`rsvg-convert`) fed as image-1 + real photo refs + watercolor prose → strong result on
attempt 1, no watercolor reference needed. **openai (`subgen.py --provider openai`)** is
the engine for polished architectural watercolor; **nano is too loose/sketchy** for this
stage. Render guides with `rsvg-convert -w N -b white` (installed 2026-06-24; the only
working SVG renderer here — `svg_geometry_report.py` hangs on complex multi-panel SVGs).

---

## STAGE 3 — SELECT / GATE

**Does:** deterministic hard-gates → vision judge → **human picks from all candidates at full size**.
**Artifact:** `judge.json` per candidate + a full-size comparison board.
**Gate:** region-IoU ≥ 0.85 (template) · outside-mask delta == 0 (edit) · text-gate clean ·
vision judge over the SVG overlay · human final pick.
**Tooling:** `judge.py`, `geom_gate.py`, `text_gate.py`, `style_board.py`,
`dup_detect.py`; `result-vision-judge`, `svg-template-review-judge` skills.
**Rule:** a passing metric is NOT acceptance (law 4); show full-size (law 6).
**MANDATORY contour-overlay fit check (cap-juluca 2026-06-24):** render the real die-cut
paths (outer silhouette + internal cuts like door flaps + keep-clear slots) as colored
strokes over the candidate at matched aspect (`rsvg-convert` the cut paths → PIL
alpha-composite). cap-juluca proved a candidate can look perfect yet have painted elements
badly misaligned with the die-cut — invisible on the bare image, obvious on the overlay.
Never approve a die-cut panel without it. **Sequencing (the real cap-juluca miss):** the
overlay is part of the board the agent BUILDS — present every die-cut candidate WITH its
contour overlay AND the fed inputs (geometry guide + refs), proactively. Do not present a
candidate as "good" and wait for the user to ask "did you check the outline?" — they had to.

---

## STAGE 4 — REPAIR / REFINE

**Does:** fix specific elements without disturbing the rest; remove ghosts; harmonize
sharpness across the composite; upscale. This is where the berlin-hotel family lives.
**Artifact:** refined image + before/after + outside-mask delta proof.
**Gate:** outside-mask pixel delta == 0 · leak_metric < 0.06 · vision judge · human.
**Tooling:** `edit.py` (one-command: automask→guardrail→engine→diff-gate→judge),
`falgen.py --mode eraser` (Bria), `compose_fairy.py`, `automask.py`, `mask_check.py`,
`upscale.py`/`reupscale.py`/`adaptive_sharpen.py`; `element-edit`, `baci-template-fit-repair` skills.

### Engine routing (Stage 4 — don't re-derive)
| operation | engine |
|---|---|
| remove an element | Bria eraser (`falgen.py --mode eraser`); `--free` = local LaMa |
| redraw in place | Flux Fill (masked) |
| restyle + layout | Flux.2 / `gen_styled.py` |
| reshape element | stretch-then-Kontext |
| edit existing text | `qwen_edit.py` |
| exact-geometry redraw | `controlnet_sdxl_gen.py` |
| same element ×N (consistency) | reference-lock (Flux.2 image_urls / IP-Adapter) |
| broad ghost/haze/occlusion in a busy scene | **mask-bounded external redraw donor** (OpenAI via subgen) |

**Open problems (highest-value to solve):**
- **Sharpness harmonization** across edited vs un-edited regions of a composite — *unsolved*.
- **Reliable single-element regen-and-composite** into a busy watercolor scene (current path seams).
- **Integration** — standalone plates look great; inserting them is what breaks.
- Pilots flagged by research: **Qwen-Image-Edit-2509** (open, native ControlNet+multi-ref) and
  **ComfyUI Flux-Fill + Differential Diffusion** (seamless mask blend).

---

## STAGE 5 — FINALIZE / EXPORT

**Does:** composite artwork into the template at exact SVG coords, verify fit, deliver,
log every result image into the central library.
**Artifact:** final export + fit-verification + results-library row.
**Gate:** 0 painted pixels outside template/cutout masks · fit verified · results synced.
**Tooling:** `export_svg_template_fit.py --require-pass`, `compose_fairy.py`,
`exact_bevel_composite.py`, `register_result.py`, `results_db.py`, `sync_results_images.py`.
**Rule:** never let an exact-composite supersede a good raw (law 5).

---

## Stage gates summary (the contract)

| Stage | Reviewable artifact | Hard gate |
|---|---|---|
| 0 Intake | BRIEF.md + PLAN.md + asset-manifest | human reviews plan + refs |
| 1a Style packet | style-packet/ | human: captures real style |
| 1b Geometry | geometry report + guide | aspect==panel, coords verified |
| 2 Generation | candidate set + contact sheet | deterministic gates pass |
| 3 Select | judge.json + full-size board | metric + vision judge + human pick |
| 4 Repair | refined + before/after | outside delta==0, leak<0.06, judge |
| 5 Export | final + fit report | 0 outside-mask px, results synced |
