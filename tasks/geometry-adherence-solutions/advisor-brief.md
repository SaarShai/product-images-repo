# Advisor brief — geometry adherence architecture decision

You are a frontier advisor. Read-only consult; do NOT edit files. Return your
answer as plain markdown text.

## Problem
We generate watercolor-style artwork that must fit an SVG die-cut template
EXACTLY: stay inside the outer silhouette, keep internal cutout holes (slots,
rects) 100% clean, respect a fixed-element "socket" (an embedded door raster
that must survive untouched), and adapt composition to the contour (no
truncated spires at the top edge). Simultaneously the art must strongly match
reference watercolor style images.

## Measured facts (do not re-litigate)
- Prompt + outset keep-clear guide + frontier gen (gpt-image/nano-banana):
  geometry FAILS systematically — mean silhouette IoU 0.120, cutouts painted
  71-98% on both candidates of a frozen evidentiary run.
- SDXL-inpaint + canny ControlNet on SVG lineart: region-IoU 1.0, holes empty.
  Weakness: painterly style fidelity below frontier gens.
- "Re-seat" (warp/composite a good frontier gen into exact geometry): IoU 0.91,
  gorgeous body, but erases fine controls; last-resort.
- Local SDXL + watercolor LoRA + IP-Adapter style ref: competitive quality AND
  free (validated on element edits, not yet on full panels).
- Hard rule: style must be driven by reference IMAGES as model inputs, never
  prose descriptions.
- Missing workflow step (finding C): no socket-masking + composite-back of the
  embedded raster; any full-panel gen "violates" the socket by construction.
- Per-defect-class gates required: outside-silhouette, cutout-painted,
  socket-violated, edge-truncated-composition, plus style-match (human/pairwise).

## Candidate architectures
1. One-stage: ControlNet geometry conditioning + style conditioning
   (IP-Adapter + watercolor LoRA) in one gen.
2. Two-stage: geometry-exact base via ControlNet, then style re-render pass
   (creative upscaler / img2img at tuned denoise) gated by measured
   silhouette-IoU against the base.
3. Gen-loose with best-style frontier model, then mechanical enforcement:
   silhouette mask, punch holes, composite socket back. Risk: art looks CUT at
   boundaries instead of composed for them (a defect class the user rejects).
4. Hard-mask inpainting (Flux Fill / SDXL inpaint): paintable region only is
   generated; geometry holds by construction; style via reference conditioning.
5. Region-map semantic color guide + frontier gen (guidance-only; weakest
   evidence).

## Questions (answer all, be decisive)
1. Which architecture (or hybrid, staged order) do you bet on and why? Consider
   that composition-adaptation-to-contour (spires meeting the top edge
   gracefully) is a GENERATION-time property that post-hoc masking cannot add.
2. Design the socket composite-back step: at what pipeline stage, what mask
   dilation/feather, how to blend so the socket edge reads intentional.
3. What is the cheapest single discriminating experiment (one panel, few gens)
   that would falsify the losing architectures? Define its measurable
   pass/fail.
4. Any failure mode we're not seeing (pre-mortem, 3 bullets max).
