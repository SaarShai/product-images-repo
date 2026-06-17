# Space np01 front-bottom 02 right panel Template Illustration Brief

## Source Evidence

- Template SVG: `tasks/space-np01-front-bottom-02/source/template.svg`
- Style references:
- `tasks/space-np01-front-bottom-02/refs/ChatGPT Image Jun 9, 2026, 11_17_34 PM.png`
- `tasks/space-np01-front-bottom-02/refs/ChatGPT Image Jun 9, 2026, 11_19_45 PM.png`
- Style packet: `style-packet/` after running
  `python3 scripts/build_reference_style_packet.py tasks/space-np01-front-bottom-02`
- Asset manifest: `asset-manifest.json`
- Template manifest: `template-manifest.json`
- Geometry report: `svg-geometry-report.md`

## Goal

Generate artwork that is composed inside the SVG contour and matches the style
references. The final result must avoid all areas outside the contour and all
internal cutouts or keep-clear zones.

Primary skill: `.codex/skills/svg-geometry-style-illustration/SKILL.md`

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
- If a candidate's geometry/dimensions/location are approved but style is wrong,
  always switch to attachment-aware whole-panel redraw: use the approved geometry
  image only as a composition/negative-space map, attach the real references and
  style-packet sheets, generate a raw coherent redraw, then run SVG checks
  downstream.
- Use the approved geometry image only as a composition/negative-space map.
- Do not use locked-geometry local restyle, palette shifts, packet-crop collage,
  or component compositing as the creative style-adaptation method.
- Match reference object vocabulary, not only palette.
- Match line weight, density, lighting, material language, and shape simplicity.
- Keep recognizable motifs away from production cut lines unless explicitly
  allowed as quiet background.

## Starting Commands

```bash
python3 scripts/svg_geometry_report.py tasks/space-np01-front-bottom-02/source/template.svg --out tasks/space-np01-front-bottom-02/svg-geometry-report.md
python3 scripts/build_reference_style_packet.py tasks/space-np01-front-bottom-02
python3 scripts/build_prompt_pack.py tasks/space-np01-front-bottom-02
```

## Review Gate

Use `tasks/space-np01-front-bottom-02/review-judge.md` and
`docs/review-judge-checklist.md` before promoting any candidate.

## Decisions

- Pending.
