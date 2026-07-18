# Round-3 status at session close (2026-07-17)

## Done and verified

- User verdicts recorded: style AWFUL (SDXL+generic-LoRA engine ceiling);
  fold seam divides composition; directive to invest in the geometry
  reference/input given to image-gen models.
- Advisor round 3 complete (independent): sol-round3.md, kimi-round3.md.
  Near-total convergence; reconciled ruling in SYNTHESIS-round3.md:
  - Q1 style: frontier restyle (gpt-image-2 via subgen openai) on a
    geometry-locked Stage-A base, then local re-mask + punch + byte-exact
    socket composite. Sequencing: fix maps FIRST, regen base, then restyle.
  - Q2 seam: fold = zero pixels in all model-facing maps; paintable open
    across fold; composition trace bridged (no horizontal edge within
    +-40px; 3-5 vertical 2px continuations); artwork-language-only prompt.
  - Q3 packet: layered spec (binary masks / width-encoded single edge map /
    flat-color region map + legend); no depth map; manifest-verified.
- Inputs->results evidence board for the user:
  REVIEW/geometry-adherence-solutions/INPUTS.md + inputs/ (on disk, not
  committed per no-PNG convention).

## Builder lane: INCOMPLETE — verified defects (cold check, this session)

scripts/build_geometry_packet.py + packet-640/ exist, but my independent
verification found:

1. packet_manifest.json NOT emitted (Layer-0 spec requirement; sha fns
   exist in script, file absent).
2. control_edge_P1/P2 contain 1876 stroke px inside the st3 vertical
   gutter (x301-339) — spec said zero. (NOTE: builder discovered the
   advisor docs conflate TWO folds: st3 = vertical center gutter; the
   user's seam = HORIZONTAL wavy boundary at y~527. Disambiguation is
   documented in the script docstring; the gutter-stroke policy was left
   unresolved.)
3. Full-width horizontal stroke at y525-528 (runs 626-636px) in BOTH
   control_edge maps — the wavy seam is STILL drawn, i.e. the primary bug
   round 3 exists to fix. Assert 6 (no horizontal run >40px within +-40px
   of seam) fails under independent measurement.
4. Fold-open paintable check ambiguous: paintable shows a smooth V-dip
   y500-560. Cause: svg_classify marks two offset wavy strips at the seam
   (left y494-527, right y527-560) as internal_cutout — if these are REAL
   die-cut slots, paint physically cannot cross and the "continuation"
   design needs rethink; if misclassified fold artwork, they must be
   reclassified. UNRESOLVED — ground-truth the physical product first.
5. Positive: vertical bridging strokes DO cross the seam (31 columns),
   Layer-1 masks strictly binary, closeup overlay looks right otherwise.

## Next session pick-up

1. Resolve defect 4 first (is the wavy seam a cut or a fold? check the
   physical template / ask user) — it decides defects 2-3.
2. Fix build_geometry_packet.py: seam stroke removal, st3 policy, emit
   manifest; re-run asserts independently.
3. Stage-A regen x2 seeds on fixed maps -> seam check.
4. Frontier restyle per SYNTHESIS-round3.md Q1 -> Stage-C -> gate battery
   -> REVIEW for user style verdict.
