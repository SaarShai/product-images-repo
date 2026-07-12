# Visual rationale — sparse hard-case corrections

Diagnosis was limited to the two named source PNGs, the two automatic RGBA candidates, their four-background review boards, and native-resolution crops derived directly from those images. No annotation, benchmark verdict, verifier output, prior failure list, background-removal pipeline, or benchmark was used.

## image15

The four-background candidate visibly cuts the lower silhouette upward through the authored sand/watercolor wash. Native bottom-left, bottom-center, and bottom-right crops show colored granulation, sand marks, and watercolor texture continuing below the candidate alpha edge; the uniform outer cream paper begins only after that authored fade.

The overlay therefore uses eleven five-pixel red polylines distributed across the visibly textured wash. They are samples, not a filled mask. The candidate-alpha cross-check finds 86.68% of red pixels below alpha 64; the remainder touches low-edge texture or already-retained foreground while remaining semantically foreground.

No blue label was added. Native branch/kelp/coral gap crops show the clear paper openings already changing to magenta, gray, and black with the review backgrounds. The pale white/blue patches that remain near the side sprigs are also present as authored bubble/foam marks in the source. Labeling those blue would remove foreground; ambiguous rims remain alpha-zero unknown.

## sample08

The main silhouette, authored base wash, coral gaps, and kelp gaps hold across the four review backgrounds. Three small painted blue bubbles visible in the source disappear entirely on the candidate backgrounds, at approximately `(433, 346)`, `(931, 337)`, and `(1120, 462)`. The overlay marks only those locations with small red disks.

No blue label was added. The visually checked enclosed branch and kelp openings are already transparent, while the pale circular patch behind the far-right sprigs is an authored watercolor rock/foam form visible in the source. Edge translucency is intentionally left unknown.

## Review images

- `diagnostics/correction-previews/image15-source-candidate-preview.png`: source and candidate-on-magenta with the red correction strokes.
- `diagnostics/correction-previews/sample08-source-candidate-preview.png`: source and candidate-on-magenta with the three missed-bubble corrections.

## Independent verdict

Pending independent read-only vision and structural validation.
