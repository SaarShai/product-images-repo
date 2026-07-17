# VERDICT — geometry evidentiary run, princess narrow 02

Recorded 2026-07-17. Human arbiter: user, from
`REVIEW/geometry-evidentiary-princess-n02/fullres/outset-c1-overlay.png`.

## Result: NEGATIVE (run wrapped, not accepted)

Style MET; geometry NOT-MET (mean_iou 0.120, holes 3/4/5 painted 71.5/98.5/97.5%).
User confirmed rejection visually and closed the run.

## User feedback (verbatim defects, circled on overlay)

1. **Red line crossing the top subpanel** — overlay/geometry-line mistake, not
   art. Maps to the panel-spec/overlay generation, expected to resolve as panel
   geometry lines improve. Tooling defect, not a gen defect.
2. **Bird extends beyond the border of the panel** — real outside-silhouette
   violation (criterion 1; measured outside_frac 0.0091). Confirms the
   never-crop / border-strip class of gate is needed here too.
3. **Window painted in the forbidden zone (overlapping the slots)** — real
   cutout violation (criterion 3; holes 3/4/5 FAIL). The gen ignored the
   keep-clear slots despite the outset guide.
4. **Spires weirdly cut at the top** — composition defect: art truncated
   against the top contour instead of adapting to it (violates the
   complete-building rule).

## What this run proved (usable by future agents)

- The documented svg-geometry-style pipeline was NOT cold-executable at freeze
  (attempt 1: 7 tooling findings) — now fixed through commit 40cbd70.
- `export_svg_template_fit.py --require-pass` was a structural false-positive
  gate on rect/cutout-path templates (finding B) — fixed; its historical PASSes
  on such templates are not trustworthy evidence.
- Geometry adherence via prompt+outset-guide alone is insufficient on this
  panel class: cutouts violated 71-98%, IoU 0.120. Consistent with banked
  lessons (composition-belongs-to-placement, reference-beats-description):
  enforcement must be mechanical (region-map guide, aperture-lock/punch,
  composite-back), not prompt-side.
- Finding C remains OPEN: the workflow has no composite-embedded-raster-back
  step, so fixed-element sockets (the door) are unavoidably "violated" by any
  gen. Criteria 1 and 5 are in tension until that step exists.
- Human defect classes (bird-over-border, truncated spires, forbidden-zone
  window, overlay line error) each need a per-class gate before a future
  attempt can claim PASS (gate-per-visible-defect-class rule).

## Claim ceiling

Nothing validated. Max claim: "pipeline is now cold-executable and its gates
measure honestly on one held-out panel; geometry adherence itself failed."

## Status

Run CLOSED as negative result. Attempt 3 not run (gen spend not authorized).
Next lane when reopened: finding C composite-back step + region-map guide +
per-defect-class gates, then a fresh frozen contract.
