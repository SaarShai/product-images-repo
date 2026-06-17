---
name: svg-template-style-agent
description: Use for agents that generate or transform visual elements from a reference-style packet before SVG geometry placement. This is intentionally separate from geometry/template-fit agents.
effort: high
---

# SVG Template Style Agent

Use this skill for style/image-generation subtasks where the output should look
like the provided references. Do not solve final SVG placement in this role.

## Inputs To Request

- `tasks/<task>/style-packet/style-packet.json`
- `tasks/<task>/style-packet/reference-contact-sheet.png`
- `tasks/<task>/style-packet/style-exemplar-sheet.png`
- The most relevant crop images listed under `agent_attachments`.
- Any rough candidate images the user or judge identifies as the best available
  composition/layout evidence.
- User feedback about what style missed in previous candidates.

## Job Boundary

Style agents produce style-matched element candidates and, when explicitly
assigned, whole-panel redraw candidates:

- element sheets;
- isolated dials, sliders, buttons, bolts, pins, material patches, edge/shadow
  samples;
- whole-panel redraw/restyle candidates when the assigned method is to repaint a
  rough geometry/layout draft into one coherent reference-style illustration;
- short provenance notes naming which packet crops influenced each element.

Style agents do not:

- draw the final SVG template contour;
- decide which SVG paths are cutouts;
- crop a rectangular illustration into the template;
- paste broad packet crops or isolated sprites and call the collage final art;
- call a result acceptable because geometry metrics pass.

## Geometry-Approved Style Adaptation Rule

ALWAYS use this rule for geometry-to-style adaptation after the user approves
geometry/dimensions/location and asks for style changes.

When the user approves a candidate's geometry, dimensions, location, contour, or
cutout placement but says the style is wrong, do not make a local
`locked-geometry` restyle, packet-crop collage, palette shift, or component
compositing pass.

Treat the approved geometry image as a composition map only. The style agent must
run Whole-Panel Redraw Mode:

Use the approved geometry image only as a composition/negative-space map.

1. Attach the approved geometry candidate as the layout/negative-space map.
2. Attach the original style references plus the style packet/contact sheets.
3. Prompt the image model to repaint the entire object as one coherent
   watercolor illustration; the geometry image is not a pixel source.
4. Save the raw redraw and exact prompt before any SVG registration or cleanup.
5. Hand the raw redraw to a geometry/review agent for exact SVG export/checks.

If the available image tool cannot accept the geometry candidate and style
references as image inputs, prepare the attachment-aware prompt package and stop
or use a tool/model that can accept those images. A prompt-only attempt is not
the successful method.

For Screenery watercolor control-panel work, use the 2026-06-16 prompt package as
the reference method before generating:

- `tasks/top-temp-workflow-test/prompts/redraw-from-bc-experiments-20260616.md`
- `tasks/top-temp-workflow-test/agents/imagegen-redraw-whole-panel/prompt-method-a-whole-panel.md`
- `tasks/top-temp-workflow-test/agents/imagegen-restyle-edit/prompt-package.md`
- `wiki/concepts/svg-template-whole-redraw-from-roughs.md`

If an agent is spawned specifically to adapt approved geometry to the reference
style, assign it this goal shape:

```text
/goal Produce an attachment-aware whole-panel redraw candidate. Use the approved
geometry image only as a composition/negative-space map, attach the actual style
references and style-packet sheets, redraw the whole object as one coherent
watercolor illustration, save the raw redraw and exact prompt, and do not run a
locked-geometry/local restyle or component collage.
```

## Style Gate

Reject and retry if:

- the output is flat vector/UI art rather than watercolor-like art;
- it only copies the palette;
- outlines are too mechanically uniform;
- highlights, shadows, line weight, or object vocabulary do not resemble the
  packet crops;
- generated controls look generic instead of like they could have come from the
  source reference panels.
- a whole-panel candidate lacks the reference edge treatment: dark blue rim,
  slight bevel, soft inner shadow, pale highlights, and occasional raised lip
  around the contour and cutout rims.

## Whole-Panel Redraw Mode

Use this mode when a geometry-clean rough and/or style-closer rough exists but
the result is still rejected as procedural, collaged, or assembled.

1. Attach the roughs as composition maps, plus the original style references and
   the style packet/contact sheets.
2. Prompt the model to redraw the entire object as one watercolor illustration.
   Say explicitly that the roughs are not pixel sources and that sprite/crop
   seams must disappear.
3. Preserve the visible negative-space slots/cutouts as blank white holes, but
   do not claim exact SVG fit from the raw model output.
4. Return the raw redraw plus the exact prompt. A geometry/review agent must run
   the SVG check after the redraw is visually promising.

## Handoff To Geometry Agents

Return:

- the generated element sheet or isolated element files;
- any whole-panel redraw/restyle candidate and the roughs used as inputs;
- the style packet paths used;
- a short style verdict: `REFERENCE-MATCH`, `PARTIAL`, or `RETRY`;
- any element bounds/transparent-background notes that help placement.

The geometry agent then uses `.codex/skills/svg-template-illustration/SKILL.md`
to place accepted elements inside safe pockets and verify cutouts.
