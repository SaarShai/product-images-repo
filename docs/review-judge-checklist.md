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
- the result passes a mask metric but looks clipped, scarred, or unbalanced.

## Cutout Gate

Reject or patch if:

- holes land at model-guessed positions instead of SVG coordinates;
- there are blue blocks, sliced hardware, broken pipes, halos, smeared inpaint,
  jagged local edges, or mismatched lighting near cutouts;
- a crop looks improved but the full-frame panel got worse;
- the clean-line export hides damage visible in artwork-only.

## Style Gate

Reject or restart if:

- only the colors match while the object vocabulary is wrong;
- shape language, line weight, lighting, density, or material rendering misses
  the references;
- a procedural sketch survives under palette changes after user feedback says
  the style is wrong;
- the composition ignores important reference motifs that define the family.

## Production Cut Gate

Reject or revise if recognizable motifs cross production cuts:

- characters, faces, hands, fairies, birds, butterflies;
- flower heads, badges, dials, buttons, logos, windows, doors, lamps, flags;
- roof tips, hardware heads, control modules, or other read-as-object details.

Quiet background may cross a seam only if the task brief says it is acceptable.

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
