# Image 14 sparse sure-FG / sure-BG correction labels

This folder contains a short, deliberately sparse human-correction pass for the Photoshop image14 background-removal proposal. It is not a segmentation, trimap, solver result, or production final.

## Inputs inspected at native size

- Source: `/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/double Marine Bed Wrapper/images/ChatGPT Image Jul 7, 2026, 11_22_35 AM.png`
- Photoshop proposal alpha: `/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/double Marine Bed Wrapper/images/Images/candidates/image14-research/photoshop-scout/image14-photoshop-auto-mask-alpha.png`
- Deletion diagnostic: `/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/double Marine Bed Wrapper/images/Images/candidates/image14-research/photoshop-scout/diagnostic-high-confidence-deletion-overlay-red.png`

All three are 941×1672. Verified SHA-256 values are recorded in `image14-labels-metadata.json` and checked by the build script before it writes anything.

No `bg-benchmark` or benchmark/guard artifact was read. The script does not run a solver.

## Annotation contract

- `(0,0,0,0)` = unknown; this is nearly the entire image.
- `(255,0,0,255)` = visually certain foreground that Photoshop deleted.
- `(0,0,255,255)` = visually certain background that Photoshop wrongly kept; none was sufficiently certain here, so blue count is zero.

Coordinates are native pixel centers, `(x, y)`, with origin at the upper-left. The five red strokes are width 13 px: broad enough to survive a one-pixel transport error, but sparse enough to leave substantial surrounding area for a downstream unlock radius.

| ID | Start → end | Visual reason |
|---|---|---|
| R1 | `(58,1503) → (105,1525)` | Left sandy wash immediately outside the reef base |
| R2 | `(568,1509) → (529,1537)` | Painted sand between the central shell and front wash |
| R3 | `(628,1552) → (679,1561)` | Right-center sandy watercolor footprint below shell details |
| R4 | `(262,1595) → (325,1595)` | Lower-left painted wash beneath the starfish |
| R5 | `(874,1534) → (834,1538)` | Right sandy wash immediately outside the reef base |

The strokes touch both dominant deleted-sand components while avoiding bubble rims, isolated branch-interior pinpricks, and the feathered outermost sand boundary. Those ambiguous pixels stay unknown.

Measured native coverage is 3,215 red pixels across five disconnected strokes, 0 blue pixels, and 1,570,137 transparent unknown pixels. That is `3,215 / 1,573,352 = 0.2043408%` labeled coverage.

Blue was considered and deliberately omitted. A separate read-only verifier initially suggested outer blank-canvas strokes, but those locations had proposal alpha 0—Photoshop had already removed them correctly. On corrected reinspection, retained exact-white regions were only 341 pixels across 210 components; the largest component was 9 pixels. Near-white retained loci were likewise tiny and touched painted structures or highlights, so no conservative blue stroke was established.

## Deterministic build

```bash
python3 tasks/double-marine-bed-wrapper-batch/scouts/image14-labels/build_labels.py
```

The script draws only the explicit coordinate constants above onto a blank RGBA canvas. It does not derive labels from source colors, copy the Photoshop alpha, or threshold any candidate. The source, alpha, and diagnostic are used only for hash/dimension checks, review rendering, and post-build validation that the selected red strokes target deletion loci.

Expected deliverables in this scout folder and the product `Images/candidates/bg-assisted-v1/image14-labels/` folder:

- `image14-correction-labels-rgba.png` — exact native transparent annotation.
- `image14-correction-labels-overlay-native.png` — native source with correction strokes visible.
- `image14-labels-review-contact-sheet.png` — full-frame and sand-crop visual comparison.
- `image14-labels-metadata.json` — coordinates, reasoning, input hashes, and measured checks.

Structural verification is performed by the build and repeated independently after generation. Visual acceptance remains for a separate judge; this scout does not issue its own verdict.

Focused positive and negative checks (unexpected-color and red/blue-overlap gates):

```bash
python3 -m unittest discover -s tasks/double-marine-bed-wrapper-batch/scouts/image14-labels -p 'test_build_labels.py' -v
```
