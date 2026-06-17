# Berlin Skyline Live Example Template Illustration Brief

## Source Evidence

- Template SVG: `tasks/berlin-skyline-live-example/source/template.svg`
- Style references:
- `tasks/berlin-skyline-live-example/refs/WhatsApp Image 2026-06-16 at 01.31.54.jpeg`
- `tasks/berlin-skyline-live-example/refs/Beisheim-Center_und_Potsdamer_Platz_in_Berlin_(2013)_(cropped).jpg`
- Style packet: `style-packet/` after running
  `python3 scripts/build_reference_style_packet.py tasks/berlin-skyline-live-example`
- Asset manifest: `asset-manifest.json`
- Template manifest: `template-manifest.json`
- Geometry report: `svg-geometry-report.md`

## Goal

Generate artwork that is composed inside the SVG contour and matches the style
references. The final result must avoid all areas outside the contour and all
internal cutouts or keep-clear zones.

## Geometry Rules

- Treat the SVG as authoritative.
- Identify the outer contour, internal cutouts, slots, dashed safe areas, and
  keep-clear zones before prompting.
- Fill `template-manifest.json` before prompting. If roles are ambiguous, stop
  and inspect the SVG directly.
- Plan safe pockets for motifs/modules before rendering.
- Do not create a generic rectangle and crop, clip, erase, or mask it to fit.
- Use final masks only as export guardrails and verification.

## Style Rules

- Build and inspect a visual style packet before style-sensitive generation.
- Style/image-gen agents should use packet images directly and generate element
  sheets before geometry placement.
- Match reference object vocabulary, not only palette.
- Match line weight, density, lighting, material language, and shape simplicity.
- Keep recognizable motifs away from production cut lines unless explicitly
  allowed as quiet background.

## Starting Commands

```bash
python3 scripts/svg_geometry_report.py tasks/berlin-skyline-live-example/source/template.svg --out tasks/berlin-skyline-live-example/svg-geometry-report.md
python3 scripts/build_reference_style_packet.py tasks/berlin-skyline-live-example
python3 scripts/build_prompt_pack.py tasks/berlin-skyline-live-example
```

## Review Gate

Use `tasks/berlin-skyline-live-example/review-judge.md` and
`docs/review-judge-checklist.md` before promoting any candidate.

## Decisions

- Checkpoint 1 source/composition plan is recorded in
  `checkpoints/checkpoint-1-source-and-composition-plan.md`.
- Visual Checkpoint 1 approval board is recorded in
  `outputs/reviews/checkpoint-1-approval-board.png`.
- Recommended strategy: whole-set composition first, then panel-aware
  refinement, because the U-Bahn, base band, and top contour need to read as one
  family across all three panels.
- Proposed panel allocation:
  - left narrow panel: Fernsehturm + Brandenburg Gate;
  - central door panel: Berliner Dom + Kaiser Wilhelm Memorial Church style
    tower/spire + simplified bridge/viaduct arch;
  - right narrow panel: Ritz-Carlton / Beisheim / Potsdamer Platz high-rise,
    without the optional green Potsdamer traffic-light/clock tower for the
    first candidate.
- Primary run-through element: yellow Berlin U-Bahn low across the set.
- Keep sky/removable background white or very pale paper-white.
- User approved Checkpoint 1 choices `1A, 2A, 3A`: source packet approved,
  landmark roster approved, whole-set-first strategy approved.
- User approved Checkpoint 1 choice `4A`: low U-Bahn run-through,
  bridge/viaduct arch, adaptive top contour, and white/paper-white sky.
- First generation phase: style-matched Berlin skyline element sheet, then
  review before final template placement.
