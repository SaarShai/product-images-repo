# Skyline Assets

This folder contains the default template and teaching examples for
skyline/city-scape Screenery image-generation tasks.

## Template

- `city-skyline template.svg`: default three-panel skyline template.
- `city-skyline template.ai`: Illustrator source companion.

Default guide roles in the SVG:

- black strokes: production panel borders, outer contours, door flaps, cut and
  hinge references;
- yellow dashed strokes: safe/margin guides;
- red dashed strokes and rectangles: no-crop or no-focal-feature zones;
- green dashed strokes: temporary top-contour guides to adapt to building tops;
- orange dashed stroke: central saloon-door arch guide.

## Example Roles

- `2 buildings composite - st. paul's cathedral + wesminster abbey.png`:
  example of a two-building composite inside one panel.
- `2 landmarks composite - big ben + london eye.png`:
  example of two iconic landmarks composed into one panel.
- `door panel example - bridge inside door flaps area.png`:
  example of a bridge span fitting the central saloon-door arch generally.
- `princess palace example - door fits in door flaps area.png`:
  example of a doorway/entrance feature supporting the saloon-door arch.
- `example - exaggerated door.png`:
  precedent for modifying building proportions so an entrance complements the
  arch guide.
- `example - landmark (statue) fitting in door flaps area.png`:
  example of a statue/column-like landmark fitting within the arch area.
- `example - bridge runs through panels + top contour tracing buildings shape.png`:
  example of a run-through bridge plus top contour adaptation to skyline
  silhouettes.
- `example of DON'T - specific elements (fairies, birds) cropped.png`:
  counterexample showing recognizable features cropped by cut lines and red
  keep-clear zones.
- `example of DO - specific elements (fairies, birds) not cropped.png`:
  corrected example showing recognizable features moved away from production
  cuts while non-specific wall texture occupies the risky lane.

## Use Rules

- Use these examples as rule evidence, not as mandatory visual style.
- Treat user-supplied references as the style and landmark authority for a
  specific task.
- Keep the default sky/removable background white unless the user explicitly
  asks for a sky background.
