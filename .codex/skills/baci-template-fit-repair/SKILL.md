---
name: baci-template-fit-repair
description: Use when working on tasks/baci-door, Baci door SVG template-fit, hex holes, hole-section scars, or image-generation repairs that must preserve a Screenery door template while fixing local cutout artifacts.
effort: medium
---

# Baci Template-Fit Repair

Use this skill for Baci-door image-generation work when the result is close but
the two hex cutout or hole-section areas are wrong.

## First Principles

- Start from the current task files in `tasks/baci-door/`, not from memory.
- Treat `tasks/baci-door/source/baci-door-updated-20260616.svg` as the current
  authoritative template unless the user provides a newer SVG.
- Verify both path panels and polygon cutouts. Older evidence can miss polygons.
- A geometry pass is not a visual pass. Always inspect the hole crop and the
  full-frame artwork after export.
- If the full panel is good and only the holes are bad, prefer bounded local
  donor repair plus exact SVG cutout cleanup. Avoid broad inpaint loops.

## Recovery Checklist

1. Run `git status --short` and list the newest `tasks/baci-door/outputs/`
   artifacts.
2. Read `docs/baci-door-template-fit.md`.
3. Regenerate or inspect the geometry report:

   ```bash
   python3 scripts/svg_geometry_report.py tasks/baci-door/source/baci-door-updated-20260616.svg --out tasks/baci-door/svg-geometry-report-updated-20260616.md
   ```

4. Confirm exporter metrics on the current candidate with
   `scripts/export_svg_template_fit.py --require-pass`.
5. Make a crop or contact sheet around the polygon cutouts before deciding that
   a candidate is acceptable.

## Repair Pattern

When the full panel is good:

1. Use the model edit result as a donor only inside bounded rectangles around
   the two hole neighborhoods.
2. Keep the original image everywhere outside those rectangles.
3. Resize the donor to the base image dimensions if the model changes size.
4. Run `scripts/fix_baci_hex_holes.py` to erase local bitmap marks and redraw
   exact SVG polygon holes.
5. Run `scripts/export_svg_template_fit.py --require-pass`.
6. Inspect metadata, final crop comparison, artwork-only export, and clean-line
   export.

## Done Means

- Metadata verdict is `PASS`.
- `outside_nonwhite_pixels`, `center_gap_nonwhite_pixels`, and
  `hex_clear_nonwhite_pixels` are all `0`.
- The hole-section crop has no blue blocks, sliced hardware, or obvious repair
  scars.
- The full-frame panel still has the desired composition and is not clipped or
  underfilled by a local/global fix.

## Anti-Patterns

- Repeating prompt-only attempts when the failure is exact cutout placement.
- Treating a path-only geometry report as proof that there are no SVG polygons.
- Calling a candidate done because the mask metrics pass while the hole crop is
  visibly damaged.
- Using a global offset because the hole crop improves, without checking the
  full-frame tradeoff.
