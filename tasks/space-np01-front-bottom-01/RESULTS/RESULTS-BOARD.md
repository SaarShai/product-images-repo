# RESULTS BOARD — space-np01-front-bottom-01

**Task:** watercolor space control-panel illustration fitting SVG geometry
(viewBox 763.65x2602.29, ~1:3.585). 2 openings: 1 long tapered vertical slot + 1 round port.
**METHOD (user-confirmed):** OUTSET-the-SVG + keep the RAW.
1. `scripts/outset_cutouts.py template.svg --out template-outset30.svg --outset 30` (buffer
   cutouts outward +30 units so the empty area absorbs cut drift; outer contour verbatim).
2. `scripts/build_trueaspect_base.py` from the outset SVG → enlarged-hole contract base.
3. nano sources via `geom_adherence_test.py` (refs as attachments).
4. PICK the best RAW by eye. No re-seat, no exact.png — the raw is the deliverable.

## PRIMARY DELIVERABLE — OUTSET-A-o30-s1 / raw.png  ✅ KEPT
`np01-front-bottom-01-FINAL-outset30-s1.png` — outset-30 nano raw. User-confirmed keeper.
Clean empty slot + port with generous outset margin, bright cobalt + colorful tick-marked
controls. This is the art + the method to reuse.

## Superseded (obsolete) — re-seat route
The earlier `exact_bevel_composite.py` re-seat outputs (`*-FINAL-nb-s2*.png`) are SUPERSEDED.
The re-seat degraded the raw (user: "you ruined it"). Kept only as historical reference;
not a deliverable. The re-seat route is no longer used for this panel family.

## All 8 re-seated sources (region-IoU, rim 1.2 unless noted)
| src | region-IoU | per-opening |
|---|---|---|
| s2 (rim 1.0) | **0.899** | 0.853 / 0.915 |
| s2 (rim 1.2) | 0.895 | 0.865 / 0.924 |
| s3 | 0.886 | 0.853 / 0.92 |
| s4 | 0.884 | 0.848 / 0.919 |
| s7 | 0.884 | 0.853 / 0.914 |
| s1 | 0.880 | 0.848 / 0.912 |
| s5 | 0.879 | 0.843 / 0.915 |
| s6 | 0.879 | 0.846 / 0.911 |
| s8 | 0.873 | 0.838 / 0.908 |
