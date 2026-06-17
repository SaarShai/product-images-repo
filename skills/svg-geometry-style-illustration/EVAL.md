# SVG Geometry To Style Illustration Eval

This skill is evaluated by workflow behavior, not by a single deterministic
image result.

## Regression Cases

- A user provides an SVG template and style references. The agent must scaffold
  a task, parse geometry, build a visual style packet, and avoid prose-only
  style prompting.
- A rough candidate fits the geometry but looks procedural. The agent must
  choose `WHOLE-PANEL-REDRAW`, not more local locked-geometry repainting.
- An image-generation tool cannot accept reference attachments. The agent must
  prepare the attachment-aware prompt package or stop, and must label any
  prompt-only output as a smoke test.
- A candidate gets a mask `PASS`. The agent must still run visual review before
  acceptance.

## Smoke Commands

```bash
python3 scripts/validate_svg_template_workflow.py
python3 scripts/scaffold_template_task.py validator-smoke \
  --svg assets/templates/two-panel-template.svg \
  --refs assets/reference-images/castle-style-reference.png \
  --dry-run
```

## Evidence Sources

- `tasks/top-temp-workflow-test/checkpoints/style-packet-fit-checkpoint-1-review.md`
- `tasks/top-temp-workflow-test/prompts/redraw-from-bc-experiments-20260616.md`
- `tasks/top-temp-workflow-test/agents/imagegen-artdirector/final-prompt.md`
- `tasks/top-temp-workflow-test/agents/imagegen-artdirector/review.md`
- `wiki/concepts/svg-template-whole-redraw-from-roughs.md`
