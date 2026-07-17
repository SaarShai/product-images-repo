# Experiment-1 conclusions (2026-07-17)

Staged hard-mask architecture (SYNTHESIS.md) tested end-to-end on the frozen
princess-n02 panel. 8 scored gens + 1 smoke, ~107s each Stage A / ~69-99s
Stage B, local MPS, $0 API. All measured, all raws preserved.

## What is now PROVEN (on this panel; claim ceiling = one panel, exemplar-conditioned)

1. **Geometry by construction works.** All 8 scored gens: 0 px outside
   silhouette, P1 holes 0.0% painted, coverage 99.89-99.99%. Versus the
   frontier prompt-route's frozen failure (iou 0.120, cutouts 71-98% painted).
2. **Content requires a composition scaffold.** Contour-only lineart →
   near-empty washes (round 1, 4/4). Selective structural trace of the frozen
   frontier exemplar (registered, clipped, geometry re-added) → full castle
   with towers/roofs/windows/gate (round 2, 2/2), geometry unchanged.
   Pre-registered decision rule fired correctly.
3. **Stage-B style refinement is drift-safe.** Same checkpoint/pipeline at
   strength 0.35/0.50: silhouette IoU vs base 0.9891 (gate >= 0.97 PASS),
   holes <= 1.14% pre-composite, style visibly lifted (brighter washes,
   decorative detail; delta 13.7/17.0 mean RGB — refinement, not rewrite).
4. **Socket composite-back exists and is byte-exact** (finding C closed at
   experiment scope): frozen RGBA arch matte (0 over-removed px), alpha-over
   paste — interior delta = 0, feather ring = deterministic blend exactly,
   alpha == frozen matte, corner integration 99.99% painted (wall reaches the
   arch; no pasted-card look). Real door seated in B-s21-d050/final.png.
5. **Pipeline runs cold on MPS** with fp16 + VAE-fp32-decode (via latent
   output), vae_slicing, CPU generator, watermark-ratio env. attention_slicing
   is INCOMPATIBLE with loaded IP-Adapter (processor conflict) — documented
   deviation.

## Open items (honest, none hidden)

- **Style ceiling vs frontier refs**: gens are muddier/dustier than the
  luminous frozen refs. USER is the arbiter (pairwise in REVIEW folder).
  Levers untried: higher IP scale/full routing, Stage-B engine swap
  (criterion-6 path), palette-bias prompt, upscale pass.
- **Registration gate**: appearance-based detection has a ~3.0-3.16px noise
  floor on real diffusion output (reg-tol 1.5 calibrated on synthetic edges)
  and mis-detects on painterly Stage-B candidates (flat washes merge into the
  blob). Paste-measuring gates all pass. Redesign decision pending
  (kimi-reggate.md consult): transform-provenance verification + junction
  crops, appearance demoted to advisory.
- **P2 arm punch path**: st2 bars painted-over as designed; bevel-punch
  validation deferred until the punch step is exercised on P2 (P1 needed no
  punch — holes were clean voids by construction).
- **Fold-band braid artifact** (R2/B, center fold): the 4px fold stroke
  renders as a braided seam. Round-3 fix: thinner/dashed fold stroke or
  exclusion from the control map.
- **Composition generalization**: exemplar-traced map only. Procedural/novel
  composition is a separate later round.
- **Production resolution**: 640x1544 working res; upscale-then-composite
  ordering is designed (upscale art BEFORE socket paste) but not yet run.

## Deviations from frozen card (all documented in-line)

attention_slicing OFF (IP-Adapter conflict); VAE fp32 at decode via
output_type="latent" (pipeline-internal encodes need fp16); multi-ref IP via
manual embedding averaging (diffusers 0.38 nested-list form is silently
broken — verified by shape check). Prompt: card-verbatim (the "cottage" file
was a never-read stray; scored runs verified via code path + meta.json).

## Verdict

Architecture VALIDATED at experiment scope: exact geometry + rich
exemplar-conditioned content + reference-driven style + byte-exact fixed
element, simultaneously, on one held-out panel, locally, $0. A frozen
evidentiary run (fresh contract, evidentiary-run skill) is the required next
step before any production/generalization claim.
