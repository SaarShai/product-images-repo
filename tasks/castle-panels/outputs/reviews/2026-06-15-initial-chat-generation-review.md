# Initial Prompt Test Review - 2026-06-15

The three prompt variants were generated in chat using the available PNG
references only. No SVG was available, so this pass tested prompt behavior rather
than production geometry fidelity.

## Prompt A - Strict Geometry-First

Strengths:
- Strong watercolor castle style match.
- Clear central slot.
- Custom top contour attempted.
- Good amount of fairytale detail.

Failures:
- Template geometry was reinterpreted instead of preserved.
- Panel proportions and notch geometry drifted from the raster template.
- Multiple focal elements are close to no-feature / divide-sensitive areas.
- The output behaves like a plausible redesigned die-line, not an exact fitted
  production result.

## Prompt B - Balanced

Strengths:
- Best all-around visual balance.
- Castle skyline contour feels more intentional.
- Good style match and pleasing composition.

Failures:
- Still morphs the die-line.
- Focal elements remain too close to protected regions.
- The central slot and divide are cleaner than average but not CAD-reliable.

## Prompt C - Contour-First

Strengths:
- Strongest custom contour behavior.
- Good upper skyline variation.
- Style remains close to the reference.

Failures:
- Most likely to loosen exact geometry because contour priority dominates.
- More focal elements near the divide and outer margins.
- Still needs vector-mask enforcement for production use.

## Main Learning

Prompt wording alone is not enough for exact die-line work when the model only
receives raster references. The model can imitate the design intent but will
redraw the template. For production, use a two-stage workflow:

1. Use the image model to generate the watercolor artwork inside a conservative
   safe-area composition.
2. Apply the SVG paths afterward as the exact vector cut line, slot, divide, and
   mask overlay.

## Next Prompt Direction

The next prompt should be "artwork-inside-mask-first" rather than asking the
model to invent final production lines. The model should avoid drawing the black
die-line itself unless a later vector compositing step is not available.
