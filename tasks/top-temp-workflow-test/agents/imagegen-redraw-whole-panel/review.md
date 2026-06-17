Verdict: PROMPT RESTART

Evidence inspected:
- `tasks/top-temp-workflow-test/agents/imagegen-redraw-whole-panel/inputs/input-contact-sheet.png`
- `tasks/top-temp-workflow-test/agents/imagegen-redraw-whole-panel/generated/method-a-prompt-only-smoke-01.png`
- `tasks/top-temp-workflow-test/agents/imagegen-redraw-whole-panel/review-artifacts/method-a-prompt-only-smoke-01-fit-check-artwork-only.png`
- `tasks/top-temp-workflow-test/agents/imagegen-redraw-whole-panel/review-artifacts/method-a-prompt-only-smoke-01-fit-check-clean-black-lines.png`
- `tasks/top-temp-workflow-test/agents/imagegen-redraw-whole-panel/review-artifacts/method-a-prompt-only-smoke-01-fit-check-debug-mask.png`
- `tasks/top-temp-workflow-test/agents/imagegen-redraw-whole-panel/review-artifacts/method-a-prompt-only-smoke-01-fit-check-metadata.json`
- `tasks/top-temp-workflow-test/agents/style-imagegen-fit/style-imagegen-fit-preview-white.png`
- `tasks/top-temp-workflow-test/agents/style-matte-elements/style-matte-elements-preview-white.png`
- `tasks/top-temp-workflow-test/style-packet/style-exemplar-sheet.png`

Passes:
- The prompt-only smoke image is a real whole-panel redraw rather than a
  procedural sprite placement or crop collage.
- It keeps the large diagonal slot, lower-right round cutout, and bottom center
  void visually blank in the raw generated image.
- The watercolor blue body, irregular ink outline, knobs, sliders, gauge,
  capsule buttons, screw heads, highlights, and shadow pooling are closer to the
  two style references than the more procedural placement passes.
- The local export check reports `PASS` with `outside_nonwhite_pixels: 0`,
  `center_gap_nonwhite_pixels: 0`, and `hex_clear_nonwhite_pixels: 0`.

Failures or risks:
- The available `image_gen` call was prompt-only. It could not accept
  `template.svg`, B/C, the two style targets, or the style-packet sheets as
  actual image inputs.
- The generated image is `1263x1245`, not the template's `1592.1x1570.39`
  viewBox or the expected `1593x1571` raster target.
- The silhouette is visually close but not exact. The clean-line overlay shows
  alignment drift, especially around the right edge, lower-right round cutout,
  and bottom center area.
- The mechanical export `PASS` is a rejection gate only. It does not prove this
  prompt-only smoke image is production-fit, because the exporter masks a white
  background and can hide exact contour drift.

Next move:
- Use `prompt-method-a-whole-panel.md` in an image model that supports image
  attachments or masked image-to-image generation. Attach `template.svg`,
  `input-contact-sheet.png`, B, C, both style references, and the style-packet
  sheets. Request a `1593x1571` output with transparent outside/cutout negative
  space. Then rerun the export fit check and visual judge before considering
  acceptance.
