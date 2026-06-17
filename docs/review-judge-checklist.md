# Review Judge Checklist

Use this checklist for adversarial review of SVG-template-constrained artwork.
It is meant for a human or agent judge who opens the actual output images.

## Evidence To Inspect

- Task brief: `tasks/<task>/session-brief.md`
- Source SVG: `tasks/<task>/source/*.svg`
- Geometry report: `tasks/<task>/svg-geometry-report.md`
- Template manifest: `tasks/<task>/template-manifest.json`
- Candidate artwork: `tasks/<task>/outputs/generated/*.png`
- Artwork-only export: `tasks/<task>/outputs/final/*-artwork-only.png`
- Clean-line or overlay export: `tasks/<task>/outputs/final/*-clean-black-lines.png`
- Debug mask or score JSON: `tasks/<task>/outputs/*/*debug*` or `*.json`
- Cutout crop/contact sheet when the task has holes, slots, or scar-prone areas
- Style reference images
- Style packet: `tasks/<task>/style-packet/style-packet.json`
- Style packet sheets: `tasks/<task>/style-packet/*sheet.png`

## Geometry Gate

Reject or patch if:

- painted pixels escape the SVG-derived contour;
- metadata points at an unexpected template SVG for the task;
- decorative elements cross holes, slots, red/yellow keep-clear areas, or center
  seams;
- final masks visibly chopped through objects that should have been routed
  around geometry;
- the panel is underfilled because a global shift/scale fixed one area while
  damaging another;
- the panel is underfilled because an open SVG path was closed diagonally while
  a sibling polyline/line that completes the bottom or side edge was ignored;
- the result passes a mask metric but looks clipped, scarred, or unbalanced.

## Cutout Gate

Reject or patch if:

- holes land at model-guessed positions instead of SVG coordinates;
- edge sockets, bite notches, tabs, and interlocking shapes are filled as blue
  panel material when the SVG intends them as cutout/blank space;
- there are blue blocks, sliced hardware, broken pipes, halos, smeared inpaint,
  jagged local edges, or mismatched lighting near cutouts;
- a crop looks improved but the full-frame panel got worse;
- the clean-line export hides damage visible in artwork-only.

## Style Gate

Reject or restart if:

- only the colors match while the object vocabulary is wrong;
- the candidate was generated from prose style descriptions while ignoring the
  packet images;
- shape language, line weight, lighting, density, or material rendering misses
  the references;
- the contour and cutout edges look flat, clipped, or mask-cut instead of having
  the reference-like dark blue rim, slight bevel, soft inner shadow, and pale
  highlight;
- a procedural sketch survives under palette changes after user feedback says
  the style is wrong;
- the composition ignores important reference motifs that define the family.

Accept a style-sensitive candidate only when it looks like the generated
elements could have come from the packet crops. Similar blue, red, yellow, or
mint colors are not enough.

## Production Cut Gate

Reject or revise if recognizable motifs cross production cuts:

- characters, faces, hands, fairies, birds, butterflies;
- flower heads, badges, dials, buttons, logos, windows, doors, lamps, flags;
- roof tips, hardware heads, control modules, or other read-as-object details.

Quiet background may cross a seam only if the task brief says it is acceptable.

## Method Routing Gate

Reject further procedural-placement work and request a whole-image redraw when:

- the best candidates already establish usable rough layout/geometry;
- the user accepts B/C-style roughs as the best direction but rejects the final
  look;
- the user approves geometry/dimensions/location and asks only for style
  adaptation;
- failures are cohesion/style failures, not SVG-mask failures;
- pasted sprites, broad crop patches, halos, or collage seams remain visible.

The redraw prompt should attach the rough candidates as composition maps and the
reference/style-packet images as style targets. The raw redraw is not production
fit until a later SVG export/check clears exact contour and cutout geometry.

Reject local `locked-geometry` restyle outputs as the main creative fix when the
problem is reference-style cohesion. They may be diagnostic geometry artifacts,
but they are not the successful style adaptation method.

## Verdicts

Use one verdict:

- `ACCEPT`: geometry, style, and visual crop/full-frame checks pass.
- `LOCAL PATCH`: the main artwork is good and the defect is bounded.
- `PROMPT RESTART`: the method, composition, or style vocabulary is wrong.
- `BLOCKED`: required evidence is missing or tooling cannot inspect the output.

## Review Note Template

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
