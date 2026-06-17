# Image-Gen Smoke Test Prompt

This prompt was used for one small live image-generation smoke test.

## Tool Limitation

The available `image_gen` tool exposed a prompt-only interface. It could use the
style packet exemplar sheet and reference panel images already attached in the
chat, but it did not expose a way to attach the exact 6 to 10 crop files listed
in Prompt A. The result was copied from the Codex generated-image cache to:

- `tasks/top-temp-workflow-test/agents/style-prompt-lab/imagegen-smoke-test-01.png`

This is therefore a useful visual smoke test, not a complete test of the
crop-selection workflow.

## Prompt Sent

```text
Using the attached style packet exemplar sheet and reference panel images in this chat as the visual source of truth, generate a small isolated element sheet, not a final panel composition. Create separate watercolor control-panel parts on a clean white background with generous spacing: 2 rounded capsule buttons, 2 short slider rails with tiny square colored nubs, 1 round blue-rim dial with pale face and tick marks, 3 vertical colored pins with dark blue base washers, 2 tiny screw heads, and 1 blue watercolor edge/texture swatch. Match the actual packet look: friendly rounded shapes, blue ink outlines, hand-painted uneven edges, watercolor granulation, soft upper-left highlights, and shadow pooling under raised controls. Do not include text labels, arrows, a full blue panel, SVG contour, diagonal slot, yellow safe area, or template cutouts. Do not make flat vector icons, glossy app UI, photoreal metal, or dark machinery.
```
