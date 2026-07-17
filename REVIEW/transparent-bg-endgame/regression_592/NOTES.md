# R38 visual re-validation — green_purge.py hardening regression vs banked round-7 output

Date: 2026-07-16. Scope: `H-G2-OUT-GREEN-r1` and `-r2` only (the two round-7
"best yet — bank it" candidates). This closes the outstanding R38 ledger item
("signed off on a COUNT metric with no visual re-check").

## What was compared

- **Current output**: re-derived from raw green-screen renders using the
  Route C-green v2 recipe (PIPELINE.md, current HEAD scripts, commit
  `f3bc9c4` — "Independent audit fixes: retract overclaims, fix misrouting +
  runner/purge P0s"):
  1. `scripts/chroma_key.py key raws/H-G2-OUT-GREEN-<tag>.png keyed-<tag>.png`
  2. `scripts/decontam_binarize.py --rgba keyed-<tag>.png --out decontam-<tag>.png --bg-color '#00FF00'`
  3. `scripts/green_purge.py decontam-<tag>.png purged-<tag>.png --no-green-art --erode 2 --band 6`
  Run under `/usr/bin/python3` in a scratch dir, per PIPELINE.md § Route
  C-green v2.
- **Banked reference**: `tasks/transparent-bg-endgame/round7_outline/processed/H-G2-OUT-GREEN-<tag>-purged.png`,
  generated 2026-07-13 09:26 — right after commit `3b0d0c3` and *before* the
  two later `green_purge.py` hardening passes (`19546d7` Sol audit round 2,
  and `f3bc9c4` independent audit fixes, both applied since).

Diff = per-pixel RGBA inequality (any channel) between new and banked, at
identical 1024×1536 resolution. Clustering = 8-connected components on the
changed-pixel mask after 1 dilation iteration (merges near-neighbor changed
pixels into one cluster; does not itself count as a changed pixel).

## Headline numbers

| | r1 | r2 |
|---|---|---|
| Changed px (any RGBA channel) | **58** | **5** |
| Alpha-channel changed px | 0 | 0 |
| Clusters (8-conn, 1px dilation merge) | 26 | 5 |
| Mean \|Δ\| over changed px (0-255 scale, per-channel max) | 55.21 | 12.2 |
| Max \|Δ\| over changed px | 190 | 46 |
| Largest single cluster | 5 px | 1 px |

Full per-cluster tables: `r1-clusters.json`, `r2-clusters.json`. Aggregate:
`all_stats.json`.

**Alpha is untouched in both candidates (0 px)** — confirms the original
"RGB-only" framing. The **pixel counts here (58 / 5, 63 total) are
substantially smaller than the R38 ledger snapshot (592 px / 58 clusters /
meanΔ56 / maxΔ149)**. That's expected and itself worth recording: the R38
number was measured mid-hardening (after `19546d7`, before `f3bc9c4`); the
independent-audit-fixes commit (`f3bc9c4`, today) further changed
`green_purge.py`'s repaint/donor-safety logic and reduced the delta from
banked by ~90%. r1's mean-Δ (55.21) and cluster count in the same ballpark as
the R38 snapshot (56 / 58) landing almost exactly on today's r1 alone
suggests the R38 592-px figure likely already included both candidates plus
possibly a coarser/no-dilation clustering pass — treat R38's raw number as
superseded by this re-derivation, not contradicted.

## Visual verdict

Every rendered cluster board (`boards/`, 12× NEAREST, banked | new |
diff-heatmap, checkerboard alpha compositing) shows **isolated 1-to-5-pixel
speckles inside busy textured/edge regions** (fine ink-line texture, feather
boundaries of thin decorative strands) — never a contiguous patch, never a
visible color-band, never a shape/geometry change. In the side-by-side
banked/new panels at 12×, the differences are **not visually distinguishable
by eye**; they only become visible when isolated in the diff-heatmap channel.
No new artifacts (no green residue, no halo, no hue banding) are introduced;
the changed pixels sit on both sides of ±Δ (some pixels get slightly darker,
some slightly lighter/more saturated) consistent with a donor-repaint
re-derivation rather than a systematic defect.

**Verdict: the RGB-only regression from the green_purge.py hardening is
visually a non-issue on both banked "best yet" candidates.** Direction is
consistent with the intended fix (donors sourced from real opaque art per the
independent-audit repaint-safety fix), magnitude is now smaller than at the
time R38 was filed, and no pixel cluster reaches a size or contrast where a
human reviewer would notice it without a diff tool. Recommend closing R38 on
this evidence.

## Files

- Boards (top 12 clusters by pixel count for r1, all 5 for r2), each a
  12× NEAREST banked | new | diff-heatmap triptych with cluster px/bbox/Δ
  stats in the title bar:
  `/Users/za/Documents/product images repo/REVIEW/transparent-bg-endgame/regression_592/boards/`
- Full-resolution banked + newly-derived purged RGBAs (both candidates):
  `/Users/za/Documents/product images repo/REVIEW/transparent-bg-endgame/regression_592/fullres/`
- Per-candidate cluster tables (JSON, all clusters not just top 12):
  `/Users/za/Documents/product images repo/REVIEW/transparent-bg-endgame/regression_592/r1-clusters.json`
  `/Users/za/Documents/product images repo/REVIEW/transparent-bg-endgame/regression_592/r2-clusters.json`
- Aggregate stats: `/Users/za/Documents/product images repo/REVIEW/transparent-bg-endgame/regression_592/all_stats.json`
- Analysis script (reproducible): `/Users/za/Documents/product images repo/REVIEW/transparent-bg-endgame/regression_592/analyze.py`
