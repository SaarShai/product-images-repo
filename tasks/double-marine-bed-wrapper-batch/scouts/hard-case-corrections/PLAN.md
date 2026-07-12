# Hard-case sparse correction overlays — plan

## What / why

Create two human-authored correction overlays that supply only high-confidence semantic corrections to the existing automatic foreground extractions. Red means definite foreground omitted by the candidate; blue means definite background incorrectly retained by the candidate. Transparent pixels are deliberately unknown.

## Scope

- `image15`: compare `ChatGPT Image Jul 7, 2026, 11_34_15 AM.png` with `image15-auto-v1-rgba.png` and its four-background review board.
- `sample08`: compare `ChatGPT Image Jul 7, 2026, 11_09_25 AM.png` with `sample08-auto-v1-rgba.png` and its four-background review board.
- Inspect full frames and targeted native-resolution crops only.
- Draw sparse, interior strokes/patches. Do not attempt full segmentation.
- For image15, authored bottom sand/watercolor wash is foreground; uniform outer cream paper is background.

## Explicit exclusions

- Do not open or use `bg-benchmark/annotations`, benchmark verdict JSON, verifier output, or prior failure lists.
- Do not run the background-removal pipeline or benchmark.
- Do not infer uncertain antialiased edge pixels; leave them transparent/unknown.

## Method

1. Record source hashes and native dimensions.
2. Inspect sources, candidates, and four-background review boards visually, then inspect native-resolution crops around suspected errors.
   Inventory every visible coral/branch negative-space loop and fork as an explicit native-resolution ROI; any retained cream/white source-paper interior receives a small blue center stroke, otherwise the ROI is recorded as already transparent or non-paper foreground.
3. Encode only clear false negatives as `(255, 0, 0, 255)` and clear false positives as `(0, 0, 255, 255)` on an otherwise `(0, 0, 0, 0)` canvas.
4. Re-open the overlays visually over the source/candidate and run a fresh structural validator.
5. Send the artifacts to an independent read-only vision verifier that receives no annotations or prior failure material.

## Done means

1. Two correction overlays exist in the requested `corrections-v1` folders and exactly match their source dimensions.
2. Every nontransparent pixel is exactly opaque red or opaque blue; all other pixels are alpha zero; the two label sets do not overlap.
3. Corrections are sparse and visibly target only clear source-versus-candidate foreground/background errors, including the image15 wash/paper distinction.
4. Source SHA-256 hashes still match the recorded pre-edit values.
5. Task-side rationale/metrics and an independent validation verdict exist for both cases.

## Source identity recorded before work

- image15: `1536 x 1024`, SHA-256 `bf6f2deb7bce6e2b76a644d0caa7e3ae6519837c4d0842d47c548bc4fb650e72`
- sample08: `1634 x 962`, SHA-256 `8b0111dab8fb19887a83b8eaf8c6140e89d1b3e93b8b61265ab94e6ac3416af2`
