# Berlin Skyline SVG-Locked Redraw Prompt

Date: 2026-06-16

Purpose: restart from the visually preferred top option while preventing the
image model from redrawing the physical SVG template. Use this prompt with the
SVG-locked composition map:

- `outputs/reviews/dimension-repair/repair-option-3-svg-locked-composition-map.png`

The user-approved top image is visual/style/composition evidence only:

- `refs/user-feedback/20260616-best-option-dimension-drift.png`

## Prompt

```text
Create a rough artwork-only Berlin skyline illustration for a Screenery
3-panel skyline collection.

Use the attached SVG-locked composition map as the geometry/composition map.
Use it only for layout, scale, panel proportions, separator height, and landmark
allocation. Do not copy/paste its element-sheet fragments. Redraw the whole
scene as one cohesive delicate watercolor and colored-pencil illustration.

Use the user-approved best Berlin option only as visual direction: soft
watercolor/pencil, white paper sky, continuous Berlin scene, yellow U-Bahn low,
bridge/viaduct in the center, adapted skyline top-contour idea. It is NOT
geometry authority; its frame is too wide and its bottom sub-panels are too low.

The SVG geometry is locked. Do not redraw, resize, reinterpret, stylize, widen,
compress, or invent the template geometry. The real SVG will be overlaid after
generation. Any generated template guide line is an error.

Output artwork only on a pure white/paper-white background. Do not draw panel
borders, dashed safe margins, red danger zones, green top-contour guides, orange
arch guides, door split lines, knobs, labels, or production strokes.

Preserve the true SVG proportions: the active set is narrower and taller than
the user-approved top image. The middle door panel must not become wider. The
bottom sub-panel region must not be pushed down; the true top/bottom separator
is about 40% down the active template height.

Composition:
- Left narrow panel area: Fernsehturm tall on the left and Brandenburg Gate
  lower, both whole and not split. Gate and Quadriga stay clear of future seam
  and red-zone lanes.
- Center door panel area: Berliner Dom and Kaiser Wilhelm Memorial Church
  tower/spire above; a simplified bridge/viaduct over quiet water/stone echoes
  the saloon-door arch. The bridge arch should echo the SVG arch and must not
  become a huge replacement arch spanning most of the central panel.
- Right narrow panel area: Ritz-Carlton / Beisheim / Potsdamer Platz high-rise
  with full lower podium/base, whole inside the right panel.
- A yellow Berlin U-Bahn train runs low as infrastructure. Use plain yellow body
  over future seams and red-zone lanes; keep doors and windows away from those
  places.
- Keep sky/background completely white or paper-white.

Adaptive top contour: suggest the skyline silhouette through the artwork itself,
following TV tower, Brandenburg Gate dip, Dom dome/cross, church tower, and
hotel crown, but do not draw any green contour line.
```

## Prompt-Only Scout Result

A prompt-only artwork test without the SVG-locked map stopped drawing guide
lines and looked stylistically promising, but drifted toward a generic
rectangular skyline scene. Conclusion: prompt wording alone is not enough; the
next generation must use the SVG-locked map as an image input and then overlay
the real SVG afterward.
