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
5. When using x16 internally for an x8 deliverable, keep x16 files as scratch
   only: delete or hide them after the run, label the manifest/finals as x8,
   and verify source-to-final dimensions so transient artifact names cannot be
   mistaken for the delivered scale.
6. Run background removal on the x4 RGB sample, not the x8/x16 final, to keep
   model inference practical.
7. Use BRIA RMBG hard180 as the current baseline when the user wants hard alpha
   and minimal halos.
8. Verify alpha histogram and report transparent %, opaque %, and
   semi-transparent %. The expected hard-alpha gate is `semi_pct == 0.0`.
   Keep final alpha binary by default; allow a localized one-pixel
   anti-aliasing patch only if a specific jagged curve is reviewed and approved,
   and report any nonzero `semi_pct` as a deliberate exception.
9. Build a high-resolution crop board plus individual clickable file paths; do
   not rely only on a compressed overview grid.
10. For remaining defects, treat them as mask-repair defects rather than as a
   reason to switch global removers:
   - colored enclosed restore for over-cut holes;
   - colored-margin restore near existing foreground for thin-stem erosion,
     with a component-size guard so speck-like candidates are not restored;
   - reviewed ROI white-gap cleanup for trapped background.
11. Reject broad unattended repairs if metrics show many new small foreground
    components or the change overlay shows widespread restored pixels.
12. Transfer the approved x4 binary mask to x8 by resizing the mask and
    hard-thresholding again, then QA at x8 on gray, white, black/magenta, and
    the final expected background.
13. Only batch the folder after the user approves scale, baseline background
    method, and repair policy on the sample.

Production default after the 19-image batch:
`x4 Real-ESRGAN -> BRIA hard180 -> guarded colored-margin restore -> x16/Lanczos RGB downsample -> binary x8 mask transfer`.

For the batch script, the colored-margin restore guard uses a minimum repair
component size of `256` pixels because smaller candidates produced thousands of
speck-like components on the first batch image. Keep that guard or a comparable
component filter to avoid restoring stray background pixels as foreground.

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
  hard180 was closest, image references need clickable full paths, and x16
  should be communicated as an internal transient when the requested deliverable
  is x8.
- Full-folder batch evidence:
  `/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/double Marine Bed Wrapper/images/Images/finals/batch-manifest.json`.
- Batch verifier passed `19/19` entries with `0` failures. All finals are x8
  transparent PNGs, final dimensions equal source dimensions times `8`, and
  total semi-transparent alpha pixels across the manifest were `0`.
- After the x16/x8 clarification, a fresh dimension audit reported
  `non_x8_count 0` and the batch temp folder reported `tmp_count 0`.
- Review sheets exist under:
  `/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/double Marine Bed Wrapper/images/Images/finals/review`.
- Pause/resume was verified: after stopping at 8 completed finals, the runner
  resumed from cached/intermediate state, skipped completed finals, and
  finished the remaining images without source-file changes.

## Why Not A Skill Yet

This is now batch-proven for one full folder. Keep it as a wiki SOP until the
workflow recurs on another folder or the user explicitly asks to turn it into a
proposed skill, because the current runner is still product-folder-specific and
the safest next promotion would be a parameterized wrapper around the verified
script and verifier.

## Related

- [[concepts/mask-bounded-external-redraw-donor]]
- [[concepts/background-routes-must-write-resumable-checkpoints]]
- [[index]]

## Open Questions

- Whether the guarded colored-margin restore holds on a second illustrated
  product folder.
- Whether ROI/manual white-gap cleanup can be made safe enough for unattended
  batch use after more examples.
- Whether to promote the verified runner into a proposed repo-local skill if
  the same workflow recurs.
