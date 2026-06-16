# A2 Top Contour Artwork-Silhouette Correction - 2026-06-15

## Rejected Set

The `20260615T201000Z-a2-top-arc-side-turn-trimmed-image-gen-*` SVGs do not
trace the top of the current A2 illustration. They transfer black contour shapes
from the earlier screenshots, so the curves cross the placed artwork instead of
sitting outside it.

Dense centerline sampling against
`tasks/castle-panels/outputs/generated/20260615T175712Z-prompt-v7v8-original-a2-character-preserving.png`
found:

- `114443`: `403` painted hits
- `114448`: `348` painted hits
- `114455`: `445` painted hits

Visual issue summary: the curves cut through the left fairy/tower region, do not
follow the actual bridge-and-roof silhouette, and miss the right turret/foliage
edge behavior.

## Corrected Method

Use the placed A2 artwork itself as the source of truth:

1. Scan the top-panel span from `x=62` to `x=792`.
2. Detect the top painted silhouette in the artwork-only PNG.
3. Generate the contour above that silhouette with production clearance.
4. Keep exact open-path endpoints at `(62,433)` and `(792,433)`.
5. Verify the whole path centerline, not only saved vertices, against painted
   source pixels.

Helper:

```bash
python3 scripts/trace_top_contour_from_artwork.py tasks/castle-panels/outputs/generated/20260615T175712Z-prompt-v7v8-original-a2-character-preserving.png --prefix 20260615T205500Z-a2-top-contour-art-silhouette
```

## Current Clean Outputs

Recommended production contour:

`tasks/castle-panels/outputs/final/20260615T205500Z-a2-top-contour-art-silhouette-production.svg`

Review sheet:

`tasks/castle-panels/outputs/reviews/20260615T205500Z-a2-top-contour-art-silhouette-review-sheet.png`

Report:

`tasks/castle-panels/outputs/reviews/20260615T205500Z-a2-top-contour-art-silhouette-report.txt`

Verification summary:

- `production`: `0` source-limit violations, `0` painted centerline hits
- `tight`: `0` source-limit violations, `0` painted centerline hits
- both SVGs contain one open `<path>`, no guide shapes, `viewBox="0 0 854 1842"`
- both endpoints are exactly `(62,433)` and `(792,433)`

Remaining placement caveat: the artwork has finial tips as high as `y=10`, so a
safe contour must run close to the top of the A2 viewBox. More top clearance
requires changing artwork placement or scaling, not just redrawing the contour.
