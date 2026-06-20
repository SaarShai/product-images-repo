# Whole-panel build — anchor set (for B0 judge calibration)

User-provided canonical examples. Each is split from a combined "template + illustration"
SVG (Drive) into a geometry-only `source/template.svg` + the extracted `illustration*.png`
(combined SVGs are 3–110MB — too heavy for git, split per user OK). One example at a time.

**Judge adherence on `overlay.png`, NOT the bare illustration.** Each anchor has an `overlay.png`
= artwork pasted at its exact SVG `<image>` transform with the coloured guide lines drawn on top
(true SVG coordinates). Built by `scripts/make_anchor_overlay.py <combined.svg> --out overlay.png`.
Because the artwork is embedded in the SVG, registration is EXACT (from the transform) — no
auto-bbox guessing. This is the registration the B0 judge reuses.

## Screenery template colour legend (from `princess-narrow-01` Illustrator `.st` classes)
| colour | hex | role | adherence rule |
|---|---|---|---|
| magenta/pink | `#ed1f79` | die-CUT line (outer contour + cutout outlines) | the physical cut; design art *to* it, not clipped after |
| yellow | `#fff200` | SAFE margin | keep ALL art inside; no bleed past it |
| red | `#ed1c24` | KEEP-CLEAR / no-focal-motif zone | no recognizable motif here (e.g. central door-fold band) |
| blue | `#1c75bc` | sub-panel / fold-score separators | no split-sensitive detail across it |
| green | `#39b54a` | top-contour guide (arch silhouette) | crown of the art follows it |
| black | `#231f20` | plain cut line (used when a template has NO colour guides) | contour + slots + holes; keep cutout areas clear background |

> Caveat: docs/ cite a slightly different yellow (`#ffdb55`) for older templates — colour codes
> may vary by template version. Confirm per-file from its `.st` classes, don't assume globally.

## Anchors

### `princess-narrow-01` — GOOD / PASS anchor (character panel)
- `source/template.svg` (viewBox 1838.94×4037.99, tall ~1:2.2) — full colour-guide set above.
- `illustration.png` 3558×7673 — watercolour fairytale castle, turrets, ivy, flowers, small
  princess figures. Adheres: art inside yellow margin, clear of central red band, crown on green
  top-contour, nothing crossing cut/fold lines.
- Source (Drive): `…/Screenery/production files/princess/princess narrow panel template and illustration.svg`
- ⚠ R30: template has out-of-viewBox coords (nested-group transforms; st0/guides at x≈10000) — confirm roles in B0 before using as geometry source.

### `space-stabilizer-01` — GOOD / PASS anchor (control panel)
- `source/template.svg` (viewBox 3116.34×1030.08, wide ~3:1) — BLACK paths only (`#231f20`):
  outer contour, long slot, short slot, **12 circle holes**.
- `illustration-1.png` 6434×2146 (the real one) — pale watercolour stabilizer with control
  clusters (buttons/knobs/sliders/lights) painted ONLY on solid areas; circle holes + long slot
  left as clear background so nothing is cut. `illustration-0.png` (4291×12874, off-aspect) = stray layer, ID later.
- Source (Drive): `…/Screenery/production files/space/space stabilizer example.svg`

### `space-narrow-panels-01` — GOOD / PASS anchor (around-cutout + bevel/outset)
- `source/template.svg` (viewBox 3479.52×4285.44, two panels × top/bottom subpanels) — BLACK only:
  outer contours, stabilizer slot, notches, **5 circle holes** + small cutout polygons.
- 12 embedded PNGs: the tall ~1:2.9 ones (`illustration-6/7/8/11`, 13–14MB) + square ones
  (`9`,`10`) are the real per-panel arts; the small 0.2MB off-aspect ones are layer strays.
  `illustration-6` = cobalt control panel where the circle hole + vertical slot sit in **empty,
  beveled-rim recesses** — controls designed AROUND the cutouts with an **outset margin** and the
  panel contour **leaning into** each cutout (rim/bevel). This is the exact "exact-aperture +
  painted-rim" target (the open problem).
- Source (Drive): `…/Screenery/production files/space/space narrow panels example.svg`

### `skyline/` — 9 teaching examples + template (copied from `assets/skyline/`; backup snapshot byte-identical)
All VIEWED. Per its README these are **rule evidence, not style authority**. Each encodes one rule the
B0 judge rubric should check:
- **DO** / **DON'T** — recognizable features (fairies/birds) NOT cropped vs cropped at seams/red zones (clean PASS/FAIL pair).
- **bridge inside door flaps** (London Tower Bridge) — a run-through element spanning the central saloon-arch is OK.
- **bridge through panels + top-contour traces buildings** (NYC) — run-through + top-contour adapts to skyline silhouettes.
- **landmark (statue) fits door flaps** (Columbus column) — a vertical landmark fitting the orange arch.
- **2-building composite** (St Paul's+Westminster) / **2-landmark composite** (Big Ben+London Eye) — composing within one panel.
- **exaggerated door** (cathedral) — modify building proportions so an entrance complements the arch guide.
- **princess palace** — doorway/double-door fitting the door-flaps + saloon-arch.
- `city-skyline template.svg/.ai` — the 3-panel template (centre door panel + 2 sides; blue dashed = top/bottom sub-panel separators here).
Note: these are standalone teaching rasters (no per-example combined SVG) → used as rubric rules, not exact-registration anchors. The DON'T is the cropped-element FAIL anchor.

### `princess-panels-FAIL-01` — FAIL anchor (annotated; contrastive twin of princess PASS)
- Same castle+door subject as a passing princess panel but USER-REJECTED — forces the judge to
  separate "pretty" from "correct."
- `source/template.svg` (viewBox 3225.58×4635.01) — full colour set **including orange `#f7941d`**
  (saloon-door arch) and yellow **`#ffdb55`** (note: this template's safe-margin yellow differs from
  princess-narrow-01's `#fff200` — confirm colours per file). Geometry: two `door_flap` cutouts,
  arched `top_contour`, finger/wing cutouts (`st8`), red keep-clear band (`st7`).
- `illustration-0.png` 1096×1456 (low-res draft).
- **GOOD criterion (point 1):** the wooden door fits perfectly/near-perfectly to the **orange arch
  zone** + the **door-flap cut outlines**.
- **Labeled FAIL modes (user, ground truth):**
  1. illustration **doesn't reach the bottom** (white gap at base — under-fill).
  2. the **wing cutouts don't align** with the finger holes (painted wings ≠ actual cutout positions).
  3. the **top of the contour** needs adjusting to the shape of the illustration top (spires vs top_contour).
  4. **fairies cropped** at the forbidden **red zone** (recognizable motif in keep-clear band).
- Source (Drive): `…/Screenery/production files/princess/princess panels template FAIL.svg`

### `window-fit-01` — GOOD / PASS anchor (precise CURVED-cutout fit)
- `source/template.svg` (viewBox 1587.63×2321.06, arched panel) — BLACK only (`#1d1d1b`): outer
  contour + **arched-window cutout** (cls-1 @ 468,1059–1148,1721) + small finger-hole cutout(s) + a tall slot.
- `illustration-0.png` 3263×4749 — cosy cat-on-bookshelf with mice; the glowing **arched window fits
  the arched cutout almost exactly** and the **finger-hole knob** aligns with its cutout (verified on overlay).
- First anchor with a **curved** cutout (vs rect/circle) — tests precise fit to a non-trivial shape.
- Source: `/Users/za/Downloads/example - window fit.svg`

## B0 readiness
- PASS end (exact-registration Screenery panels): princess-narrow-01, space-stabilizer-01,
  space-narrow-panels-01, **window-fit-01** (+ skyline DO as rubric rule).
- FAIL end: princess-panels-FAIL-01 (4 annotated modes: under-fill, cutout-misalign, top-contour,
  red-zone crop) + skyline DON'T (seam crop).
- Both ends covered → the B0 judge can be calibrated to reproduce these verdicts.
