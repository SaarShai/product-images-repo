# Castle Panels Current Status

Updated: 2026-06-15

## Current Modes

- Empty-center mode: V6/V9A-style composition. The center lane should remain
  blank or nearly blank.
- Wall-center mode: V7/V8/V9B-style composition. The center lane may contain
  quiet wall/background texture only.

Keep these modes separate. Do not judge an empty-center prompt by wall-center
criteria, or a wall-center prompt by empty-center criteria.

## Current Best References

- Best complete empty-center reference:
  `tasks/castle-panels/outputs/generated/20260615T132212Z-prompt-v6-narrow-center-safe-gutters.png`
- Current best wall-center export after scoring:
  `tasks/castle-panels/outputs/final/20260615T-system-v9b-wall-sx070-sy104-y0-full-guides.png`
- Current best wall-center score:
  `tasks/castle-panels/outputs/reviews/20260615T-system-v9b-wall-sx070-sy104-y0-score.json`
- Source wall-center artwork:
  `tasks/castle-panels/outputs/generated/20260615T174701Z-prompt-v9b-template-first-revised.png`
- Best current A2 top-contour method:
  `tasks/castle-panels/outputs/final/20260615T205500Z-a2-top-contour-art-silhouette-production.svg`

## Promotion Gate

A candidate is not ready for handoff until it has:

1. A generated artwork PNG saved under `outputs/generated/`.
2. A template-fit score report from `scripts/score_template_fit.py`.
3. A fixed-template overlay/export recipe with metadata.
4. A visual review note that checks semantic failures the scorer cannot prove,
   especially fairies, birds, butterflies, flower heads, windows, doors, lamps,
   flags, roof tips, and other recognizable motifs near cut bands.
5. If a custom contour is used, a contour report with `0` painted centerline
   hits against the placed artwork.

## Current Work

The current system work added deterministic scoring and placement sweeps so
future iterations can move quickly:

```bash
python3 scripts/score_template_fit.py --batch-generated --sweep --mode wall --md-out tasks/castle-panels/outputs/reviews/20260615T-system-wall-score-sweep.md --json-out tasks/castle-panels/outputs/reviews/20260615T-system-wall-score-sweep.json
python3 scripts/score_template_fit.py --batch-generated --sweep --mode empty --md-out tasks/castle-panels/outputs/reviews/20260615T-system-empty-score-sweep.md --json-out tasks/castle-panels/outputs/reviews/20260615T-system-empty-score-sweep.json
```

The scorer is a rejection/ranking aid, not a substitute for final visual review.

Latest wall-center result:

- `20260615T-system-v9b-wall-sx070-sy104-y0`: `PASS`, score `94.30`
- Placement: `scale_x=0.70`, `scale_y=1.04`, `offset_y=0`
- Measured gaps: left `12 px`, right `12 px`, bottom `37 px`
- Conservative alternate:
  `20260615T-system-v9b-wall-sx066-sy104-y0`, `PASS`, score `94.17`,
  left `30 px`, right `29 px`, bottom `37 px`
- Remaining review risk: horizontal split crosses side architecture/foliage and
  needs semantic review before production handoff.
