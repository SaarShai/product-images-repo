# Space np01 front-bottom 02 right panel Review Judge

Use `docs/review-judge-checklist.md` for the full gate.

## Required Evidence

- Source SVG: `tasks/space-np01-front-bottom-02/source/template.svg`
- Geometry report: `svg-geometry-report.md`
- Template manifest: `template-manifest.json`
- Style packet: `style-packet/style-packet.json`
- Style packet sheets: `style-packet/*sheet.png`
- Candidate artwork: `outputs/generated/<candidate>.png`
- Overlay/debug/metadata: `outputs/reviews/` or `outputs/final/`
- Style references:
- `tasks/space-np01-front-bottom-02/refs/ChatGPT Image Jun 9, 2026, 11_17_34 PM.png`
- `tasks/space-np01-front-bottom-02/refs/ChatGPT Image Jun 9, 2026, 11_19_45 PM.png`

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
