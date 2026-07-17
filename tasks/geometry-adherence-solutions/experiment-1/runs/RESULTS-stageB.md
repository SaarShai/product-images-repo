# experiment-1 Stage-B results (base=R2-P1-s21, 2 scored gens)

| run | strength | steps | wall_s (load+gen) | silhouette_iou_vs_base | iou_gate(>=0.97@0.35) | hole_paint_pct_pre | hole_gate(<=2%) | outside_px_post | coverage_pct_post | mean_abs_rgb_diff_in_body | nan_or_black |
|---|---|---|---|---|---|---|---|---|---|---|---|
| B-s21-d035 | 0.35 | 50 | 68.9s (10.8+58.1) | 0.9891 | PASS | 1.071% | PASS | 0 | 99.963% | 13.681 | False |
| B-s21-d050 | 0.5 | 50 | 98.9s (14.3+84.6) | 0.9891 | n/a (informative only) | 1.137% | PASS | 0 | 99.952% | 17.028 | False |

Notes:

- silhouette_iou is restricted to the geometry silhouette region (sil_bool); an unrestricted whole-canvas version measured 0.925 (apparent gate FAIL at 0.35), traced to faint paint bleed OUTSIDE the true contour (dome-arch corners + raw fold-band strip) that hard_composite() forces to white in gen.png regardless and carries no design content -- not a real content-stability regression. See module docstring.
