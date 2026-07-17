# Independent second opinion — geometry adherence architecture decision

Author: Kimi (independent advisor; no other advisor's answer seen).
Read-only consult; sole write is this file, per instructions.

## Q1 — The bet: hybrid 4+2, staged, with 5 demoted to a composition input and 3 demoted to a guardrail

**Architecture: staged pipeline — (i) hard-mask inpaint base with structural
composition conditioning, (ii) gated style re-render, (iii) mechanical
guardrails (punch + socket composite-back) as the last raster ops, (iv)
per-defect-class gates.**

Staged order:

1. **Composition plan (from arch 5, demoted).** Build the region map / layout
   sketch from the SVG + composition intent, with spire tips *drawn to meet the
   top contour*. Use it as a ControlNet structural condition (canny/softedge
   lineart), NOT as a frontier-gen guidance image. This is where
   composition-adaptation-to-contour is decided — the brief is correct that it
   is a generation-time property, so it must be injected at the earliest
   generation step, not hoped for from a loose gen.
2. **Stage A — geometry-exact base (arch 4 + arch 1's conditioning).** SDXL
   inpaint with the paintable mask = silhouette **minus socket only** (paint
   OVER the cutout holes — see pre-mortem bullet 2), plus canny ControlNet on
   the composition lineart, plus watercolor LoRA + IP-Adapter on the frozen
   reference images. Geometry holds by construction (measured precedent:
   region-IoU 1.0, holes empty). Style enters via reference IMAGES
   (IP-Adapter), satisfying the no-prose-style hard rule.
3. **Stage B — gated style re-render (arch 2).** img2img (or creative
   upscaler) on the Stage-A base at a swept denoise (~0.35 / 0.5), same
   IP-Adapter/LoRA conditioning, to lift painterly fidelity toward the
   frontier bar. Gate it *measured against the Stage-A base*: keep the
   highest-denoise variant whose pre-cleanup silhouette drift and hole drift
   stay under threshold (thresholds in Q3). If none pass, ship Stage A — a
   geometry-exact, slightly-less-painterly panel — rather than any violation.
4. **Stage C — mechanical guardrails (arch 3's tools, demoted).** Re-apply
   silhouette mask (1px feather), punch holes, composite the socket raster
   back (Q2). Because the art was *composed for the contour* in Stage A, these
   masks trim sub-threshold drift only — they do not chop a rectangular
   composition, so the rejected "cut at the boundary" look is not induced.

Why the losers lose:

- **Arch 3 as primary (gen-loose + enforce): already falsified by the measured
  facts.** Re-seat gave IoU 0.91 with erased fine controls, and the user
  rejects the cut-look defect class. Post-hoc masking cannot compose spires to
  a top edge. Its tools survive only as Stage-C guardrails on art that was
  already composed to the contour.
- **Arch 5 as the geometry mechanism: falsified.** Prompt+guide adherence on
  this panel class measured IoU 0.120 with 71–98% painted cutouts —
  systematic, not noise. Guidance-only cannot hold hard holes. Its real value
  is placement/proportion (Wanderland: 26%→5% registration distortion), which
  is why it survives as the Stage-1 composition input.
- **Arch 1 alone (soft ControlNet, no hard mask):** canny conditions but does
  not guarantee; the IoU-1.0 evidence comes from the *inpaint hard mask*, not
  the canny. Keep the canny, keep the mask, drop "one-stage, no hard mask."
- **Arch 2 alone without the hard-mask base:** a geometry-exact base is the
  anchor the style pass is gated against; without Stage A's construction-time
  guarantee there is nothing trustworthy to gate against.

The engine question (SDXL vs frontier style quality) is deliberately separated
from the architecture question: Stage B is a swappable engine slot. If SDXL
tops out below the style bar (Q3 experiment tests exactly this), swap Stage B
to a frontier img2img/edit-capable model while keeping the staged geometry
logic. Do not swap the architecture to chase an engine.

## Q2 — Socket composite-back design

**Principle: the socket is excluded from every generative step and restored
from the original raster as the final compositing operation. No model ever
touches door pixels.**

- **Mask source:** socket polygon parsed from the SVG (the same fixed parser
  that now handles `<rect>` + cutout paths post-40cbd70), rasterized with the
  identical coordinate transform used for the silhouette and hole masks, at
  both working and final-export resolutions. Single geometry source of truth;
  never hand-align.
- **At generation (Stage A and B):** socket zone is in the *unpaintable* mask
  at its exact polygon (erode 0–1px, no more). Fill the socket area of the
  conditioning canvas with a neutral surround-matched fill (mean of the
  adjacent wall colors, lightly blurred) so the inpaint model generates wall
  texture continuously right up to the boundary instead of hallucinating
  door-ish content at the rim.
- **At composite (Stage C, LAST raster op before gates — after the style pass,
  after any upscale/sharpen):** paste the **original door raster from its
  highest-resolution source**, transformed per the SVG, with the paste mask
  **dilated +1px outward** at final resolution and a **1px linear alpha
  feather at the rim that falls entirely on the art side**. Door interior
  pixels: byte-exact (the +1px dilation makes the door's own edge/frame cover
  the outermost ring of generated art, which is what hides the seam).
- **Why this reads intentional:** the door's own frame/bevel edge overlapping
  1px of art reads as the door's rim, not a paste line. If the door raster
  has no inherent frame and the junction gate flags a visible seam, add — on
  the art side only — a 2–3px contact-shadow ring at ≤10% multiply. Optional,
  conditional, never inside the polygon. (Repo precedent for bevel-aware
  compositing exists: `scripts/exact_bevel_composite.py`,
  `scripts/composite_window.py`.)
- **Ordering discipline:** compositing last is what makes "socket survives
  untouched" achievable at all — any style pass, upscaler, or sharpen running
  on a panel with the door already pasted drifts its pixels (this was finding
  C: violation by construction). Upscale the *art alone*, then paste the
  native-res door so it stays crisp.
- **Gate:** socket gate = (a) interior pixel-diff vs original: max |Δ| = 0
  inside polygon-minus-rim; (b) registration check: edge-alignment offset
  between pasted socket and SVG polygon ≤ 1px (catches transform bugs a
  pixel-diff alone can mask — see pre-mortem bullet 3); (c) human rim review
  on a junction crop at high zoom.

## Q3 — Cheapest discriminating experiment: 4 local gens on the frozen princess-n02 panel, $0

Reuse the frozen evidentiary inputs (template, socket raster, frozen style
refs, fixed gates) — same panel, same contract family, so results are
comparable against the recorded frontier failure (IoU 0.120).

1. **Stage A base** — hard-mask inpaint + composition-canny + watercolor LoRA +
   IP-Adapter(refs), paintable = silhouette − socket (holes painted over):
   **2 gens** (2 seeds).
2. **Stage B style pass** on the better base at denoise **0.35 and 0.5**:
   **2 gens.**
3. Run Stage C (silhouette re-mask, punch, socket composite-back) on both
   Stage-B outputs and on the Stage-A base (control).

Pre-registered measurable pass/fail:

| # | Metric | PASS | FAIL meaning |
|---|--------|------|--------------|
| 1 | Post-cleanup silhouette IoU (all 3 outputs) | ≥ 0.99 | Stage-C tooling broken (should be ~1.0 by construction — a FAIL here is a pipeline bug, not an architecture signal) |
| 2 | **Style-pass drift**: silhouette IoU of Stage-B output vs Stage-A mask, *before* cleanup | ≥ 0.97 at denoise 0.35 | Two-stage img2img re-composes at boundaries → arch 2 dead; fall back to arch-4-pure (heavier style conditioning in one pass) |
| 3 | Pre-punch hole paint %, Stage-B output | ≤ 2% | Style engine ignores structure internally → cap denoise or change engine |
| 4 | Socket interior max pixel Δ after composite-back | = 0 | Composite-back implementation bug (fix code, not architecture) |
| 5 | Composition-adaptation: truncated primary elements at top contour (human, overlay review) | 0 | Composition-conditioning insufficient → strengthen Stage-1 lineart (draw spires to edge), not more prompt |
| 6 | Style: blind pairwise vs frozen frontier attempt (outset-c1, style-PASSED), user judges | parity-or-better on ≥1 variant | SDXL+LoRA+IP-Adapter style ceiling on full panels → swap Stage-B engine to frontier img2img/edit; staged architecture stands |

Why this falsifies the losers: arch 3 needs no re-spend (re-seat's 0.91 +
erased controls + the rejected cut-look already falsify it; add one frontier
gen-loose+punch control only if that verdict is disputed). Arch 5-as-geometry
is falsified by the frozen run's 0.120. Arch 1-without-hard-mask is falsified
by construction logic + the measured evidence that the hard mask is what
delivered IoU 1.0. The experiment therefore discriminates among the survivors:
it separates **staging** (criterion 2) from **engine** (criterion 6) so a
style shortfall can't be misread as an architecture failure, and vice versa.

**Claim ceiling:** one panel = one data point. A PASS here authorizes only a
frozen evidentiary run under `skills/evidentiary-run/SKILL.md`; a tuned
denoise value is a per-panel knob until it survives that freeze.

## Q4 — Pre-mortem (3 bullets)

- **Style-pass *internal* composition migration.** img2img at a denoise high
  enough to change style can also move elements: a window drifts into
  adjacency with a slot keep-clear while silhouette IoU and hole-paint
  metrics stay green (the hole is still punchable — the window just crowds
  it, recreating the "window in the forbidden zone" defect one step removed).
  No current gate measures element-vs-cutout clearance. Add one (region-map
  adherence / minimum-clearance metric) before any PASS claim, or this ships
  silently.
- **Cutout-island wash discontinuity.** If the paintable region is
  silhouette − holes − socket, the holes split it into disconnected islands;
  inpainting tends to give islands mismatched wash, lighting, and paper
  texture — the assembled/collaged look this repo has repeatedly failed on.
  Default to painting OVER the holes (paintable = silhouette − socket) and
  punching only after the final style pass, so wash continuity spans the
  hole zones. This is a pipeline-default decision, not an aesthetic tweak.
- **Socket rasterization registration bug (finding-B class).** The
  composite-back/punch path is new code with the same rect-vs-path and
  transform-matrix surface that produced the structural false-positive gate;
  add working-res → export-res scaling through an upscaler and a silent 1–2px
  offset is plausible. Symptom: door pasted off-register, reads as a double
  rim, while an interior-only pixel-diff gate still reports green. The socket
  gate must include an explicit offset/registration check (Q2), with a
  fail-pre-fix fixture, before the step is trusted.
