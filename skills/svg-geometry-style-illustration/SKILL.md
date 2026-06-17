---
name: svg-geometry-style-illustration
description: Use when an agent must produce an SVG-template-constrained illustration that both fits exact contour/cutout geometry and adapts to the actual attached reference image style. Orchestrates geometry agents, style-packet/style-imagegen agents, whole-panel redraw, and review judges.
effort: high
---

# SVG Geometry To Style Illustration

Use this skill for end-to-end SVG template illustration work where the output
must satisfy both constraints:

- exact product geometry from an SVG contour, including internal cutouts,
  sockets, slots, keep-clear zones, and no-focal-motif areas;
- visual style adapted from actual reference images, not from remembered style
  adjectives.

This is an orchestration skill. It deliberately delegates specialized work to:

- `.codex/skills/svg-template-illustration/SKILL.md` for geometry parsing,
  safe-pocket planning, placement, export, and mask verification;
- `.codex/skills/reference-style-packet/SKILL.md` for converting references
  into attachable visual evidence;
- `.codex/skills/svg-template-style-agent/SKILL.md` for style-matched element
  sheets and attachment-aware whole-panel redraws;
- `.codex/skills/svg-template-review-judge/SKILL.md` for accept, patch,
  restart, or blocked decisions.

## Required Reading

1. Read `AGENTS.md`.
2. Read `docs/svg-template-illustration-workflow.md`.
3. Read `docs/review-judge-checklist.md`.
4. Read the four delegated skills listed above.
5. If this is Screenery watercolor control-panel work, read:
   - `wiki/concepts/svg-template-whole-redraw-from-roughs.md`
   - `tasks/top-temp-workflow-test/prompts/redraw-from-bc-experiments-20260616.md`
   - `tasks/top-temp-workflow-test/agents/imagegen-artdirector/final-prompt.md`
   - `tasks/top-temp-workflow-test/agents/imagegen-artdirector/review.md`

## Core Rule

The winning pattern is:

```text
SVG geometry -> safe composition map -> visual style packet -> attachment-aware
style synthesis -> exact SVG export/check -> visual judge
```

Do not collapse those steps into one vague prompt. In particular, do not ask an
image-generation agent to "match the style" from prose while the actual
reference images sit unused.

## Routing Decision

Choose the route from evidence, then write it down in the task notes.

Use `ELEMENTS-FIRST` when:

- no acceptable layout exists yet;
- the current bottleneck is missing reference-style controls, motifs, texture
  samples, or material fragments;
- the geometry is complex enough that a deterministic geometry agent should own
  placement.

Use `WHOLE-PANEL-REDRAW` when:

- a rough candidate already proves useful geometry, dimensions, placement, or
  negative-space logic;
- the user approves geometry/location but rejects style;
- placement candidates pass masks but look procedural, assembled, collaged, or
  sprite-based;
- the style problem is cohesion, object vocabulary, edge treatment, or material
  language.

Use `LOCAL-PATCH` only after:

- the raw redraw is visually strong;
- the remaining defect is bounded;
- the patch can be checked against the exact SVG mask and reviewed in full
  frame plus cutout crops.

Use `PROMPT-RESTART` when:

- the image was designed as a rectangle and clipped later;
- style came from prose instead of attached style references or style-packet
  sheets;
- the available tool cannot accept required image inputs and the attempt would
  become prompt-only;
- repeated local fixes are accumulating halos, scars, or incoherent lighting.

## Workflow

### 1. Recover And Scaffold

Run:

```bash
git status --short
python3 scripts/asset_report.py
```

If the task folder does not exist:

```bash
python3 scripts/scaffold_template_task.py <task> --svg <svg> --refs <refs...>
```

Record the task folder, source SVG, style references, and latest user feedback
in `tasks/<task>/session-brief.md`.

### 2. Geometry Agent: SVG To Safe Map

Assign a geometry agent this goal shape:

```text
/goal Parse the SVG template as the authoritative geometry source. Produce a
geometry report, fill template-manifest.json, identify outer contours, internal
cutouts, sockets/notches, keep-clear zones, and safe pockets, then create one
or more composition maps/roughs that already avoid forbidden areas. Do not
solve final visual style and do not rely on final clipping as the composition
method.
```

Required outputs:

- `tasks/<task>/svg-geometry-report.md`
- filled `tasks/<task>/template-manifest.json`
- one or more rough composition maps under `outputs/generated/` or
  `outputs/reviews/`
- overlay/debug artifacts showing outer contour and cutout interpretation

Geometry check:

- no diagonal auto-closing of open SVG paths until sibling lines/polylines have
  been inspected;
- sockets, bite notches, tabs, holes, and slots are negative space unless the
  SVG/task evidence proves otherwise;
- recognizable motifs do not cross cut lines or internal holes in the rough.

### 3. Style Packet Agent: References To Visual Evidence

Build the packet:

```bash
python3 scripts/build_reference_style_packet.py tasks/<task>
```

Assign a style-packet/style agent this goal shape:

```text
/goal Build and inspect a style packet from the actual reference images. Select
the smallest high-signal attachment set needed for the next generation pass:
full references, contact/exemplar sheets, edge-treatment crops, body texture
crops, and component/accent crops. Do not describe style from memory.
```

Required outputs:

- `tasks/<task>/style-packet/style-packet.json`
- `tasks/<task>/style-packet/reference-contact-sheet.png`
- `tasks/<task>/style-packet/style-exemplar-sheet.png`
- a short note naming the attachment set for the next image-generation agent

Style packet check:

- full-reference context is present;
- crops show material texture, line/edge treatment, lighting, and object
  vocabulary;
- the selected attachment set is small enough to focus the generator, usually
  6 to 10 images/crops plus any rough maps.

### 4. Choose The Creative Pass

#### Elements-First Mode

Use this when the task still needs a library of reference-style parts before
final placement.

Assign the style image-generation agent:

```text
/goal Generate an isolated element sheet from the actual style packet images.
Produce reference-style controls/motifs/material samples with transparent or
clean backgrounds. Do not solve final SVG placement. Return a style verdict:
REFERENCE-MATCH, PARTIAL, or RETRY.
```

Then assign the geometry agent:

```text
/goal Place only REFERENCE-MATCH or strong PARTIAL elements into SVG-derived
safe pockets. Reject unsafe placements before final export. Produce overlay,
debug mask, metadata, and a judge-ready review packet.
```

Reject the result if it reads as pasted sprites, broad crop collage, or
procedural assembly. If the layout is good but the look is wrong, route to
Whole-Panel Redraw Mode.

#### Whole-Panel Redraw Mode

This is the required route when geometry is accepted but style is wrong.

Use the approved geometry image only as a composition/negative-space map.

Assign the image-generation agent:

```text
/goal Produce an attachment-aware whole-panel redraw candidate. Use the
approved geometry image only as a composition/negative-space map. Attach the
original style references, style-packet sheets, and selected crops. Redraw the
whole object as one coherent illustration in the reference style. Save the raw
redraw and exact prompt. Do not run locked-geometry local restyle, palette
shift, packet-crop collage, or component compositing as the creative pass.
```

Prompt requirements:

- say that rough geometry images are composition maps, not pixel sources;
- attach actual reference/style-packet images;
- ask for one coherent fresh illustration, not a collage;
- preserve the visible negative spaces from the map;
- do not claim exact SVG fit from the raw model output;
- record the exact prompt and attachment list under `tasks/<task>/prompts/` or
  the agent folder.

For watercolor control panels, include the proven edge language: dark blue rim,
slight bevel, soft inner shadow, pale edge highlight, subtle rim/lip around
outer contours and cutout rims, soft watercolor granulation, and raised rounded
controls with pooled shadows.

If the image tool cannot accept the rough map and style references as image
inputs, stop after preparing the attachment-aware prompt package. A prompt-only
substitute is a test artifact, not the successful method.

### 5. Exact SVG Export And Cleanup

After a visually promising raw redraw exists, hand it back to a geometry agent:

```text
/goal Register/export the visually promising raw redraw against the exact SVG
template. Use masks as export/check guardrails only. Produce artwork-only,
overlay/clean-line, debug mask, metadata, and cutout crop artifacts. Report
whether defects are bounded enough for local patch or require prompt restart.
```

Use available task-specific exporters, for example:

```bash
python3 scripts/export_svg_template_fit.py <candidate.png> \
  --template-svg tasks/<task>/source/template.svg \
  --out-dir tasks/<task>/outputs/final \
  --prefix <candidate-prefix> \
  --require-pass
```

A mechanical pass is not approval. It only means the candidate is worth visual
review.

### 6. Review Judge

Assign the judge:

```text
/goal Judge this candidate against the SVG, template manifest, overlay/debug
artifacts, cutout crops, original references, and style packet. Inspect the
actual images. Return ACCEPT, LOCAL PATCH, PROMPT RESTART, or BLOCKED, with one
concrete next move.
```

The judge must inspect:

- source SVG and filled manifest;
- raw redraw or generated element/placement image;
- artwork-only export;
- overlay/clean-line export;
- debug mask or score JSON;
- cutout crops for holes/slots/scar-prone areas;
- original references and style-packet sheets.

## Checklists

### Before Image Generation

- Source SVG is copied or pinned in the task folder.
- Geometry report exists.
- `template-manifest.json` names outer contours, cutouts, keep-clear zones, and
  safe pockets.
- Style packet exists and has been visually inspected.
- The prompt includes actual image attachments, not only adjectives.
- The selected route is written as `ELEMENTS-FIRST`, `WHOLE-PANEL-REDRAW`,
  `LOCAL-PATCH`, or `PROMPT-RESTART`.

### Before Accepting A Candidate

- Candidate was designed or redrawn from SVG geometry, not rectangle-clipped.
- Cutouts and outside contour are clean in overlay/debug artifacts.
- Recognizable motifs do not cross production cuts.
- Style matches object vocabulary, rendering, edge treatment, lighting, shape
  simplicity, and density from the references.
- The result looks like one coherent image, not pasted sprites or crop collage.
- A judge inspected actual images and returned `ACCEPT`.

## Done Means

- The task folder contains the source SVG, references, style packet, geometry
  report, filled manifest, prompt package, raw candidate, exact export/check
  artifacts, and review note.
- The final note states the route used and why.
- Any successful style adaptation used actual reference/style-packet image
  inputs.
- Exact geometry was checked after style synthesis.
- The next step is explicit: accept, local patch, prompt restart, or blocked.

## Anti-Patterns

- Prose-only style transfer.
- Prompt-only substitute for an attachment-aware method.
- Locked-geometry local repaint as the main creative pass after the user asks
  for style adaptation.
- Broad packet-crop collage.
- Calling a metric `PASS` production approval.
- Asking one agent to solve SVG geometry, style synthesis, exact export, and
  acceptance review without separate gates.
- Keeping a procedural placement pipeline after the user approves geometry but
  rejects style.
