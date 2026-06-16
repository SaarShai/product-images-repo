# Castle Panels Final Handoff - 2026-06-15

## Canonical Status

Use `tasks/castle-panels/CURRENT.md` for the latest state. This handoff keeps the
scored export commands and artifacts.

## Current Best Wall-Center Candidate

Source artwork:

`tasks/castle-panels/outputs/generated/20260615T174701Z-prompt-v9b-template-first-revised.png`

Current best scored placement:

- Artwork scale X: `0.70`
- Artwork scale Y: `1.04`
- Artwork offset X: `0`
- Artwork offset Y: `0 px`
- Template fit: `cover`
- Score: `94.30 PASS`
- Measured feature gaps: left `12 px`, right `12 px`, bottom `37 px`

Exported files:

- Artwork only:
  `tasks/castle-panels/outputs/final/20260615T-system-v9b-wall-sx070-sy104-y0-artwork-only.png`
- Artwork with clean black template lines:
  `tasks/castle-panels/outputs/final/20260615T-system-v9b-wall-sx070-sy104-y0-clean-black-lines.png`
- Artwork with full construction guides:
  `tasks/castle-panels/outputs/final/20260615T-system-v9b-wall-sx070-sy104-y0-full-guides.png`
- Export metadata:
  `tasks/castle-panels/outputs/final/20260615T-system-v9b-wall-sx070-sy104-y0-metadata.json`
- Score:
  `tasks/castle-panels/outputs/reviews/20260615T-system-v9b-wall-sx070-sy104-y0-score.json`

Recreate command:

```bash
python3 scripts/export_composite.py tasks/castle-panels/outputs/generated/20260615T174701Z-prompt-v9b-template-first-revised.png --prefix 20260615T-system-v9b-wall-sx070-sy104-y0 --art-scale 1 --art-scale-x 0.70 --art-scale-y 1.04 --art-offset-y 0 --score-json tasks/castle-panels/outputs/reviews/20260615T-system-v9b-wall-sx070-sy104-y0-score.json
```

Remaining review risk: the horizontal split crosses side architecture/foliage.
This looks materially better than the older V9B `scale_x=0.90` export, but it is
not a substitute for a semantic production review.

Conservative alternate: `20260615T-system-v9b-wall-sx066-sy104-y0` scores
`94.17 PASS` and increases side feature gaps to left `30 px` and right `29 px`,
but it looks more horizontally compressed. Use it only if stricter side
clearance matters more than preserving artwork density.

## Previous V6 Empty-Center Reference

Source artwork:

`tasks/castle-panels/outputs/generated/20260615T132212Z-prompt-v6-narrow-center-safe-gutters.png`

Current best placement:

- Artwork scale: `0.90`
- Artwork offset X: `0`
- Artwork offset Y: `+50 px`
- Template fit: `cover`
- Fixed template preview:
  `assets/templates/previews/two-panel-template-cropped.png`

## Previous V6 Exported Files

- Artwork only:
  `tasks/castle-panels/outputs/final/20260615T132212Z-v6-scale090-y50-artwork-only.png`
- Artwork with clean black template lines:
  `tasks/castle-panels/outputs/final/20260615T132212Z-v6-scale090-y50-clean-black-lines.png`
- Artwork with full construction guides:
  `tasks/castle-panels/outputs/final/20260615T132212Z-v6-scale090-y50-full-guides.png`
- Export metadata:
  `tasks/castle-panels/outputs/final/20260615T132212Z-v6-scale090-y50-metadata.json`

## Previous V6 Recreate Command

```bash
python3 scripts/export_composite.py tasks/castle-panels/outputs/generated/20260615T132212Z-prompt-v6-narrow-center-safe-gutters.png --prefix 20260615T132212Z-v6-scale090-y50 --art-scale 0.90 --art-offset-y 50
```

## Previous V6 Notes

- Prompt V6 preserves the designed-center concept without a fade/erase effect.
- The high top bridge reconnects the left and right castle groups.
- Scaling the artwork to `90%` improves side safe margins.
- Moving the scaled artwork down by about `50 px` improves the bottom gap while
  keeping the top bridge clear of the short upper red keep-out rectangle.

## Remaining Decisions

- The clean black-line export contains only the black template lines available
  from the current template preview/SVG. The top custom contour remains a
  separate production decision.
- If using a custom top contour, prefer the current artwork-silhouette method
  and require `0` painted centerline hits against the placed artwork.
- The scored wall-center candidate still needs semantic review around the
  horizontal split, especially where the split crosses side architecture and
  foliage.
- If the scored candidate is approved, the next production step is to create the
  final exact vector mask/cut contour from the authoritative SVG/Illustrator
  workflow, using this artwork placement as the visual layer.
