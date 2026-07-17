# Princess narrow panel 02 evidentiary run Review Judge

Use `docs/review-judge-checklist.md` for the full gate.

## Required Evidence

- Source SVG: `tasks/geometry-evidentiary-princess-n02/source/template.svg`
- Geometry report: `svg-geometry-report.md`
- Template manifest: `template-manifest.json`
- Style packet: `style-packet/style-packet.json`
- Style packet sheets: `style-packet/*sheet.png`
- Candidate artwork: `outputs/generated/<candidate>.png`
- Overlay/debug/metadata: `outputs/reviews/` or `outputs/final/`
- Style references:
- `tasks/geometry-evidentiary-princess-n02/refs/princess style 01.png`
- `tasks/geometry-evidentiary-princess-n02/refs/princess style 02.png`

## Verdict

```text
Verdict: ACCEPT | LOCAL PATCH | PROMPT RESTART | BLOCKED

Evidence inspected:
- <path>

Passes:
- <specific pass>

Failures or risks:
- <specific failure or risk>

Next move:
- <one concrete action>
```

## Geometry-Approved Style Rule

If geometry/dimensions/location are accepted but style is rejected, the next move
is `PROMPT RESTART` through attachment-aware whole-panel redraw. Use the approved
geometry as a composition map only; do not accept locked-geometry local restyle,
palette shifts, or packet-crop/component collage as the creative method.

Use approved geometry as a composition map only.
