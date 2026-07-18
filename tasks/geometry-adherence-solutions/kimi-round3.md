# kimi-round3.md — Round-3 consult answer (style, fold seam, geometry packet)

Independent advisor answer. Evidence read: `experiment-1/CONCLUSIONS.md`,
`experiment-1/PARAMS.md`, `runs/RESULTS-*.md`, `runs/B-s21-d050/meta.json` +
`final.png`, `assets-640/control_canny.png`, `assets-640/control_composition.png`,
`scripts/build_assets.py`, `scripts/build_composition_map.py`,
`scripts/gen_stage_a.py`, both frozen style refs, the frozen frontier exemplar
`tasks/geometry-evidentiary-princess-n02/experiments-outset/outset-c1/raw.png`,
repo skill `region-map-guide`, repo doc `docs/image-generation.md`, wiki fact
`concepts/onepass-geometry-style-route-flux-control-lora`. (Deliberately did
NOT read the co-advisor's round-3 raw/verdict files.)

---

## Q1 — Style-fix lever ranking

### Diagnosis (why "awful", in contribution order)

1. **Engine ceiling.** The target style is frontier-engine output — the
   exemplar outset-c1 and both princess refs are high-key, luminous,
   thin-ink watercolor that SDXL-base + a generic fused watercolor LoRA
   (0.75) does not render. The LoRA's palette prior is exactly the
   ochre/dusty brown the user rejected. No amount of conditioning tuning
   moves SDXL-base across this gap; Stage-B 0.35/0.50 already proved the
   local restyle delta is ±14–17 mean RGB — refinement, not a style jump.
2. **IP-Adapter barely binds — by design.** Style-layer-only routing
   (`up.block_0=[0,0.55,0]`) was chosen to mechanically block layout copy.
   It transfers one UNet block's worth of texture statistics; the refs
   never stood a chance of setting palette/light.
3. **Prompt has zero palette/light anchors.** "Soft pastel washes" *admits*
   muddy. Nothing says high-key / white paper / pale cream / light blue
   sky — the defining properties of the refs.
4. **Warm bias from the machinery.** Beige neutral fill (222,213,199) +
   fp16 pipe: measured 65–70/255 warm-dark VAE drift on kept regions
   (PARAMS Amendment 3 table).

### Ranking (committed)

**1. Lever (c) — frontier Stage-B restyle, then local re-mask + punch +
composite-back. RECOMMENDED. Do this now.**

- It is the only lever whose style ceiling *is* the target style: the refs
  came from this engine class.
- The Re-seat route's failure ("style but erased controls") is now
  mechanically covered — that route accepted/restyled with no repair path;
  we now re-impose silhouette (hard white composite), holes (punch), and
  the door socket (byte-exact alpha-over, provenance-gated) **after** the
  restyle. The styler only needs *approximate interior composition
  preservation*, which frontier img2img edits demonstrably preserve
  (`docs/image-generation.md`: "strong composition preservation on edits").
- Zero new machinery: `scripts/subgen.py --provider openai` + existing
  `composite_back.py` Stage C. This is also exactly the repo doctrine for
  "geometry approved, style failed": feed the geometry-locked rough + style
  refs into image generation as composition inputs, whole-panel restyle,
  exact SVG exporter/checker as the downstream gate (AGENTS.md).
- **Provider: openai (gpt-image-2 via subgen/Codex). NOT nano-banana** —
  region-map-guide recorded a tested rejection of nano (ignored zones,
  painted keep-clear, didn't lock aspect, didn't match reference style).
- **Sequencing matters:** fix the maps first (Q2), regenerate the Stage-A
  base (2 seeds), *then* restyle. Restyling the current B-s21-d050 base
  would bake the seam-reading composition into the style pass — img2img
  preserves the composition you give it, ledge and all.
- New pipeline: Stage A (fixed maps) → **Stage B = frontier restyle**
  (replaces local SDXL Stage B) → Stage C unchanged (re-mask → punch →
  socket composite-back → gates). Restyle at ≥1024x1536 doubles as the
  designed upscale-before-paste pass (CONCLUSIONS open item); paste the
  door at final res, last.
- Drift guard: after resize/registration back to canvas, verify interior
  composition drift vs the base (canny-edge correlation / motif-centroid
  offset inside paintable, advisory), then the existing hard gates run.
  If the provider recomposes tall-thin input (subgen already warns on
  this), pad the base to the provider portrait aspect with white margins,
  restyle, center-crop back — never warp.

**2. Lever (a) — IP full routing / higher scale, LoRA dropped. Same-week
local fallback only.**

Concrete sweep (no new machinery, skip `load_lora_weights`/`fuse_lora`):
LoRA off; IP-plus global scale 0.65 (fallback: up-blocks-only 0.8);
positive += "high-key luminous watercolor, pale cream stone, light airy
blue sky, white paper showing through, delicate thin ink lines, soft
sunlit glow"; negative += "muddy, ochre, dusty, brown wash, dull".
Expectation-setting: this yields *less muddy SDXL*, not *luminous
frontier* — and full routing re-opens layout copy from the refs (they are
also castles), so watch for CN-vs-IP composition fights. Run it only if
(c) is blocked; run it anyway as the ablation row (one evening, $0).

**3. Lever (b) — checkpoint swap. Do not checkpoint-lottery.**

Any specific "better watercolor SDXL" pick is an unverified new asset that
invalidates the frozen card's tuning (guidance 5.5 was checkpoint-specific)
and stays inside the SDXL rendering ceiling. If local style must be
*owned*, the honest version of (b) is (d): train on the approved refs
rather than lottery a generic fine-tune. Ranked above (d) only on
machinery cost, below it on expected payoff.

**4. Lever (d) — Flux + trained style LoRA. The production endgame, not
this fix.**

Repo-proven (wiki, confidence 0.95): `fal-ai/flux-control-lora-canny` +
per-collection trained LoRA at `control_lora_scale 0.35` → silhouette-IoU
0.975–0.988 *first-shot*, one pass, on Cap Juluca + Marriott;
`scripts/onepass_gen.py` + the lora.json registry already exist. It is the
right move when panel volume justifies training data (10–20 approved
images per collection); it is the most new machinery for fixing one
panel's style this week.

**Answer to "closest with least new machinery": (c), by a wide margin on
both axes.** Order: c → a (fallback/ablation) → d (production strategy) →
b (fold into d).

---

## Q2 — Fold-seam control-map redesign (committed design: **"invisible
fold, bridged content"**)

Root cause is two-part, both verified: (i) the fold band (st3) is drawn as
the same 4px white stroke as the die contour/arch/cutouts in BOTH
`control_canny.png` and `control_composition.png` — a canny ControlNet
reads any stroke as "hard edge here", and the model dutifully painted a
decorated ledge/braid; (ii) the frozen exemplar `outset-c1/raw.png` is
**itself discontinuous at the fold** — it draws a stone ledge with cast
shadow at that height, wall+trees terminating above, towers restarting
below. The round-2 trace imported the exemplar's seam.

One design, four inseparable parts:

1. **OMIT the fold stroke from every model-facing edge map, all arms.**
   Zero pixels — not dashed, not 1px, not faint. A canny CN has no
   "weak-edge" semantic other than width, and ANY stroke at the fold says
   "draw something here". The fold is a physical artifact of the product,
   not a drawing element; the art must be painted as if the panel were one
   continuous sheet.
2. **KEEP the fold only in non-visual channels.** st3 stays in the
   geometry layer as the paintable, clearance-gated no-focal-motif zone
   (masks/manifest, and the Layer-3 region map of Q3 with quiet-band
   legend language). Deterministic and textual — never neural-visual.
3. **BRIDGE the composition trace across the fold** so content, not
   vacuum, occupies the seam (stroke removal alone leaves an empty
   horizontal corridor that still reads as a division). In
   `build_composition_map.py`:
   - erase trace pixels inside `fold_band ⊕ 6px`;
   - re-register so **no horizontal exemplar edge lands within fold ±40px**
     (shift the lower-subpanel trace vertically until the wall base/ledge
     clears the band — the exemplar's ledge line must not straddle the
     fold);
   - synthesize 3–5 vertical continuation strokes (2px, interior class) at
     the x-positions of the towers/wall edges nearest the fold, spanning
     `fold_top−30px → fold_bottom+60px`, clipped to `paintable_P1 ⊖ 2px`.
   The CN then sees uninterrupted verticals crossing the seam: one
   continuous castle; the fold band carries only boring wall/roof edges —
   which *is* the required no-focal-motif zone.
4. **Prompt (artwork language only):** positive += "one continuous castle
   scene flowing across the whole panel"; negative += "horizontal seam,
   ledge, shelf, split composition, band dividing the picture". Never the
   words "fold"/"panel"/geometry terms (repo prompt-boundary rule:
   geometry words make the model reinvent the template).

Load-bearing fallback ONLY: if a seam still reads on 2/2 test gens after
1–4, the residual cause is the exemplar's own ledge composition → re-trace
from a different composition source (or hand-place the trace). Do **not**
fall back to dashed/faint strokes — that re-introduces the bug at lower
amplitude. Why the alternatives lose: dashed/faint still encodes an edge;
paintable-channel-only retention leaves the trace vacuum; prompt-only is
the card's own weakest conditioner; re-registration alone leaves the 4px
stroke.

---

## Q3 — Canonical geometry-packet spec (builder-ready)

### Principles

- **SVG stays the single source of truth** — the only *authored* artifact,
  input to gates and the builder. Models never receive the SVG: they
  consume pixels, and feeding SVG text or an SVG screenshot collapses all
  semantics back into one undifferentiated stroke style — that collapse is
  the current bug. So: **raster encodings, derived, layered by consumer.**
- One builder emits the entire packet + manifest + overlay checks; every
  consumer script verifies the manifest sha256 at load (refuse stale
  assets).
- Geometry gates (re-mask, punch, socket composite-back) re-run after ANY
  model pass, so no model-facing map needs to be geometry-safe — it needs
  to be *semantically honest*.

### Packet contents (at working res W×H, aspect-exact round8 of SVG body)

**Layer 0 — manifest/provenance** (machines only): `transform.json`,
`packet_manifest.json` (svg sha256, scale, per-file sha256),
`door_socket_placement.json`, `provenance.json` (Amendment-5 mechanism,
unchanged).

**Layer 1 — deterministic masks** (never shown to a model; consumed by
inpaint/gates/compositor; strictly binary 0/255, NEAREST):
`silhouette_mask.png`, `paintable_<arm>.png`, `holes_mask.png`,
**`keepclear_mask.png` (NEW — fold band + bottom keep-clear as their own
file; today they exist only implicitly)**, `socket_mask.png`,
`door_socket_rgba.png`.

**Layer 2 — `control_edge_<arm>.png`** (white-on-black; the ONLY map the
SDXL canny CN gets). Encoding = **presence × width**, not color — a canny
CN cannot read color semantics; omission is the semantic:

| class | encoding | rationale |
|---|---|---|
| die-cut outer contour | 4px | intentional ink rim at the cut edge |
| internal cutouts (holes) | 4px, **P1 arm only** | framed openings in P1; OMIT in P2 so art paints continuously, then punch |
| socket arch edge | 4px | Amendment-1 intentional frame around the fixed door |
| composition trace | 2px | suggestive scaffold, bridged across fold per Q2 |
| fold band | **omitted (0px)** | Q2: physical artifact, never an edge |
| keep-clear zones | **omitted (0px)** | quiet zones are regions, not edges |

Rule: an edge map may contain only classes the model should render as
visible ink/paint edges. Everything else lives in Layer 1 or Layer 3.

**Layer 3 — `guide_semantic.png` + `legend.txt`** (flat fills, palette
names; repo-proven region-map pattern, built with the region-map-guide
builder and its gates: `--expect-aspect` exit-2, unique color per meaning,
**no strokes/outlines/text drawn in-map** — bold lines get traced into the
art). For frontier models as image-1 and for human review:

| fill | legend meaning |
|---|---|
| flat color per motif cluster (sky/trees, gate wall, tower cluster, foreground foliage) | region, not edge, encoding of composition |
| pale yellow band at fold | "quiet background zone — continuous scenery only, no edges, no focal objects; paint straight through it" |
| pale blue at keep-clear | "quiet zone, background only" |
| magenta at holes | "physical openings in the product — paint as background sky, no object detail" |
| actual door raster pasted in place | "fixed wooden door — keep it exactly" |
| white outside silhouette | "outside the product — leave blank" |

Colors are arbitrary labels; the legend words carry the content; the fill
edge IS the boundary (never draw the contour as a stroke).

**Depth map: NO** for this product class — the art is flat children's-book
watercolor; a depth CN fights the 2D wash aesthetic and competes with the
edge CN (dual-CN was already the documented, non-taken escalation).
**Segmentation: YES**, but only as Layer 3's flat-color region map — the
proven pattern (Wanderland: registration distortion 26%→5%; provider
discipline: openai only, nano tested and rejected 2026-07-12).

### Consumer matrix

| consumer | inputs |
|---|---|
| SDXL Stage A | `paintable_<arm>` (inpaint mask) + `control_edge_<arm>` (canny CN) + style refs (IP) + prompt T3 |
| SDXL Stage B (if kept) | same, image = Stage-A out |
| **frontier restyle (Q1-c, primary)** | image-1 = **Stage-A geometry-locked art** (art, not the guide map — it is the composition input), image-2 = style ref(s), prompt T1; then Layer-1 gates |
| frontier one-shot/recompose (other panels, fallback) | image-1 = `guide_semantic.png` (locks aspect + zones), image-2 = style ref(s), prompt T2 |
| Stage C (no model) | Layer-1 masks + `door_socket_rgba` + Layer-0 provenance |

### Instruction templates

**T1 — frontier restyle (no geometry words):**
"Restyle this picture into luminous children's-book watercolor: pale cream
stone, light airy blue sky, white paper showing through, delicate thin ink
outlines, soft translucent washes, gentle sunlight. Keep every object
exactly where it is — same shapes, same positions, same sizes. Do not
move, add, or remove any architectural element. Keep the wooden door
exactly as it is. Change only the painting style, colors, and light."

**T2 — frontier one-shot with region map (legend):**
"Image 1 is a color-region placement map, not art. Each color names what
occupies that region: <color→meaning lines from legend.txt>. Do not paint
the map's colors or outlines. Yellow band = quiet background zone:
continuous scenery only, no edges, no focal objects — paint straight
through it. Magenta shapes = openings in the product: paint them as
background sky. Green/pasted door = fixed element, keep it exactly. Style:
match image 2 exactly — luminous high-key watercolor, pale cream stone,
light blue sky, white paper showing through, delicate thin ink lines."

**T3 — SDXL local (card prompt + palette anchors):** existing card prompt
with Q1 lever-(a) additions; negatives += "muddy, ochre, dusty, brown
wash, horizontal seam, ledge, band dividing the picture".

### Builder contract

`scripts/build_geometry_packet.py --svg X --out DIR --res WxH --arm
P1|P2` emits Layers 0–3 + `checks/` overlays, with hard asserts: fold-band
stroke pixels in `control_edge` == 0; all Layer-1 masks strictly binary
(NEAREST); guide-map colors unique (exit 2); canvas aspect == round8 of
SVG body; manifest written last, verified first by every consumer.
Production ordering unchanged: restyle/upscale BEFORE socket paste; all
gates LAST.

---

## One-line summary

Q1: frontier restyle-then-remask (c) now — the Re-seat lesson is
neutralized by byte-exact composite-back; (a) as cheap local
fallback/ablation; (d) trained-LoRA Flux one-pass as the production
endgame; skip (b). Q2: fold = zero pixels in every visual map, retained
only as a deterministic/legend quiet zone, with the composition trace
bridged across it (no horizontal edge within ±40px, 3–5 vertical
continuations through the band). Q3: SVG = source of truth; packet =
Layer-1 binary masks + Layer-2 presence×width edge map (fold/keep-clear
omitted) + Layer-3 flat-color region map with legend for frontier
consumers; no depth map; one builder, manifest-verified, gates always
last.
