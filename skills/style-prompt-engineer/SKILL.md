---
name: style-prompt-engineer
description: "Turn a requested art style (named by the user, or embodied in a reference image) into the best generation prompt sections + the right reference-image inputs. Use before ANY style-sensitive generation or restyle — by Fable or weaker agents."
effort: medium
---

# style-prompt-engineer — style → prompt sections + ref-input plan

Built WITH the user 2026-07-05 (v1 draft). Companion to `reference-style-packet`
(that skill builds the visual packet; this one builds the words + decides how
refs enter the call). Style verdicts always belong to the USER, not the model.

## Rule 0 — substrate ≠ illustration style

Screenery products are printed on PET-felt panels. Product photos therefore show
fiber texture — that is the SUBSTRATE, not the art. Unless the user explicitly
asks for simulated material texture, the prompt describes the ILLUSTRATION style
only, and the anti-clause bans material simulation.
(Lesson: Marriott r4/r5 chased "felt fiber grain" from mockup photos; the actual
target was professional children's-book WATERCOLOR. Whole rounds wasted.)

## The 8 style axes (describe a style, or read one off a reference)

1. medium (watercolor / gouache / ink+wash / flat vector / colored pencil / oil)
2. stroke & edge (loose wet edges / crisp ink outline / soft pencil / hard flat)
3. palette (named colors + saturation level + warm/cool)
4. light (soft ambient / warm rim / flat no-shadow / dramatic)
5. detail density (minimal / storybook-medium / dense decorative)
6. texture ON THE ART (paper grain, pigment granulation, dry-brush) — distinct from substrate
7. figure/architecture treatment (rounded friendly / realistic / geometric)
8. white space & background handling (vignette / full-bleed / isolated on white)

## Procedure

**A. User names a style** → pull the matching snippet block below, fill the 8 axes,
show the assembled style section to the user BEFORE spending on generation.

**B. User gives a reference image** → look at it and write one line per axis (8 lines).
Then BOTH: (a) attach the reference image as an engine input (LAW 0 — always
when the engine supports refs), and (b) compress the 8 lines into the prompt's
style section. Text alone is a fallback, never the default.
Check first: is this ref a PRODUCT PHOTO (mockup, 3D perspective, substrate
visible) or the FLAT ART? Product photo → extract flat-art crops for the packet
(`reference-style-packet`) and apply Rule 0.

**C. Assemble the prompt** in this order:
`[content description] + [style section] + [constraint tail]`
Constraint tail (always): isolated on pure white background; artwork fills the
panel silhouette to its contour; all signs/plaques BLANK, no letters or writing;
`[anti-clause]`.

## Snippet blocks (v1 — extend per user feedback)

### watercolor-storybook (Screenery house default)
style: "professional children's book illustration, hand-painted watercolor,
soft translucent washes with gentle pigment granulation, warm inviting palette,
loose but controlled brushwork, subtle paper texture, soft ambient light,
rounded friendly architecture, storybook charm"
anti: "no photorealism, no 3D render, no felt or fabric or fiber texture, no
embroidery, no plastic sheen, no heavy black outlines, no digital gradient look"

### flat-vector-storybook
style: "flat vector children's illustration, crisp clean shapes, saturated flat
color fills, minimal shading, simple geometric forms"
anti: "no texture, no painterly strokes, no photorealism, no gradients"

### ink-and-wash
style: "loose ink linework with translucent watercolor wash, visible confident
pen strokes, white paper breathing through, limited palette"
anti: "no photorealism, no dense opaque paint, no 3D depth"

### felt-craft (simulated material — ONLY when user explicitly wants it)
style: "handcrafted felt applique artwork, dense wool-felt texture, stitched
edges, soft 3D relief"
anti: "no photorealism, no painting look"

## Engine notes

- Refs as inputs: `falgen.py --mode flux2edit --refs <img...>`; one-pass route
  carries style via LoRA — a LoRA TRAINED ON THE WRONG STYLE (e.g. felt-look
  crops when the target is watercolor) poisons every output; check what the
  LoRA learned before using it.
- Restyle prompts: minimal content words; "repaint in EXACTLY the reference's
  style" + axis lines + "keep composition/framing exactly, same crop" + Rule 0 anti-clause.
- SDXL CLIP caps at 77 tokens — use the short form of the style section.

## Done means

- Style section + anti-clause shown/logged before generation spend.
- Ref-input plan stated (which images attached to which engine parameter).
- After results: style-comparison board vs the intended style refs; user judges.

## Validation (2026-07-05, Marriott r6)

Ref+text vs text-only A/B, same source candidate, same prompt minus the ref:
ref+text → watercolor matched the exemplar, silhouette-IoU 0.9989; text-only →
weaker style AND broken geometry (IoU 0.8352). Board: `tasks/marriott-hospital/outputs/r6-ab-board.jpg`.
Full r6 set (3 panels): IoU 0.987-0.9998, blank signage, style approved-pending-user.

### china-marriott-luminous-storybook (read 2026-07-05 from the 6-screen collection; full read: tasks/marriott-hospital/style-read/STYLE-READ.md)
style: "polished children's picture-book illustration, fine watercolor and gouache
washes over delicate precise linework, fine paper-grain stipple texture, one
harmonized scene palette, rich muted color, luminous glowing windows and lanterns,
soft dusk light, dense storybook detail, architecturally faithful buildings with
gently rounded corners"
anti: "no photorealism, no 3D render, no felt or fabric or fiber texture, no
embroidery, no loose sloppy washes, no heavy black outlines, no neon color, no flat vector look"
note: the collection's fine stipple grain is PAPER texture, not fiber — this is the
style a LoRA previously mis-learned as felt. Signature axis = luminous light.

## Lesson (2026-07-05): the anemia failure mode

A technically-correct medium read can still produce ANEMIC output if the prompt
omits (a) named palette colors + "rich saturated", (b) the warm↔cool interplay
(both poles named), (c) per-surface content density (empty prompt = empty walls).
Ship-gate: hi-DPI crop comparison against the ORIGINAL reference files — a style
verdict from thumbnails or derived copies is void.
