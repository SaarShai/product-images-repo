---
name: reference-style-packet
description: Use when reference images must be turned into a visual style packet for image-generation agents, especially when previous outputs matched geometry but missed the actual art style.
effort: medium
---

# Reference Style Packet

Use this skill before style-sensitive image generation. The goal is to stop
agents from inventing style from prose and make them use the actual reference
images as visual evidence.

## Required Inputs

- Task folder under `tasks/<task>/`.
- Reference images under `tasks/<task>/refs/` or explicit `--refs` paths.
- Current user feedback about style failures.

## Workflow

1. Read `AGENTS.md`, `docs/svg-template-illustration-workflow.md`, and the task
   `session-brief.md`.
2. Build or refresh the packet:

   ```bash
   python3 scripts/build_reference_style_packet.py tasks/<task>
   ```

3. Inspect the generated sheets:
   - `tasks/<task>/style-packet/reference-contact-sheet.png`
   - `tasks/<task>/style-packet/style-exemplar-sheet.png`
4. Read `tasks/<task>/style-packet/style-packet.json` and confirm it names
   attachable source crops, not just text labels.
5. Use `tasks/<task>/prompts/prompt-v2-style-packet-elements-first.md` for
   style/image-gen agents.

## Rules

- Style agents must receive images from the packet, not only prose.
- The packet should include full references, region crops, texture/edge crops,
  and component/accent crops when possible.
- For Screenery watercolor control panels, edge-treatment crops are important:
  agents should see the dark blue rim, slight bevel, soft inner shadow, pale
  edge highlight, and occasional raised lip around outer contours and holes.
- Palette is supporting evidence only. Do not call style matched because colors
  are similar.
- If the packet crops are weak or misleading, regenerate or add manual crops
  before asking for more image generation.
- Keep style generation independent from exact SVG verification. Style agents
  may generate element sheets, or, when rough B/C-style candidates are accepted
  for layout but not final art, they may use those roughs as image inputs for a
  whole-panel redraw/restyle. The SVG exporter/checker verifies exact geometry
  after the redraw.

## Done Means

- The task has `style-packet/style-packet.json`.
- The task has contact/exemplar sheets that were visually inspected.
- The task has a style-agent prompt that lists packet image attachments.
- A judge can reject a candidate for procedural/flat style even when geometry
  metrics pass.
