# SYNTHESIS — geometry adherence architecture (2026-07-17)

Inputs: inventory.md (repo, measured), sota-survey.md (external), sol-verdict.md
(GPT-5.6 Sol), kimi-verdict.md (Kimi K3, independent). Full agreement on the
core; one empirical disagreement; two additions from Kimi.

## Decision: staged hard-mask architecture (converged 4+1/4+2)

All four evidence lanes converge: geometry must hold BY CONSTRUCTION (hard
inpaint mask), composition-to-contour must be injected at GENERATION time
(ControlNet lineart with spires drawn to terminate at the top contour, elements
routed clear of holes/socket), style must enter as reference IMAGES
(IP-Adapter + watercolor LoRA). Guidance-only frontier gen is falsified
(iou 0.120); gen-loose+clip is falsified (re-seat 0.91 + erased controls +
rejected cut-look); region-map survives only as the composition INPUT.

Pipeline (engine slot swappable; start with localgen.py — local, $0, already
implements the stack but has ZERO full-panel measurements):

- **Stage 0 — composition plan.** From SVG spec: control lineart where top
  forms terminate/taper at the contour, major elements routed around holes +
  socket. This is where the truncated-spires defect class is solved.
- **Stage A — geometry-exact base.** SDXL inpaint, paintable mask per hole
  policy (below), canny CN on Stage-0 lineart, IP-Adapter on frozen refs +
  watercolor LoRA. Precedent: region-IoU 0.969-1.0 (controlnet_sdxl_gen).
- **Stage B — gated style re-render (optional).** img2img at denoise 0.35/0.5,
  SAME conditioning, gated vs Stage-A base: silhouette IoU ≥ 0.97 pre-cleanup,
  hole paint ≤ 2%. None pass → ship Stage A. Engine swappable to frontier
  img2img if SDXL style ceiling proven (criterion 6).
- **Stage C — mechanical guardrails, LAST raster ops.** Silhouette re-mask
  (1px feather) → punch holes + bevel → socket composite-back. Socket:
  original raster at native res, pasted with +1px dilated mask, 1px feather on
  the ART side only, interior byte-exact; upscale art BEFORE paste, never
  after. Gate = interior pixel-diff 0 AND explicit ≤1px registration/offset
  check (finding-B-class bug risk; needs fail-pre-fix fixture).

## The one disagreement → resolved empirically

- Sol: paintable = silhouette − holes − socket (hole violations impossible by
  construction).
- Kimi: paintable = silhouette − socket only; paint OVER holes, punch after the
  style pass — else hole islands get mismatched wash/lighting (the repo's
  recurring "assembled/collaged" failure). Elements still kept clear via
  Stage-0 routing + clearance gate; punch_holes.py bevel provides the
  "painted-framed opening" the user wants.
- Resolution: one Stage-A arm each. Cheap, discriminating, settles a
  pipeline default.

## New gate class (Kimi pre-mortem — adopt)

**Element-vs-cutout clearance gate**: minimum clearance between salient
elements and hole polygons. Silhouette IoU + hole-paint % both stay green while
a window crowds a slot — the princess-n02 "forbidden zone" defect recurs
one step removed. No current gate measures this. Required before any PASS.

Full gate battery per candidate: outside-silhouette 0px · hole paint (post-C)
0 · socket interior Δ=0 + registration ≤1px · clearance gate · composition
(no truncated primary element at contour, human overlay review) · style (blind
pairwise vs outset-c1, user judges) · junction crops at high zoom.

## Proposed experiment (NOT started — awaiting user authorization)

~6 local gens, $0 API, frozen princess-n02 inputs (comparable to the recorded
frontier failure):
1. Stage A × 2 seeds × 2 hole-policy arms (4 gens).
2. Stage B at denoise 0.35 + 0.5 on best base (2 gens).
3. Stage C on all; run full gate battery; blind pairwise style vs outset-c1.

Pre-registered decision rules (kimi-verdict.md Q3 table + Sol's gate table):
staging failure (drift) ≠ engine failure (style parity) — separated so one
can't be misread as the other. PASS here authorizes only a fresh frozen
evidentiary run, nothing more (claim ceiling).

Prereq check before spend: .venv-gen present, ~/models-gen weights (SDXL
inpaint, xinsir canny, IP-Adapter encoder, watercolor LoRA) — inventory notes
weights external.

## Claim ceiling

Nothing new validated. This document is a decided architecture + experiment
design, zero generations run.
