---
schema_version: 2
title: "Illustrated product upscale and background-removal workflow"
type: concept
domain: image-generation
tier: semantic
confidence: 0.8
trust: verified
validation_scope: "single-sample: sample08; full-folder batch not yet verified"
created: "2026-07-08"
updated: "2026-07-08"
verified: "2026-07-08"
sources:
  - "/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/double Marine Bed Wrapper/images/Images/candidates/upscale-first/hard180-manual-repair-workflow-v1.md"
  - "/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/double Marine Bed Wrapper/images/Images/candidates/upscale-first/sample08-hard180-surgical-repair-metrics-v2.json"
supersedes: []
superseded-by:
contradicts: []
tags:
  - image-generation
  - upscaling
  - background-removal
  - hard-alpha
  - screenery
  - task-retrospective
---

# Illustrated product upscale and background-removal workflow

## Summary

For similar illustrated watercolor product assets, treat this as a starting
workflow rather than a universal rule: upscale first and decide background
removal second. Use a sample-gated, hard-alpha workflow because global soft
alpha produced faded edges/halos on sample08, while global model swaps did not
beat the sample-specific hard180 result.

**Trigger / symptom:** future illustrated product-image upscaling or
background-removal tasks where the user needs high-resolution PNGs with clean
transparent backgrounds, hard or nearly-hard alpha, and reviewable sample
candidates before a batch run.

## Procedure

1. Write all candidates under the user's target folder in `Images/candidates/`;
   never modify source images.
2. Decide upscaling before background removal. Run the sample through several
   upscale candidates before choosing the background-removal route.
3. For this folder/style family, use local Real-ESRGAN x4plus as the default
   x4 route when the review candidate preserves the artwork.
4. For x8, prefer the known-good x16-then-Lanczos-downsample route over direct
   Real-ESRGAN second-pass `-s 2`, because direct `-s 2` produced tile/mosaic
   artifacts on sample08.
5. Run background removal on the x4 RGB sample, not the x8/x16 final, to keep
   model inference practical.
6. Use BRIA RMBG hard180 as the current baseline when the user wants hard alpha
   and minimal halos.
7. Verify alpha histogram and report transparent %, opaque %, and
   semi-transparent %. The expected hard-alpha gate is `semi_pct == 0.0`.
   Keep final alpha binary by default; allow a localized one-pixel
   anti-aliasing patch only if a specific jagged curve is reviewed and approved,
   and report any nonzero `semi_pct` as a deliberate exception.
8. Build a high-resolution crop board plus individual clickable file paths; do
   not rely only on a compressed overview grid.
9. For remaining defects, treat them as mask-repair defects rather than as a
   reason to switch global removers:
   - colored enclosed restore for over-cut holes;
   - colored-margin restore near existing foreground for thin-stem erosion;
   - reviewed ROI white-gap cleanup for trapped background.
10. Reject broad unattended repairs if metrics show many new small foreground
    components or the change overlay shows widespread restored pixels.
11. Transfer the approved x4 binary mask to x8 by resizing the mask and
    hard-thresholding again, then QA at x8 on gray, white, black/magenta, and
    the final expected background.
12. Only batch the folder after the user approves scale, baseline background
    method, and repair policy on the sample.

Production default if the sample is approved:
`x4 Real-ESRGAN -> BRIA hard180 -> colored-margin restore -> human ROI white-gap cleanup -> binary x8 mask transfer`.

Do not use these as unattended defaults for this workflow: soft160, broad color
reclaim, direct Real-ESRGAN second-pass `-s 2`, or automatic white-gap removal.

## Evidence

- Sample workflow note:
  `/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/double Marine Bed Wrapper/images/Images/candidates/upscale-first/hard180-manual-repair-workflow-v1.md`.
- Hard180 candidate: `sample08-bg-bria180-x4-hard-clean.png`, `5792 x 4344`,
  alpha `49.2416%` transparent, `50.7584%` opaque, `0.0000%`
  semi-transparent.
- Colored-margin repair candidate:
  `sample08-bg-bria180-x4-colored-margin-restore-hard-clean.png`, restored
  `33,931` likely over-cut pixels and kept `0.0000%` semi-transparent.
- Broad color reclaim was rejected because it restored `228,181` pixels in
  `716` components.
- White-gap automation was demoted to ROI/manual review because metrics jumped
  to many small foreground components.
- User corrections: soft160 edges were too faded, halos were unacceptable,
  hard180 was closest, and image references need clickable full paths.

## Why Not A Skill Yet

This is a repeatable SOP, but it is sample-proven rather than batch-proven
because the full folder batch has not been run or approved yet. Store it as a
wiki SOP now so future sessions recall the current workflow, and promote it to a
proposed skill only after one successful folder batch confirms the commands and
gates end-to-end.

## Related

- [[concepts/mask-bounded-external-redraw-donor]]
- [[concepts/background-routes-must-write-resumable-checkpoints]]
- [[index]]

## Open Questions

- Whether the hard180 plus colored-margin restore route holds across the full
  double Marine Bed Wrapper folder, not only sample08.
- Whether ROI/manual white-gap cleanup can be made safe enough for unattended
  batch use after more examples.
- Before batching, compare baseline hard180, colored-margin restore, and its
  change overlay on the known defect zones.
