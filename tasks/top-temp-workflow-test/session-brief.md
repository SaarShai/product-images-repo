# Top Temp Workflow Test Template Illustration Brief

## Source Evidence

- Template SVG: `tasks/top-temp-workflow-test/source/template.svg`
- Style references:
- `tasks/top-temp-workflow-test/refs/ChatGPT Image Jun 9, 2026, 11_19_45 PM.png`
- `tasks/top-temp-workflow-test/refs/ChatGPT Image Jun 9, 2026, 11_17_34 PM.png`
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

- Match reference object vocabulary, not only palette.
- Match line weight, density, lighting, material language, and shape simplicity.
- Keep recognizable motifs away from production cut lines unless explicitly
  allowed as quiet background.

## Starting Commands

```bash
python3 scripts/svg_geometry_report.py tasks/top-temp-workflow-test/source/template.svg --out tasks/top-temp-workflow-test/svg-geometry-report.md
python3 scripts/build_prompt_pack.py tasks/top-temp-workflow-test
```

## Review Gate

Use `tasks/top-temp-workflow-test/review-judge.md` and
`docs/review-judge-checklist.md` before promoting any candidate.

## Decisions

- `path[0]` is the outer material contour.
- `path[1]` is the large diagonal rounded slot keep-clear.
- `path[2]` is the lower-right round/bolt-like keep-clear.
- This test intentionally checks whether agents use `template-manifest.json`
  instead of assuming every SVG path is paintable material.
