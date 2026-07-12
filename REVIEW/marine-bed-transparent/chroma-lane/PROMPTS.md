# Chroma-lane prompt matrix — gpt-image-2 uniform background experiment

Model: `gpt-image-2` via `images/edits`-equivalent (Responses API `image_generation`
tool, background=transparent rejected by this model — confirmed 400
`"Transparent background is not supported for this model."`). Quality=high on
this endpoint exceeds the ~60-75s sync cap for `images/edits` (confirmed:
`RemoteDisconnected` after ~75s on a live call), so all gens run through the
async Responses `background: true` job + poll pattern (`chroma_gen.py`).

Reference image (image input, fed as `input_image` data URL):
`.../double Marine Bed Wrapper/images/ChatGPT Image Jul 7, 2026, 11_20_05 AM.png`
— pastel watercolor coral tower; palette sampled at low-saturation warm
pinks/peach/tan (see chroma_gen.py sampling note); brief also flags
pinks/purples/greens/yellow/blue elsewhere in the piece, so bg colors avoid
all of those hue families.

## Colors (3)
- `#00FF00` — pure green (brief default; probes hue distance from any pastel
  greens in the art)
- `#FF00FF` — pure magenta (brief default; prior session finding: caused rim
  halos on pink art — retained here specifically to re-test with a stricter
  hygiene prompt, P3)
- `#00A0FF` — strong azure (brief default; furthest hue from the observed
  warm pink/peach/tan palette of any of the three, best separation candidate)

## Prompt styles (3)

### P1 — minimal
```
<motif clause omitted — this is an edit of an existing illustration, not a
motif>, on a completely solid, flat, uniform background of exactly the color
{HEX}. Every single background pixel must be the identical RGB value. No
gradient, no vignette, no texture, no shadow, no glow.
```

### P2 — chroma-studio
P1 + ` Professional chroma-key studio backdrop, as used for green-screen
compositing; the artwork floats on the flat key color; no reflection or
color spill onto the artwork.`

### P3 — chroma-studio + banked edge-hygiene block (verbatim from
`skills/transparent-product-image-gen/SKILL.md`) + extra glow/crop guards
P2 + verbatim edge-hygiene block:
```
every object has clearly defined, fully closed outlines; no shape fades into
the background; edges crisp; interior highlights enclosed by visible outlines
```
+ `No glow, aura, halo, soft wash, or gradient bloom around the artwork;
background color runs right up to the crisp painted edge of every element.`
+ `The entire illustration fits fully inside the frame with clear margins on
all sides; nothing cropped at any edge.`

## Full prompt template used (edit-mode, keep artwork identical)

```
Keep this illustration's artwork completely unchanged — same subject,
composition, colors, and detail — and repaint ONLY the background to be
completely solid, flat, uniform color {HEX}. Every single background pixel
must be the identical RGB value {HEX}. No gradient, no vignette, no texture,
no shadow, no glow. [P2 clause if style>=P2] [P3 clauses if style==P3]
```

9 gens = 3 colors x 3 styles. Output naming:
`raw_{color}_{style}.png` in `chroma-lane/raws/`.
