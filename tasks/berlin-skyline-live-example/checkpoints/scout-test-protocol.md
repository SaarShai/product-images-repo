# Berlin Skyline Scout-Test Protocol

Date: 2026-06-16

Purpose: decide whether the next Berlin skyline generation should proceed from
(A) a wireframe/layout map, (B) a rough whole-set composition map, or (C) direct
whole-scene generation from the references and template.

## Inputs

- Approved element sheet: `outputs/generated/20260616-berlin-elements-v2.png`
- Source template: `source/template.svg`
- Style render reference: `refs/WhatsApp Image 2026-06-16 at 01.31.54.jpeg`
- Hotel reference: `refs/Beisheim-Center_und_Potsdamer_Platz_in_Berlin_(2013)_(cropped).jpg`
- Style packet: `style-packet/`

## Scout Inputs

- A wireframe/layout map: `/Users/za/Documents/product images repo/tasks/berlin-skyline-live-example/outputs/reviews/scout-tests/scout-a-wireframe-layout-map.png`
- B rough whole-set composition map: `/Users/za/Documents/product images repo/tasks/berlin-skyline-live-example/outputs/reviews/scout-tests/scout-b-rough-whole-set-map.png`
- C direct reference/template board: `/Users/za/Documents/product images repo/tasks/berlin-skyline-live-example/outputs/reviews/scout-tests/scout-c-direct-reference-board.png`
- B2 seam-safe rough map: `/Users/za/Documents/product images repo/tasks/berlin-skyline-live-example/outputs/reviews/scout-tests/scout-b2-seam-safe-map.png`
- Review contact sheet: `/Users/za/Documents/product images repo/tasks/berlin-skyline-live-example/outputs/reviews/scout-tests/scout-inputs-contact-sheet.png`

## Test A: Wireframe/Layout Map

Question: can a schematic map alone control landmark placement and template
rules well enough for generation?

Pass: panel allocation, saloon arch, low U-Bahn, white sky, and whole landmarks
survive without copying labels/guides.

Fail: model invents generic skyline, reproduces construction marks, or ignores
red/seam safety.

Decision unlocked: use wireframe maps only if obedience is excellent; otherwise
use them only as internal planning artifacts.

## Test B: Rough Whole-Set Composition Map

Question: can a pictorial B+C hybrid map be repainted into one cohesive
watercolor scene rather than a pasted element collage?

Pass: one coherent watercolor/pencil Berlin illustration, all landmarks
recognizable, full hotel lower podium/wing, central bridge/arch and U-Bahn
run-through retained.

Fail: pasted/assembled feel, landmark omissions, or focal details still collide
with production cuts.

Decision unlocked: if B passes, proceed with rough composition map -> whole-set
redraw -> SVG export/verification.

## Test C: Direct Whole-Scene

Question: can direct prompting from references/template control both composition
and style without a map?

Pass: cohesive and complete composition that respects the template as well as B.

Fail: generic Berlin postcard, omissions, cropping, or weak saloon-door/use of
the three-panel template.

Decision unlocked: choose direct generation only if it matches B on template
obedience and beats B on visual cohesion.

## Test B2: Seam-Safe Rough Map

Question: after the first smoke tests, can the repeated Brandenburg Gate seam
crop be prevented by changing the composition map before a full render?

Pass: the entire Brandenburg Gate and Quadriga stay inside the left narrow
panel with quiet clearance before the seam, while the whole-set watercolor
cohesion remains strong.

Fail: the model still crops the gate or the seam-safe layout becomes too weak
or disconnected.

Decision unlocked: proceed only if the next full-generation map is seam-safe;
otherwise redesign the left panel allocation before rendering.

## Judge Rubric

Use `prompts/scout-tests/scout-judge-rubric.md`. Do not promote any scout to a
final candidate. A scout only decides the next method.

## Preliminary Method Expectation

The earlier placement options were too similar and too faint to decide a method.
Scout B is the current expected winner because it gives the model pictorial
composition evidence while still asking for a whole-scene repaint. Scout C is
the control for whether the map is unnecessary. Scout A is mostly a negative
control for whether pure schematics are useful.
