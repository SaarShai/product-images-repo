# Berlin Skyline Scout Test Report

Date: 2026-06-16

Purpose: answer whether the current placement-wireframe route is strong enough to justify a full image-generation pass.

## Artifacts

- `outputs/reviews/scout-tests/scout-0-whole-reference-remix.png`
- `outputs/reviews/scout-tests/scout-1-reference-faithful-rhythm.png`
- `outputs/reviews/scout-tests/scout-2-strong-saloon-arch-hero.png`
- `outputs/reviews/scout-tests/scout-3-continuous-city-band.png`
- `outputs/reviews/scout-tests/scout-tests-contact-sheet.png`

## Pairwise Mean Pixel Difference

- `scout-0-whole-reference-remix.png` vs `scout-1-reference-faithful-rhythm.png`: 3.29 / 255
- `scout-0-whole-reference-remix.png` vs `scout-2-strong-saloon-arch-hero.png`: 3.35 / 255
- `scout-0-whole-reference-remix.png` vs `scout-3-continuous-city-band.png`: 3.35 / 255
- `scout-1-reference-faithful-rhythm.png` vs `scout-2-strong-saloon-arch-hero.png`: 2.20 / 255
- `scout-1-reference-faithful-rhythm.png` vs `scout-3-continuous-city-band.png`: 2.42 / 255
- `scout-2-strong-saloon-arch-hero.png` vs `scout-3-continuous-city-band.png`: 2.49 / 255

Interpretation: the previous placement options were useful inventory maps but too visually similar/faint for a full-generation decision. These scout tests are deliberately bolder; they should be judged by whether one route reads within a few seconds.

## Proceed Criteria

- A route has visibly distinct hierarchy, not just labels.
- Landmarks remain whole within their physical panels.
- Run-through elements read as infrastructure, not cropped focal subjects.
- The saloon arch has either a clear useful role or is intentionally quiet.
- The image-generation input should be a composition map plus style references, not a final crop.
