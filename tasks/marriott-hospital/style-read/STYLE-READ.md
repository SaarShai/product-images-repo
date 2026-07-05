# China Marriott collection — style read (skill: style-prompt-engineer, Procedure B)

Read from flat-art crops of all 6 screens (`china-marriott-art-crops.jpg`), frames/substrate excluded (Rule 0).

## 8-axis read

1. **Medium** — watercolor + gouache washes over fine precise linework; polished picture-book
   illustration. NOT loose wet-on-wet: washes are controlled and even, with a fine stipple grain
   (pigment on textured paper). This stipple is what the LoRA mis-learned as "felt fiber".
2. **Stroke & edge** — delicate thin outlines; precise small details; no bold cartoon lines.
3. **Palette** — one harmonized scene-palette per screen: Hospital white/sky-blue/leaf-green;
   Police navy/cream; Fire brick-red/sand; Kitchen celadon/cream/brass; Water Cube luminous
   night-blues; Birds Nest dusk apricot/lavender. Rich but muted-saturated; never neon.
4. **Light — the signature axis** — LUMINOUS: glowing windows, lanterns, lamp halos, warm interior
   light against cooler ambient; dusk/magic-hour mood on several screens; soft shadows.
5. **Detail density** — HIGH. Dense small objects (teapots, shelves, flower beds), patterned tiles,
   foliage with individually painted leaf clusters.
6. **Texture on the art** — fine even stipple/paper grain everywhere; no impasto, NO fiber strands.
7. **Architecture** — faithful but friendly: real Beijing landmarks (Birds Nest, Water Cube)
   accurately structured with gently rounded corners.
8. **Background** — full-bleed to the die-cut contour; sky reaches the panel top (scalloped cloud tops).

## Style section (prompt snippet: `china-marriott-luminous-storybook`)

style: "polished children's picture-book illustration, fine watercolor and gouache
washes over delicate precise linework, fine paper-grain stipple texture, one
harmonized scene palette, rich muted color, luminous glowing windows and lanterns,
soft dusk light, dense storybook detail, architecturally faithful buildings with
gently rounded corners"

anti: "no photorealism, no 3D render, no felt or fabric or fiber texture, no
embroidery, no loose sloppy washes, no heavy black outlines, no neon color,
no flat vector look"

## Ref-input plan

- Engine refs (always attach): 2-3 flat-art CROPS from `china-marriott-art-crops.jpg` regions —
  crops, not full product photos (frames would leak substrate).
- For Hospital panels: Hospital crops (same screen = content+palette truth) + one Kitchen or
  Water Cube crop (technique diversity). Hold-out rule applies to generated candidates, not
  to the collection's own approved source art.

## Open question for user
r6 (Cap Juluca-anchored) is looser/paler than this read. Regenerate r7 with this exact
style section + Marriott crops as refs? (probe recommended)

## Correction (2026-07-05, vision review vs Drive ORIGINALS)

r9/r10 finals compared at hi-DPI against the original Police/Fire screens exposed
what the first read underweighted:
- **Palette axis was under-called**: the collection is RICH — deep navy + warm
  cream stone + gold accents, strongly saturated. My outputs drifted to washed
  grey-blue monochrome. The palette line must name the actual colors AND
  "rich saturated".
- **Warm/cool interplay is structural**, not just "luminous": warm cream/gold
  lamps against cool navy — specify both poles or the model goes cold+glow-blobs.
- **Detail density means NO EMPTY SURFACES**: every ref surface carries a feature
  (badge, cornice, notice board, planter, crosswalk). Sparse content prompts
  produce anemic panels even with the right technique words.
- **Judging rule**: always compare against the ORIGINAL reference files at
  hi-DPI crops (not derived/downscaled copies) before shipping.
