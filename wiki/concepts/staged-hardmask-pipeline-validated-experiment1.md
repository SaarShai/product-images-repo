---
schema_version: 2
title: "Staged hard-mask pipeline delivers geometry+content+style+socket simultaneously (experiment-1, princess-n02)"
type: fact
domain: "image-generation"
tier: tactical
confidence: 0.85
trust: verified
scope: this-repo
created: "2026-07-17"
updated: "2026-07-17"
verified: "2026-07-17"
sources:
  - tasks/geometry-adherence-solutions/experiment-1/CONCLUSIONS.md
  - tasks/geometry-adherence-solutions/experiment-1/PARAMS.md
  - tasks/geometry-adherence-solutions/experiment-1/runs/RESULTS-round2.md
  - tasks/geometry-adherence-solutions/SYNTHESIS.md
supersedes: []
superseded-by: []
contradicts: []
tags:
  - geometry
  - svg-template
  - controlnet
  - ip-adapter
  - composite-back
  - gates
---

# Staged hard-mask pipeline delivers geometry+content+style+socket simultaneously

## Summary

On the same panel where the frontier prompt-route failed (iou 0.120, cutouts
71-98% painted), the staged local pipeline — SDXL-inpaint hard mask + canny CN
composition map + IP-Adapter(style-layer-only, multi-ref) + watercolor LoRA →
gated low-denoise style pass → punch/composite-back — produced full castle
panels with 0 px outside silhouette, 0.0% hole paint, byte-exact door
composite (delta=0, corner integration 99.99%), locally on MPS, ~107s/gen, $0.
Entry: tasks/geometry-adherence-solutions/experiment-1/ (scripts
gen_stage_a.py, build_composition_map.py, composite_back.py; frozen card
PARAMS.md + 5 amendments).

## Key mechanisms (each was load-bearing)

1. Geometry via hard inpaint mask + outside-pin composite = violations
   impossible by construction; CN guidance alone does not guarantee.
2. Content REQUIRES an interior composition scaffold: contour-only lineart →
   empty washes; selective structural canny trace of a style-PASSED frontier
   exemplar (registered per-axis, clipped by paintable, SVG strokes re-added)
   → full castle. Dense map needs CN lowered (0.55, end 0.65) or lines emboss.
3. Fixed-element socket: exclude an ARCH-SHAPED (alpha-matte) footprint from
   paintable — not the raster's white-bg rect (rect pins fill into corners =
   pasted-card look); neutral-fill the arch in init; draw the arch outline in
   the control map (model paints a frame); alpha-over composite the frozen
   RGBA back as the LAST raster op. Byte-exact + corner-integration gates.
4. Registration gate must be transform-provenance (independent re-derive +
   hash), NOT appearance-detection: real diffusion output has a ~3px
   edge-softening noise floor and painterly candidates false-positive
   appearance detectors (flat washes merge with the neutral zone).

## MPS/diffusers-0.38 traps (verified)

attention_slicing incompatible with loaded IP-Adapter (processor conflict);
VAE fp32 must happen at decode only (output_type="latent" then manual decode);
nested multi-ref IP form [[r1,r2]] silently produces malformed embeddings —
use manual encode_image averaging; kept regions tint ~60-70/255 via VAE
roundtrip.

## Claim ceiling

One panel, exemplar-conditioned composition. NOT yet: composition
generalization, production resolution, P2 punch path, frontier-style parity
(user arbiter). Next required step before production claims: fresh frozen
evidentiary run per skills/evidentiary-run/SKILL.md.

## Related

[[geometry-adherence-needs-mechanical-enforcement-princess-n02]] ·
[[regate-failed-artifacts-after-gate-patch]] · gate-per-visible-defect-class
(memory) · reference-beats-description (memory)
