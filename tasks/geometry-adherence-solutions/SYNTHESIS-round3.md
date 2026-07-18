# Round-3 synthesis (Sol + Kimi K3, independent, 2026-07-17)

Sources: sol-round3.md, kimi-round3.md. Convergence was near-total; the few
conflicts are ruled below with reasons.

## Q1 style — CONVERGED: lever (c), frontier restyle then local re-mask

Both advisors ranked (c) first: feed the geometry-locked Stage-A art +
the user's style refs to a frontier engine (gpt-image-2 via subgen
--provider openai; nano REJECTED per region-map-guide test record), restyle
at >=1024, then re-impose geometry locally (silhouette re-mask, punch,
byte-exact socket composite) — viable now ONLY because Stage-C exists (the
Re-seat lesson is neutralized).

- Diagnosis (Kimi, confirmed by meta): SDXL-base + generic LoRA 0.75 is an
  ENGINE CEILING; refs bound at one UNet block x0.55 never had a chance;
  prompt had zero high-key/palette anchors; beige init + fp16 adds warm
  drift.
- SEQUENCING (Kimi, adopted): fix the maps FIRST (Q2), regen Stage-A base,
  THEN restyle. Restyling the current seam-baked base preserves the ledge.
- Local fallback/ablation (both): LoRA OFF, IP-Adapter raised (Sol 0.85
  full routing / Kimi 0.65 global — run as a small sweep), palette-anchor
  prompt. Expectation: less-muddy SDXL, not frontier luminosity.
- Checkpoint lottery (b): skip (both). Flux + trained style LoRA (d):
  production endgame at collection volume, not this fix (both; wiki 0.95
  onepass route).

## Q2 fold seam — CONVERGED: "invisible fold, bridged content"

Three verified causes: identical 4px stroke semantics; exemplar trace
itself discontinuous (outset-c1 paints a ledge at that height); paintable
mask BLOCKS rows 525-527 (paint cannot cross).

Ruling (merged):
1. Fold (st3) = ZERO pixels in every model-facing edge map. Not dashed,
   not faint (any canny stroke = "edge here"). Both advisors identical.
2. Fold removed from paintable exclusions — paint flows through. Fold kept
   ONLY in: keepclear_mask.png (new Layer-1 file), region-map quiet band
   (Layer 3), and clearance gates.
3. Bridge the composition trace (Kimi's numbers, adopted): erase trace in
   fold band +-6px; re-register lower trace so NO horizontal exemplar edge
   lands within fold +-40px; synthesize 3-5 vertical 2px continuation
   strokes at tower/wall x-positions spanning fold_top-30 -> fold_bottom+60,
   clipped to paintable eroded 2px. (Sol's version: >=2 continuations per
   side — Kimi's is a superset; adopted.)
4. Prompt: ARTWORK LANGUAGE ONLY (Kimi, backed by repo prompt-boundary
   rule; overrules Sol's verbatim "physical fold" sentence — geometry words
   make models reinvent the template). positive += "one continuous castle
   scene flowing across the whole panel"; negative += "horizontal seam,
   ledge, shelf, split composition, band dividing the picture".
   Frontier legend text uses "quiet background zone" wording, never "fold".
Fallback if seam persists 2/2 after all four: different composition source
for the trace. NEVER dashed/faint strokes.

CAUTION (my verification, both advisors' labels checked): fold element =
st3 (build_composition_map.py FOLD_ROLE=no_focal_motif_zone). Sol wrote
"st2" — st2 is the REAL slot cutouts; do not touch st2 classification.

## Q3 geometry packet — CONVERGED spec, one conflict ruled

SVG = checksummed single source of truth; models consume rasters only.
Packet layers (Kimi's structure + Sol's provenance/preview additions):

- Layer 0 manifest/provenance: transform.json, packet_manifest.json (svg
  sha256 + per-file sha256), door_socket_placement.json, provenance.json.
- Layer 1 deterministic masks (binary 0/255, NEAREST; never model-facing):
  silhouette, paintable_<arm>, holes, keepclear (NEW), socket,
  door_socket_rgba.
- Layer 2 control_edge_<arm>.png — the ONLY canny-CN input. Encoding =
  presence x width (canny cannot read color): contour 4px; holes 4px P1
  only (omit in P2, punch later); socket arch 4px; composition trace 2px
  bridged; fold 0px; keep-clear 0px. Rule: an edge map contains only
  classes the model should render as visible edges.
- Layer 3 guide_semantic.png + legend.txt — flat fills, no strokes/text,
  unique color per meaning, aspect-gated (region-map-guide builder).
  For frontier consumers as image-1 + human QA (Sol's semantic_preview
  merged into this layer).
- Depth map: NO (both — no authoritative depth; invents ledges).
  Segmentation CN: NO; flat-color region map for frontier reasoning: YES.

CONFLICT ruled: Sol proposed dual canny CNs (geometry 0.75 + composition
0.40). Kimi kept single width-encoded map. RULING: single map now (matches
validated pipeline, less machinery); dual-CN is the documented escalation
if composition embossing recurs.

Builder contract: scripts/build_geometry_packet.py --svg X --out DIR
--res WxH --arm P1|P2, emits Layers 0-3 + checks/ overlays. Hard asserts:
fold stroke px in control_edge == 0; masks strictly binary; unique guide
colors; aspect == round8 of SVG body; manifest verified by every consumer.

## Round-3 execution plan

Lane A (builder): build_geometry_packet.py per spec; regen assets; assert
fold invisible + paintable open at fold + bridged trace (checks/ overlays).
Lane B: Stage-A regen x2 seeds on new maps -> seam + geometry gates.
Lane C: frontier restyle (subgen openai) on best new base at >=1024
(pad-not-warp if aspect fights), then Stage-C re-mask/punch/composite +
full gate battery -> REVIEW folder for user verdict.
Claim ceiling: still one panel, exemplar-conditioned.
