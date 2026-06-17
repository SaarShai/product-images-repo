---
name: svg-template-review-judge
description: Use when judging, reviewing, scoring, or deciding whether to accept, patch, or restart SVG-template-constrained illustration candidates.
effort: medium
---

# SVG Template Review Judge

Use this skill whenever a generated or repaired candidate must be reviewed
against an SVG template, cutout geometry, style references, or production
handoff standard.

## Required Inputs

- Source SVG path.
- Candidate artwork path.
- Overlay/debug image path when available.
- Metadata/score JSON when available.
- Style reference paths.
- Style packet paths when available.
- Task brief or prompt path.

If any of these are missing, say what is missing and judge only the evidence you
can actually inspect.

## Non-Negotiable Review Behavior

- Inspect the actual images with an image-viewing tool when available.
- Read the metadata, but do not use it as a substitute for visual review.
- Compare artwork-only, clean-line/overlay, debug mask, and cutout crops when
  the task has holes, slots, or scars.
- State whether the next best move is `ACCEPT`, `LOCAL PATCH`, `PROMPT RESTART`,
  or `BLOCKED`.

## Checklist

Geometry:

- No visible paint outside the SVG contour.
- No decorative element crosses internal cutouts, slots, dashed safe areas, or
  keep-clear zones.
- Final masks look like exact export guardrails, not like a visible rescue crop.
- Side gutters, bottom anchoring, center slots, and seams match the task brief.

Cutouts and Scars:

- Holes are at the SVG coordinates, not model-guessed coordinates.
- No blue blocks, sliced hardware, broken outlines, halos, smeared inpaint, or
  abrupt local lighting changes around cutouts.
- If a crop passes but the full frame is damaged, reject or restart.

Style:

- Object vocabulary matches the references, not only the palette.
- Style-sensitive candidates used visual style-packet images rather than prose
  descriptions alone.
- Shape simplicity, line weight, lighting, density, and material language match
  the references.
- For watercolor control-panel work, edge treatment matches the references:
  dark blue rim lines, slight bevel, soft inner shadow, pale highlights, and
  optional subtle rim/lip around outer contours and cutout rims.
- Important motifs are not cropped by product cuts. Quiet background may cross a
  seam only when the task brief allows it.

Method Evidence:

- The task records a geometry report or explicit SVG interpretation.
- The composition was planned in safe pockets before final masking.
- If rough B/C-style candidates were the best available evidence, the task tried
  a whole-image redraw/restyle prompt before more procedural placement work.
- Patch vs restart was decided from evidence, not momentum.

## Verdict Format

Use this exact shape in review notes:

```text
Verdict: ACCEPT | LOCAL PATCH | PROMPT RESTART | BLOCKED
Evidence inspected:
- <path>
- <path>

Passes:
- <specific pass>

Failures or risks:
- <specific failure or risk>

Next move:
- <one concrete action>
```

## Task-Specific Cues

- Baci-door: `PASS` requires zero outside, center-gap, and hex-clear pixels, but
  acceptance still requires clean hole crops and clean full-frame panels.
- Castle panels: scorer `PASS` is only ranking evidence; still check birds,
  butterflies, fairies, flower heads, windows, roof tips, and other recognizable
  motifs around cut bands.
- Space/control panels: reject clipped rectangular compositions even when masks
  pass. Prefer reference-style-packet restarts when procedural machinery
  survives palette or local restyling.
