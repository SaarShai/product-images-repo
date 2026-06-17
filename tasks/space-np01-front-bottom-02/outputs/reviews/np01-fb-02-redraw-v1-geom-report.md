# Step 6 — geometry adherence check

candidate: `tasks/space-np01-front-bottom-02/outputs/generated/np01-fb-02-redraw-v1-raw.png`
svg: `tasks/space-np01-front-bottom-02/source/template.svg`   bbox: `(291.0, 18.0, 733.0, 1518.0)`

OVERALL: **FAIL**  (mechanical gate only — not style approval)

- silhouette: 27612 painted px outside contour (4.9% of panel paint) -> FAIL

| # | hole | bbox(svg) | hole px | painted px | painted frac | verdict |
|---|---|---|---|---|---|---|
| 1 | polygon | [359.8, 1073.1, 550.0, 1237.8] | 7938 | 2899 | 0.365 | FAIL |
| 2 | polygon | [363.1, 711.0, 546.8, 894.7] | 7890 | 2959 | 0.375 | FAIL |
| 3 | polygon | [359.8, 367.9, 550.0, 532.6] | 7938 | 3062 | 0.386 | FAIL |
| 4 | path | [385.2, 1469.9, 524.7, 2428.0] | 43860 | 16135 | 0.368 | FAIL |
