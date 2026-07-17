# Attempt 2 (post-fix, HEAD 9fdd062) — cold executor findings

Criteria: 1 NOT-MET (111,110 violation px: holes 3/4/5 painted 71.5/98.5/97.5%,
outside 0.9%); 2 NOT-MET (mean_iou 0.120); 3 NOT-MET (cutouts painted);
4 MET (style vs frozen refs — executor visual judgment); 5 NOT-MET mechanically
(door painted INTO the embedded-raster socket = the criterion-1 worst violation).
Metrics: experiments-outset/outset-c1/metrics-original-svg.json. c2 strictly worse
(systematic, not noise). Attempt-1 fixes all re-verified working.

NEW findings:
- A: geom_adherence_test.py internal subprocess call hardcodes bare `python3`
  (not sys.executable) → swallowed guard message (capture_output) → crashes on
  missing metrics.json AFTER spending a real gen. Reproduced 2×, verbatim
  traceback in executor report (ledger R52).
- B: export_svg_template_fit.py --require-pass = STRUCTURAL false positive on
  this template: read_template() handles only <path>/<polygon>, unions cutout
  paths into the paintable mask; template has 4 <rect> cutouts + <path> cutouts
  st1/st2/st4 → reports 0 violations where svg_geometry_check.py measures
  71.5-98.5%. Its PASS is not trustworthy evidence for rect/cutout-path templates.
- C: contract criteria 1 vs 5 in tension: SVG treats the door zone (st1) as an
  internal_cutout socket for the REAL embedded raster; the workflow has no
  composite-embedded-raster-back step, so any generated door there is a
  violation. Both candidates hit it (prompt frames a door per contract).

Next-lane candidates (not started): fix A (sys.executable + check returncode),
fix B (parse <rect>, exclude internal_cutout paths from paintable union) each
with fail-pre-fix fixtures; contract/workflow: socket zones must be masked out
of gen + composited after (region-map/aperture-lock precedent).
