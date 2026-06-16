# Baci Door Template-Fit Repair Notes

These notes capture the 2026-06-16 Baci-door sessions where the hard problem
was not general style quality, but getting the two hex cutout areas to look
right while still matching the SVG template exactly.

## Source Of Truth

- Active task folder: `tasks/baci-door/`.
- Authoritative updated SVG: `tasks/baci-door/source/baci-door-updated-20260616.svg`.
- Original Baci SVG: `tasks/baci-door/source/baci-door.svg`.
- Session evidence source used in the accepted repair, possibly ephemeral:
  `/Users/za/Downloads/Image (3).png`.
- Main tooling:
  - `scripts/export_svg_template_fit.py`
  - `scripts/fix_baci_hex_holes.py`
  - `scripts/svg_geometry_report.py`

Treat SVG geometry as authoritative. The template has two panel paths and two
polygon cutouts. If a report, screenshot, or generated image disagrees with the
SVG polygons, inspect the SVG or run the exporter/parser again before generating
more variants.

## Learned Failure Modes

- Prompt-only holes can look plausible while landing at the wrong coordinates.
- Exact SVG cutouts can still leave visible scars when the generated artwork put
  pipes, brackets, shadows, or blue blocks through the target hole area.
- Generic inpaint can pass the mask metrics while looking worse around the hole
  sections.
- A global placement offset can make the hole crop look cleaner but damage the
  full-frame fit by clipping or underfilling the panels.
- A geometry `PASS` is only a mechanical gate. The crop and full-frame visual
  review still decide whether the candidate is usable.

## Preferred Repair Loop

1. Recover the current task state with `git status --short`, recent session
   transcripts if relevant, and the latest `tasks/baci-door/outputs/` files.
2. Confirm that the SVG includes both path panels and polygon cutouts:

   ```bash
   python3 scripts/svg_geometry_report.py tasks/baci-door/source/baci-door-updated-20260616.svg --out tasks/baci-door/svg-geometry-report-updated-20260616.md
   ```

3. If the full panel is close and only the hole sections are wrong, do a bounded
   local repair. Use any model edit as a donor only inside small rectangles
   around the hole neighborhoods, and keep the original image everywhere else.
4. Normalize any generated donor back to the base image dimensions before
   compositing. In the accepted run the donor returned one pixel short.
5. Run exact SVG cutout cleanup after the bounded repair:

   ```bash
   python3 scripts/fix_baci_hex_holes.py \
     tasks/baci-door/outputs/generated/20260616T071500Z-baci-door-hole-sections-bounded-imagegen-v1.png \
     --template-svg tasks/baci-door/source/baci-door-updated-20260616.svg \
     --out tasks/baci-door/outputs/generated/20260616T071500Z-baci-door-hole-sections-bounded-exact-hex-v1.png \
     --pad 34 \
     --dilate 8 \
     --inpaint-radius 4 \
     --stroke-width-units 2.0
   ```

6. Export with required template-fit checks:

   ```bash
   python3 scripts/export_svg_template_fit.py \
     tasks/baci-door/outputs/generated/20260616T071500Z-baci-door-hole-sections-bounded-exact-hex-v1.png \
     --template-svg tasks/baci-door/source/baci-door-updated-20260616.svg \
     --out-dir tasks/baci-door/outputs/final \
     --prefix 20260616T071500Z-baci-door-hole-sections-bounded-exact-hex-v1-svg-fit \
     --require-pass
   ```

7. Check both the metadata and the visual files:

   ```bash
   jq '.metrics' tasks/baci-door/outputs/final/20260616T071500Z-baci-door-hole-sections-bounded-exact-hex-v1-svg-fit-metadata.json
   ```

   Review the final crop comparison and both exported variants:

   ```text
   tasks/baci-door/outputs/reviews/20260616T071500Z-hole-section-final-crop-comparison.png
   tasks/baci-door/outputs/final/20260616T071500Z-baci-door-hole-sections-bounded-exact-hex-v1-svg-fit-artwork-only.png
   tasks/baci-door/outputs/final/20260616T071500Z-baci-door-hole-sections-bounded-exact-hex-v1-svg-fit-clean-black-lines.png
   ```

## Accepted Checkpoint

The user accepted the latest bounded repair as good enough in session
`019ecf3e-a8e8-7a21-8d48-1d05455c9d2c`.

Final metadata reported:

```text
verdict: PASS
output_dimensions: 923x1704
panel_coverage_pct: 74.49
outside_nonwhite_pixels: 0
center_gap_nonwhite_pixels: 0
hex_clear_nonwhite_pixels: 0
hex_clearance_px: 4
```

## Future Prompt Rule

For a fresh generation, do not ask the model to draw final holes. Ask it to keep
quiet, mechanical-looking material around the two SVG polygon neighborhoods and
let the SVG/export tooling own the final cutouts.
