# {{TASK_TITLE}} Review Judge

Use `docs/review-judge-checklist.md` for the full gate.

## Required Evidence

- Source SVG: `{{SVG_PATH}}`
- Geometry report: `svg-geometry-report.md`
- Template manifest: `template-manifest.json`
- Candidate artwork: `outputs/generated/<candidate>.png`
- Overlay/debug/metadata: `outputs/reviews/` or `outputs/final/`
- Style references:
{{REF_LIST}}

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
