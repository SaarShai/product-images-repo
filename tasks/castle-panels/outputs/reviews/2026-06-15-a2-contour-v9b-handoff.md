# A2 Contour + V9B Scratch Handoff - 2026-06-15

## A2 Top Contour

- SVG path only:
  `tasks/castle-panels/outputs/final/20260615T175712Z-a2-top-subpanel-contour.svg`
- Preview over A2 artwork:
  `tasks/castle-panels/outputs/reviews/20260615T-a2-top-subpanel-contour-vector-preview.png`
- Preview over A2 template overlay:
  `tasks/castle-panels/outputs/reviews/20260615T-a2-top-subpanel-contour-vector-on-template-preview.png`

The SVG contains one open vector path and no template guide lines. Its viewBox is
`0 0 854 1842`, matching the A2 artwork/review coordinate system.

## Parallel Scratch Lane

Revised V9B template-first was exported with the same practical placement recipe
used in review:

```bash
python3 scripts/export_composite.py tasks/castle-panels/outputs/generated/20260615T174701Z-prompt-v9b-template-first-revised.png --prefix 20260615T174701Z-v9b-template-first-revised-scale090-y50 --art-scale 0.90 --art-scale-y 1.00 --art-offset-y 50
```

Exported files:

- `tasks/castle-panels/outputs/final/20260615T174701Z-v9b-template-first-revised-scale090-y50-artwork-only.png`
- `tasks/castle-panels/outputs/final/20260615T174701Z-v9b-template-first-revised-scale090-y50-clean-black-lines.png`
- `tasks/castle-panels/outputs/final/20260615T174701Z-v9b-template-first-revised-scale090-y50-full-guides.png`
- `tasks/castle-panels/outputs/final/20260615T174701Z-v9b-template-first-revised-scale090-y50-metadata.json`
