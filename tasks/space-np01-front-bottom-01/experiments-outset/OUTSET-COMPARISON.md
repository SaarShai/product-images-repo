# Outset keep-clear test — np01-front-bottom 01

**Problem:** cutout geometry drifts when the model paints openings. If the empty
(paper-white) area is exactly the cutout size, drift pushes the real die-cut into
painted hardware. Fix: make the EMPTY area larger ("outset") by several points so the
cut always lands inside empty paper.

**Two ways tested (3 sources each, nano, same refs):**

## Way A — adapt the SVG (geometry stage) ✅ RECOMMENDED
- `scripts/outset_cutouts.py template.svg --out template-outset12.svg --outset 12`
  buffers each internal cutout outward +12 user-units (shapely), outer contour verbatim.
- Rebuild the true-aspect base from the outset SVG → the layout-contract image ("image 1")
  now shows LARGER holes. Generate with the normal prompt.
- Result (A-s1, A-s2, A-s3): **consistent & controlled.** Both openings stay separate,
  correctly sized (true + 12pt), clean empty centers, generous even margin on all sides,
  hardware well clear. The outset amount is exactly what you set — predictable.

## Way B — prompt instruction only (style stage) ⚠️ unreliable
- Original SVG/base; prompt adds "leave an oversized empty keep-clear band ~12–18 pt
  larger than each opening, all hardware outside it."
- Result: works *sometimes* but the model's interpretation VARIES a lot:
  - B-s1: round port grossly OVERSIZED (way past 18pt).
  - B-s2: model MERGED slot + port into one white shape joined by a white channel.
  - B-s3: uneven.
- The amount and shape of the margin are not controllable from prose.

## Verdict
**Adapt the SVG.** The outset must arrive as PIXELS in the contract image — same lesson
as the whole pipeline (geometry must be pixels, not prose). The prompt route alone is too
variable. Best practice: outset the SVG by N pt AND keep a mild prompt nudge ("keep
hardware clear of the openings") as reinforcement — but the SVG/base is load-bearing.

Recommended default: outset ~10–15 user-units (here 12 ≈ 1.7% of panel height, ~1.7% width).
Tune per template; the real cut uses the ORIGINAL SVG, the outset only governs the empty zone.

Files: `template-outset12.svg`, `np01-fb-01-base-outset12-1440x2560.png`,
`experiments-outset/OUTSET-A-svg-s*/raw.png`, `OUTSET-B-prompt-s*/raw.png`.
Central copies in `../space-np01-front-bottom-02/RESULTS/Images/`.
