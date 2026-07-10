# Acceptance rubric

The benchmark has two verdict layers. A candidate may reach machine PASS, but
image 14 remains `PENDING_HUMAN_REVIEW` until every required visual zone is
accepted. Machine checks must not be weakened after viewing a candidate.

| ID | Check | Passing evidence | Failure code |
|---|---|---|---|
| B1 | Inputs are the frozen originals/references | All asset dimensions and SHA-256 values match `manifest.json` | `source_identity_mismatch`, `source_dimension_mismatch` |
| B2 | Candidate is an intentional-size straight RGBA PNG | PNG/RGBA; dimensions match a frozen reference; alpha has both background and foreground; recomposition MAE <= 1.5 and p99 <= 8 | `candidate_format_invalid`, `alpha_channel_missing`, `candidate_dimension_mismatch`, `alpha_background_missing`, `alpha_foreground_missing`, `rgb_reconstruction` |
| B3 | Pale illustration is retained | Every `sure_foreground` disk meets its frozen alpha fraction and median | `deleted_foreground` |
| B4 | Exterior and enclosed/interior paper is transparent | Every sure-BG disk meets its frozen alpha maximum and fraction | `exterior_background_retained`, `enclosed_background_retained` |
| B5 | Labelled edges are decontaminated | Every edge probe has enough boundary support and no more than its frozen paper-colored fraction | `edge_probe_empty`, `white_edge_contamination` |
| B6 | Four-background compositing is reproducible | Report contains same-size deterministic RGB composite hashes for white, gray, black, and magenta | missing/invalid `composites` report |

Human review is required at native candidate resolution for every edge probe,
the pale sand boundary, the cut00 pale branches, and the enclosed triangular
paper pocket. Inspect white, gray, black, and magenta composites for:

- no white/paper halo or dark premultiplied rim;
- no missing pale paint or broken branch/fin silhouette;
- no opaque white pocket where the original shows paper;
- natural soft watercolor transitions rather than clipped or posterized edges.

Sparse guards are rejection evidence, not proof about every unlabeled pixel.
Unlabelled ambiguity must be resolved by human review or a new, independently
annotated benchmark version; it must not be silently relabelled PASS.
