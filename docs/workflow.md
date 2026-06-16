# Image Generation Workflow

1. Add source references under `assets/`.
2. Write one task brief under `tasks/<task>/session-brief.md`.
3. Keep prompt variants under `tasks/<task>/prompts/`.
4. Run `python3 scripts/asset_report.py` before generating.
5. Generate one output per prompt variant with the same references.
6. Save outputs in `tasks/<task>/outputs/generated/`.
7. Review each output against geometry, style, contour, and no-feature rules.
8. Promote the observed failures into the next prompt revision.
9. For die-line tasks, keep the template fixed and test artwork scale/position
   under the fixed overlay before generating more prompt variants.
10. Score candidate placement recipes with `scripts/score_template_fit.py`.
11. Export curated handoff candidates with `scripts/export_composite.py`.
12. Do a visual/adversarial review of the top scored candidates before handoff.
13. Write durable lessons to `wiki/` when user feedback changes the production
    rule, review gate, or repeatable command sequence.

For die-line work, use SVG geometry as authoritative when available. Raster
diagrams are useful visual explanations but should not be treated as CAD-true.

Current castle-panel lesson: use prompting for style and composition, then use
compositing/layout for exact side gutters, bottom gap, slot clearance, and
production-line overlays. Prompt wording got close, but fixed-template placement
was more reliable for the final margin fit.

Use `tasks/castle-panels/CURRENT.md` as the canonical current-state file. Older
review notes are evidence, not the source of truth for the latest candidate.

Latest castle-panel checkpoint: V6 and V7 are both useful modes. Use V9A when
the center should remain empty. Use V9B when the center should contain a quiet
"no elements" background such as a plain wall. Both prompts keep
birds/butterflies out of the middle rectangles and keep fairies or other focal
motifs away from the horizontal top-bottom split.

The scorer is a first gate, not a final judge. It can rank side/bottom gutters,
center fill, red-zone detail, and cutline-detail risk, but it cannot prove
whether a specific motif is a fairy, flower head, window, roof tip, or other
forbidden semantic element.

Session-learned implementation rule: use the fixed-template loop in
`wiki/concepts/castle-panel-template-cut-bands.md`. Prompt for composition, then
use scoring/export tooling for placement, and finish with semantic review. A
scored `PASS` is not production approval until a human/adversarial review clears
recognizable motifs around the center rectangles, horizontal split, side
gutters, and any custom contour.

## Screenery contour-designed artwork

For Screenery templates with yellow dashed safe areas and internal cutouts, do
not generate or draw a generic rectangular illustration and crop it to the
outline. The user rejected that approach because it makes the result look cut
down to fit instead of designed for the part.

Use a contour-first method instead:

1. Parse the SVG contour and cutout geometry.
2. Derive safe pockets where artwork can live.
3. Place each decorative module, pipe, figure, or detail inside those pockets
   before rendering.
4. Use final clipping/masking only as an exact-edge export guard.
5. Verify both final pixels and raw decorative-element masks avoid cutouts and
   outside areas.

Do not confuse geometry success with style success. If template metrics pass but
the visual language misses the references, do not keep recoloring the same
sketch. Restart the composition from the reference images because style depends
on object vocabulary, shape simplicity, lighting, and rendering language, not
only palette.

For reusable SVG-template illustration tasks, use the canonical workflow in
`docs/svg-template-illustration-workflow.md`, the judge checklist in
`docs/review-judge-checklist.md`, and the skill entrypoints:

```text
.codex/skills/svg-template-illustration/SKILL.md
.codex/skills/svg-template-review-judge/SKILL.md
```

Use `scripts/scaffold_template_task.py` to create task packets that preserve the
SVG, references, prompts, generated outputs, reviews, final candidates, and
judge notes in predictable locations.

## Baci-door hole-section repair

The 2026-06-16 Baci-door sessions added a second fixed-template lesson:
template metrics and visual quality can diverge around tiny cutouts. Use
`docs/baci-door-template-fit.md` and
`.codex/skills/baci-template-fit-repair/SKILL.md` when working in
`tasks/baci-door`.

Core rule: SVG polygon cutouts own the final hole geometry. Prompting can
reserve quiet mechanical material around those coordinates, but the model should
not be trusted to draw final holes. If the full panel is already good, repair
only bounded hole neighborhoods, normalize donor image size, run
`scripts/fix_baci_hex_holes.py`, export with
`scripts/export_svg_template_fit.py --require-pass`, then inspect both the crop
and full-frame outputs.

For Baci-door, a `PASS` means no painted pixels outside the template, center
gap, or hex-clearance masks. It does not mean the hole sections look good.
Promote a candidate only after both the metadata and the visual crop/full-frame
review are clean.
