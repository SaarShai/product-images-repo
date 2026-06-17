# Space Top Temp Contour-Native Proof

## Source

- Attached contour: `source/top-temp.svg`
- Original file: `/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/space/top-temp.svg`

## Method

This proof follows the corrected contour-first method from the space panel work:

- The SVG contour is the source of truth.
- The first path is treated as the outer part body.
- The second and third paths are treated as internal keep-clear cutouts.
- Decorative modules, pipes, buttons, bolts, and sparkle details are drawn only
  after their masks fit inside a margin-safe paintable region.
- The final body mask is used as an export guardrail only, not to rescue a
  rectangular or generic illustration.

The bottom center rectangular notch is part of the outer contour and is not
paintable material.

## Outputs

- Artwork: `outputs/generated/top-temp-contour-native-v1-artwork.png`
- Template overlay: `outputs/reviews/top-temp-contour-native-v1-template-overlay.png`
- Mask debug: `outputs/reviews/top-temp-contour-native-v1-mask-debug.png`
- Metrics: `outputs/reviews/top-temp-contour-native-v1-metadata.json`
