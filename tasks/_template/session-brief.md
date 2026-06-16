# {{TASK_TITLE}} Template Illustration Brief

## Source Evidence

- Template SVG: `{{SVG_PATH}}`
- Style references:
{{REF_LIST}}
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
python3 scripts/svg_geometry_report.py {{SVG_PATH}} --out tasks/{{TASK_SLUG}}/svg-geometry-report.md
python3 scripts/build_prompt_pack.py tasks/{{TASK_SLUG}}
```

## Review Gate

Use `tasks/{{TASK_SLUG}}/review-judge.md` and
`docs/review-judge-checklist.md` before promoting any candidate.

## Decisions

- Pending.
