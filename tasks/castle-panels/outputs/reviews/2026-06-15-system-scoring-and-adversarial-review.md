# System Scoring And Adversarial Review - 2026-06-15

## What Changed

Added deterministic scoring and placement-sweep support for castle-panel
candidate review:

```bash
python3 scripts/score_template_fit.py --batch-generated --sweep --mode wall --md-out tasks/castle-panels/outputs/reviews/20260615T-system-wall-score-sweep.md --json-out tasks/castle-panels/outputs/reviews/20260615T-system-wall-score-sweep.json
```

The scorer measures side/bottom safe-margin pressure, center-lane fill, red-zone
detail, black cutline detail, and feature gaps under fixed template overlays.

## Key Result

The broad wall-mode sweep showed that the earlier default placement recipes were
not enough: V6 scored best mechanically, but it is not a true wall-center
candidate.

A targeted wall-center sweep on revised V9B found a better recipe:

```bash
python3 scripts/score_template_fit.py tasks/castle-panels/outputs/generated/20260615T174701Z-prompt-v9b-template-first-revised.png --mode wall --sweep --x-scales 0.66,0.70,0.74,0.78,0.82,0.84 --y-scales 0.92,0.96,1.00,1.04 --y-offsets 0,20,40,60,80 --json-out tasks/castle-panels/outputs/reviews/20260615T-system-wall-v9b-targeted-sweep.json --md-out tasks/castle-panels/outputs/reviews/20260615T-system-wall-v9b-targeted-sweep.md
```

Best wall-center candidate:

- Source: `tasks/castle-panels/outputs/generated/20260615T174701Z-prompt-v9b-template-first-revised.png`
- Recipe: `scale_x=0.70`, `scale_y=1.04`, `offset_y=0`
- Score: `94.30 PASS`
- Feature gaps: left `12 px`, right `12 px`, bottom `37 px`
- Export: `tasks/castle-panels/outputs/final/20260615T-system-v9b-wall-sx070-sy104-y0-full-guides.png`
- Score JSON: `tasks/castle-panels/outputs/reviews/20260615T-system-v9b-wall-sx070-sy104-y0-score.json`

Conservative alternate:

- Recipe: `scale_x=0.66`, `scale_y=1.04`, `offset_y=0`
- Score: `94.17 PASS`
- Feature gaps: left `30 px`, right `29 px`, bottom `37 px`
- Export: `tasks/castle-panels/outputs/final/20260615T-system-v9b-wall-sx066-sy104-y0-full-guides.png`
- Tradeoff: safer side clearance, but visibly more horizontal compression.

## Rejected Or Lower-Confidence Lanes

- Original V7 wall-center lane remains visually rich but failed targeted scoring
  because focal/color detail stays too close to cut paths.
- A2 character-preserving branch is useful for contour experiments, but failed
  wall-center scoring and should not be treated as a full product-fit candidate.
- V6/V5 remain useful empty-center references. They should not be promoted as
  wall-center results because the center lane is too blank.

## Adversarial Review

The scorer is intentionally conservative but not complete.

Known limits:

- It cannot identify semantic motifs. A fairy, flower head, window, or roof tip
  near a cut band still needs visual review.
- It uses rasterized template-preview color masks, not a direct SVG-derived mask.
  That is acceptable for fast ranking, but the production handoff should still
  treat `assets/templates/two-panel-template.svg` as the geometry source.
- The top contour remains a separate decision. The current wall-center export
  has tall spires near the upper safe arc; use the artwork-silhouette contour
  method if a custom top contour is needed.
- The current best wall candidate passes mechanical scoring, but the horizontal
  split crosses side architecture/foliage. This is much safer than crossing a
  fairy or bird, but it should be reviewed before production.

## Next Iteration Rule

For future no-user-feedback runs:

1. Generate one candidate for one mode.
2. Register it under `outputs/generated/`.
3. Run a targeted score sweep for that mode.
4. Inspect only the top 3 exports/debug overlays.
5. Promote only if both the score gate and adversarial visual review pass.
