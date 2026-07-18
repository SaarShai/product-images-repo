# Sol round-3 verdict (extracted from raw)

## Q1 — Style

**Ranking: c > a > b > d.**

1. **Frontier whole-panel redraw/restyle: recommended.**

   Use **gpt-image-2 first**, with the geometry-locked candidate explicitly labeled as a composition map, plus both original style references and selected high-signal crops. Generate **4 candidates**, then reapply the authoritative silhouette/cutout masks, punch any required holes, and composite the byte-exact door back.

   This is the closest route to the luminous reference with the least new machinery because the creative route already worked; its prior failure—erasing controls—is now mechanically repairable. Do not ask it to lightly filter the muddy SDXL pixels. Ask for a **fresh coherent redraw** preserving layout and negative spaces.

   Style wording should replace “soft pastel” with:

   > luminous children’s-book watercolor; bright ivory paper showing through transparent washes; warm cream and pale gold stone; clear coral and salmon roofs; cool blue-grey shadows; delicate warm-grey linework; clean highlights; airy color separation; polished but hand-painted

   Negative:

   > no beige cast, sepia haze, grey veil, dusty pigment, muddy glazing, grunge, felt texture, opaque chalkiness, generic fantasy concept art

2. **Local IP-Adapter ablation: cheapest fallback.**

   Run one decisive local arm:

   - generic watercolor LoRA: **off, 0.0**
   - IP-Adapter-plus: **full routing, scalar 0.85**
   - style inputs: one full reference plus **3–4 style-packet crops** emphasizing luminous stone, coral roofs, fine edges, and bright paper
   - retain ControlNet/masks independently

   If content leakage becomes serious, reduce IP to **0.70**. Do not simultaneously restore the LoRA; that makes attribution unclear. The present `0.55` on one up-block while a `0.75` generic LoRA is fused strongly favors the generic learned look.

3. **Different SDXL checkpoint: exploratory, not the main answer.**

   If one checkpoint must be tested, use **`Lykon/dreamshaper-xl-v2-turbo` without the generic watercolor LoRA**, not Juggernaut. DreamShaper is an artistic SDXL fine-tune, whereas Juggernaut explicitly targets photorealism. However, DreamShaper is published as a text-to-image SDXL pipeline with a turbo schedule, so it is not a drop-in replacement for the present 9-channel inpainting setup. That integration cost moves it below the IP ablation. [DreamShaper XL model card](https://huggingface.co/Lykon/dreamshaper-xl-v2-turbo), [Juggernaut XL model card](https://huggingface.co/RunDiffusion/Juggernaut-XL-v9)

4. **Flux/IP-Adapter/LoRA rebuild: defer.**

   It requires a new conditioning and masking stack, and there is no evidence that an available Flux style LoRA matches these particular references. Consider it only if both frontier redraw and the clean IP-only SDXL arm fail.

## Q2 — Fold seam

**Commitment: remove the fold completely from every visual edge/control map and reclassify it as a paint-through, no-focal-motif zone.**

The SVG’s wavy `st2` paths are currently treated like true cutouts. Therefore the builder must do more than erase their 4 px stroke:

1. Reclassify `st2` from `internal_cutout` to `fold_line`.
2. Remove it from:

   - `holes_mask.png`
   - P1/P2 paint exclusions
   - hard white composite-back
   - geometry Canny
   - composition Canny

3. Create `fold_quiet_mask.png` as a filled band extending **12 px on each side** of the fold curve at 640×1544. This mask is advisory/semantic:

   - background wash, walls, and structural color **must paint through it**
   - no roof peak, tower base, window, door, tree crown, character, or other focal motif may originate or terminate inside it

4. Rebuild the composition scaffold so at least **two major vertical wall/tower continuations per side** cross the fold uninterrupted. Delete structural edges that terminate at the fold and bridge the corresponding wall edges across it.

5. Use this prompt sentence verbatim:

   > The wavy horizontal path marks a physical fold in the finished product, not an edge in the illustration. Do not draw, outline, shadow, lighten, separate, restart, or change buildings at the fold. Walls, towers, watercolor washes, and lighting continue seamlessly across it; only focal details avoid the quiet fold band.

Do not use a dashed or faint fold stroke. Any edge supplied to Canny can be interpreted as a ledge, roofline, wall base, or scene boundary.

## Q3 — Canonical geometry packet

The **SVG remains the checksummed source of truth**. Models receive provider-specific raster derivatives generated from it.

### Packet structure

```text
geometry-packet/
  source.svg
  manifest.json
  native-640x1544/
    silhouette_mask.png
    paintable_mask.png
    true_cutout_mask.png
    socket_mask.png
    fold_quiet_mask.png
    keepclear_mask.png
    control_geometry_edges.png
    control_composition_edges.png
    region_map.png
    semantic_preview.png
  frontier-1024x1536/
    region_map.png
    composition_guide.png
    semantic_preview.png
    transform.json
  legend.txt
  prompt-template.txt
  provenance.json
```

All binary masks are 8-bit, exactly `0/255`, resized with **NEAREST**. `provenance.json` records the SVG SHA-256, raster dimensions, role assignments, stroke widths, and generator version.

For the 1024×1536 frontier version, fit the exact-aspect panel into:

- panel bbox: approximately **x=207..817, y=32..1504**
- no stretching
- `transform.json` records the exact scale and offsets for registration back to 640×1544

### Stroke and channel semantics

| Semantic class | Encoding | Consumer |
|---|---|---|
| Outer physical cut edge | Solid white, **4 px**, black background | Geometry Canny |
| True cutouts/voids | Solid white, **3 px** | Geometry Canny + hard masks |
| Fixed door/socket boundary | Solid white, **3 px** | Geometry Canny; socket mask remains authoritative |
| Fold | **No stroke anywhere**; filled cyan only in semantic/quiet maps | Prompt and motif-placement logic |
| Keep-clear/no-focal zone | Filled yellow, no outline | Region map and placement logic |
| Composition hint | White **2 px** structural edges on its own black map | Composition Canny |
| Human QA roles | Distinct colors plus legend | `semantic_preview.png` only |

Do not combine production edges and composition traces into one same-weight map again.

### SDXL conditioning

Use two independent Canny controls:

- geometry edges: scale **0.75**, guidance **0.00–0.80**
- composition edges: scale **0.40**, guidance **0.00–0.55**

The hard paintable mask remains the geometry guarantee. The geometry Canny teaches intentional framing; the weaker composition Canny teaches content without embossing every exemplar edge.

If only one ControlNet can be supported, feed the **composition map** and rely on masks/composite-back for geometry. Do not merge the fold or keep-clear semantics into that Canny image.

### Frontier region map

Use flat fills only—no outlines or text. One color has one meaning:

- black: outside product
- grey: continuous paintable background
- green: primary castle masses
- blue: secondary towers
- orange: foliage/decorative atmosphere
- red: true blank cutout
- magenta: frozen door/socket area
- cyan: paint-through fold quiet zone
- yellow: other no-focal/keep-clear zone

The colors are labels, not requested output colors. Feed:

1. region map as image 1
2. composition guide as image 2
3. full style reference 01
4. full style reference 02
5. optionally one luminous-stone/roof style sheet

### Depth and segmentation

- **Add the semantic region-color map:** yes, for frontier models.
- **Add depth:** no. There is no authoritative scene depth in the SVG, and invented depth would encourage the fold to become a ledge.
- **Use arbitrary-color segmentation ControlNet:** no. Generic segmentation ControlNets expect their trained label conventions; the custom palette is for frontier visual reasoning unless a matching custom control model is trained.

### Canonical instruction/legend

```text
IMAGE ROLES
Image 1 is an exact-aspect semantic geometry and placement map. Its colors are
labels only. Do not reproduce its colors, outlines, or diagram appearance.
Image 2 is a composition guide only, not a pixel or style source.
Images 3–5 are the only style sources.

GEOMETRY
Keep the outer silhouette and true negative spaces indicated by image 1.
Red and magenta regions are reserved void/socket areas.
The cyan fold zone remains fully painted with continuous walls, washes, and
lighting, but contains no focal motifs. The fold must not appear in the artwork.
Yellow zones receive quiet background only.

COMPOSITION
Redraw one coherent castle scene. Major wall and tower structures continue
vertically across the cyan fold zone. No building begins, ends, changes facade,
or gains a ledge at that location.

STYLE
Match images 3–5: luminous children’s-book watercolor, bright ivory paper,
transparent warm cream and pale-gold stone, coral roofs, cool blue-grey shadows,
delicate warm-grey linework, clean highlights, airy color separation.

AVOID
No visible template lines, color-map colors, fold seam, horizontal division,
new upper building, beige/grey veil, dusty or muddy wash, grunge, felt texture,
collage seams, text, labels, or signage.
```

The key architectural decision is: **masks enforce production geometry; separate controls describe cut edges and composition; the fold exists only as semantic metadata.**


