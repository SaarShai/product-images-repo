# B0 — Build the fit/quality JUDGE (and calibrate it to the user's eye)

## Goal
A trustworthy automated JUDGE that, given a whole-panel illustration + its SVG template,
returns a PASS/FAIL verdict + typed reasons — and whose verdict **reproduces the user's
labels** on the anchor set. Once trusted, every later build step (B1+) becomes measurable.

## Loop contract (loop-engineering)
- **Generator** (later stages): image candidates. For B0 calibration: the fixed, user-labeled anchors.
- **Verifier = the judge**, 3 layers:
  - **L1 geometry oracle** (deterministic, free): region-IoU (opening placement) + white-IoU
    (cutout cleanliness) + outside_frac (no bleed), via `geom_iou.py` / `svg_geometry_check.py`
    with **canonical registration** (the exact SVG `<image>` transform — never auto-bbox).
  - **L2 defect flags** (cheap): structure/edge checks; MediaPipe for faces/hands (later).
  - **L3 VLM vision** (style/anatomy/rules): reads the registered overlay + high-DPI crops,
    scores style + the skyline rules (no focal motif in red/seams, fits orange arch, top-contour,
    bleed-margin around cutouts). Never scores geometry from the raw image.
- **Gate (calibration)**: judge verdict == user label on every current anchor. A disagreement is
  a finding — fix the judge OR correct the label (ask the user), never silently average away.
- **Stop**: judge reproduces all anchor labels + user signs off.
- **Budget**: incremental. Start L1 (deterministic). Add L2/L3 only where L1 fails to separate
  PASS from FAIL on real anchors — measured, not assumed.

## Build order (each verified with the user)
- **B0.1** L1 geometry calibration — register each anchor, compute geometry metrics, pair with the
  label, report what L1 separates and what it misses. ← current
- **B0.2** L3 VLM rubric — calibrate a vision pass on the overlay+crops to catch what L1 misses
  (crop/red-zone/style/top-contour), anchored to gold pass/fail examples.
- **B0.3** fuse L1+L2+L3 into one verdict + reasons; prove it reproduces all labels; user sign-off.

## Notes
- Re-runnable as anchors grow (user will add more during/after the build).
- Geometry foundation already fixed (R37 transforms, R38 canonical registration).
- Open geometry gaps to fold in: R41 multi-panel viewBox-clip, R42 circle/ellipse extraction.
