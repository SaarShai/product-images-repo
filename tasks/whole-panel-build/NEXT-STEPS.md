# Blueprint — next steps (for independent expert review)

## Where we are
Building a repeatable workflow to generate "whole-panel" die-cut-fitting illustrations from an SVG
template (cut contour + cutouts/holes + keep-clear + fold lines + top-contour + optional FIXED embedded
element). Validated so far on space panel-3 (geometry+style generalization) and princess panel02
("with window"): chose winner cA1, enlarged the embedded window to geometry-true size via framing-locked
gen-EDIT (B1) and geometry-opening REGEN (C2); hardened the VLM judge (hi-DPI tiles, objective/aesthetic
split, NEW element-count gate counted on the whole-panel context).

## Proposed next steps
- **Step 1 — Lock princess-window final** (B1 vs C2) + emit the production deliverable: full-bleed raster
  at print resolution + a die-cut verification preview (internal only).
- **Step 2 — GENERALIZE the pipeline on the NEXT real design** (ideally a non-castle geometry, with
  cutouts/holes and/or a different fixed element): geometry intake (mask_to_svg) → geometry guide →
  multi-approach gen fan-out (Law 0) → objective gate (geometry hard-gate + count + edges) → fix →
  human pick. Goal: prove it generalizes beyond princess/castle.
- **Step 3 — HARDEN into a repeatable SOP + tooling** from the review adoptions: gold/regression set,
  code-based geometry hard-gate (edge-IoU vs mask before VLM), prompt versioning, duplicate detector
  (ORB/SIFT) backing the count gate, deterministic output-size contract.

## Review questions
1. Critique these steps + their sequencing. What to add, drop, or reorder?
2. What MUST be built before scaling to many panels (so we don't bake in fragility)?
3. Biggest risks / blind spots in this forward plan?
4. For Step 2, what makes a good FIRST generalization target (geometry features to stress-test)?
