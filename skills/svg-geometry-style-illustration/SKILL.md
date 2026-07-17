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
SVG geometry -> OUTSET cutouts -> outset contract base -> visual style packet ->
attachment-aware style synthesis (model RAW) -> pick best raw by eye -> visual judge
```

The official end-to-end recipe for this is the "Official Method" section below.
Geometry exactness, when separately required, is verified/exported as a
NON-destructive step that never overwrites the chosen raw.

Do not collapse those steps into one vague prompt. In particular, do not ask an
image-generation agent to "match the style" from prose while the actual
reference images sit unused.

## Official Method — Outset + Keep-Raw (DEFAULT; use this)

This is the canonical, user-confirmed method for these SVG control-panel
illustrations (Screenery space/top panels and the like). Use it by default. It
generates a model RAW directly against an OUTSET contract base and keeps the raw;
it does NOT carve geometry into the raw afterward. The deterministic re-seat
route (`exact_bevel_composite.py`) is a last-resort backstop only — see
Validated Lesson A.

Steps (scripts are in `scripts/`, run from repo root; `T=tasks/<task>`):

1. **Scaffold + geometry report.** Copy the source SVG to `$T/source/template.svg`
   and the style references to `$T/refs/`. Run
   `/usr/bin/python3 scripts/svg_geometry_report.py $T/source/template.svg --out $T/svg-geometry-report.md`
   and confirm the opening count/kinds.
2. **Outset the cutouts** (drift safety — Validated Lesson B):
   `/usr/bin/python3 scripts/outset_cutouts.py $T/source/template.svg --out $T/source/template-outset30.svg --outset 30`
   Buffers every internal cutout outward by `N` user-units (default **30**), outer
   contour verbatim. The real die-cut always uses the ORIGINAL SVG; the outset only
   enlarges the empty keep-clear zone so a drifted painted hole still encloses the cut.
3. **Build the contract base from the OUTSET SVG** (this image is "image 1", the
   layout law): `/usr/bin/python3 scripts/build_trueaspect_base.py --svg $T/source/template-outset30.svg --out $T/outputs/generated/<task>-base-outset30-1440x2560.png`.
   Open it: enlarged holes at the report's positions.
4. **Write the layout-contract prompt** describing the silhouette + each opening's
   position/shape, plus the STYLE block (bright palette, colorful tick-marked
   controls, clean white bg + white side margins). The reference IMAGES are the
   single source of truth for the look and MUST be passed as attachments. A mild
   "keep all hardware clear of the openings" nudge is fine; do NOT try to express
   the outset in prose (prompt-only outset is unreliable — Validated Lesson B).
5. **Generate N raws** (≈6–8), serial + race-safe, nano via
   `scripts/geom_adherence_test.py --model nanobanana --map <outset-base> --prompt <prompt> --refs <ref1> <ref2> --svg <outset-svg> --outdir $T/experiments-outset`
   (or `scripts/subgen.py`). Every output is a first-class `raw.png` — never overwrite it.
6. **Pick the best raw BY EYE** (Validated Lesson C): both openings clean empty
   paper, each fully enclosed by its own bevel rim (no painted edge poking past the
   rim), generous even outset margin, openings stay separate, style matches the
   references. A single bad raw (opening overlap/oversize/merge) is variance —
   regenerate a few more and pick a clean one; do NOT post-process the bad raw.
7. **Deliver the chosen raw + sync ALL results (HARD RULE).** Promote the pick to
   `$T/RESULTS/`. Then copy EVERY result image (all raws/exacts/overlays, not just
   the pick) into the central library by running
   `/usr/bin/python3 scripts/sync_results_images.py` followed by
   `/usr/bin/python3 scripts/sync_results_images.py --check` to VERIFY none are missing.
   Never hand-roll a `cp` loop for this — a silent shell-glob bug once collapsed 8
   variants into one overwritten file and dropped them. No re-seat / `exact.png` in
   the deliverable path.

Confirmed defaults: `--outset 30` for tall narrow space panels; nano (agy) backend;
the trueaspect 1440x2560 letterbox base. Tune `--outset` per template if openings
are very large or very close to the contour.

## Validated Lessons (np01-front-bottom, 2026-06-17)

These three rules are user-confirmed on real deliverables. They override older
guidance where they conflict.

### A. Never RUIN a good raw (it may or may not be the final deliverable)

A model `raw.png` that nails layout + style is valuable. The raw is not always
the final deliverable — but you must NEVER destroy or degrade it. The re-seat
compositor (`scripts/exact_bevel_composite.py` -> `exact.png`) carves openings,
paints navy bevel bands, and erases hardware near openings; it visibly DEGRADES a
good raw (user verdict: "raw was good, you ruined it with exact.png").

- ALWAYS keep `raw.png` untouched and preserved as a first-class candidate.
- Any geometry post-process writes a SEPARATE file (e.g. `exact.png`), never
  overwrites or silently supersedes the raw.
- When the raw already nails layout + style, present it as the result. If a
  downstream step is needed, it must be NON-destructive to the raw.
- Re-seat / `exact_bevel_composite.py` is a LAST-RESORT backstop, not the default.
  If geometry must be enforced, prefer a non-destructive route (below) first.

### B. Absorb cutout drift with an OUTSET — adapt the SVG, not the prompt

Painted cutouts drift by several points. If the empty (paper-white) area equals
the true cutout, drift pushes the real die-cut into painted hardware. Fix: make
the EMPTY keep-clear area LARGER than the cutout.

The outset must arrive as PIXELS in the contract base, not as prose. Tested both:

- **Adapt the SVG (correct):** `/usr/bin/python3 scripts/outset_cutouts.py SRC.svg --out
  OUT.svg --outset N` buffers every internal cutout outward by `N` user-units
  (shapely), outer contour verbatim; rebuild the true-aspect base from `OUT.svg`
  so the layout-contract image shows the enlarged holes. Consistent, controlled,
  exactly `+N` pt, openings stay separate and correctly sized.
- **Prompt-only outset (unreliable — do not rely on it):** telling the model to
  "leave an oversized empty band" produces variable results — oversized one
  opening, MERGED two openings with a white channel, run-to-run drift.

Default `--outset` ~30 user-units for these tall narrow space panels (~1.2% of
panel height) — user-confirmed pick at outset 30. Tune per template; the real cut
always uses the ORIGINAL SVG, the outset only governs the empty zone. A mild
prompt nudge ("keep all hardware clear of the openings") is fine as
reinforcement, but the outset SVG/base is load-bearing.

### C. Geometry comes from the contract base image, then pick from N raws

Generate N source raws (nano via `scripts/geom_adherence_test.py` /
`subgen.py`) against the outset base + reference images, then PICK the best raw
by eye. A single bad raw (e.g. the slot top poking past its bevel) is generation
variance — regenerate a few more candidates and pick a clean one rather than
post-processing the bad one.

**Review EVERY candidate before picking — never a sample.** If you generated
s1..s8, LOOK at all eight; do not eyeball s1/s3/s5 and pick from those. Better
raws routinely sit in the unviewed cells (confirmed miss: np01-front-bottom-02
s6 was the best but was skipped because only s1/s3/s5 were viewed). When showing
the user, show the contender set (or a contact sheet), not just your one pick, so
their eye can catch what yours missed.

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
/usr/bin/python3 scripts/asset_report.py
```

If the task folder does not exist:

```bash
/usr/bin/python3 scripts/scaffold_template_task.py <task> --svg <svg> --refs <refs...>
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
/usr/bin/python3 scripts/build_reference_style_packet.py tasks/<task>
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
/usr/bin/python3 scripts/export_svg_template_fit.py <candidate.png> \
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
- Cutouts are OUTSET by `scripts/outset_cutouts.py` and the contract base is
  rebuilt from the outset SVG (Validated Lesson B); the real cut still uses the
  original SVG.
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
- Ruining/degrading a good `raw.png` — letting a destructive post-process
  (`exact_bevel_composite.py` / `exact.png`) overwrite or supersede it instead of
  preserving the raw as a separate first-class file (Validated Lesson A).
- Trying to outset cutouts with prompt prose instead of an outset SVG/base
  (Validated Lesson B).
- Post-processing one bad raw instead of regenerating clean candidates.
- Asking one agent to solve SVG geometry, style synthesis, exact export, and
  acceptance review without separate gates.
- Keeping a procedural placement pipeline after the user approves geometry but
  rejects style.
