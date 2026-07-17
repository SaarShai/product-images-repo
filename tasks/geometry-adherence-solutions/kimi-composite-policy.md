# Kimi answer — socket composite-back policy

**Decision: C — arch-shaped keep-clear + keyed-arch composite, rebuilt BEFORE Stage-A gens.**

**Q1.** A pastes a white card onto painted wall: given the banked anti-collage
aesthetic that is a near-certain cohesion-gate flag. B *without* a mask rebuild
is the same failure in beige: the frozen rect mask leaves the ex-white corners
as flat neutral fill (222,213,199), not painted wall, so arch-only composite
merely recolors the card. Rect-masked gen + arch composite is therefore NOT
acceptable; the paintable mask must become arch-shaped. Cost is small because
one derivation serves both: the white_key alpha that defines the composite
footprint IS the new socket mask (dilate ~2–3 px for keep-clear; everything
else paintable). Reversible: assets are generated artifacts — keep the rect
set alongside.

**Q2 keying guard.** white_key with preset-gi2 semantics: border-connected
flood only, thresh=246, sat≤18, **erode=0**, feather≤0.8, and NOT
`--reopen-interior` — the door leaf carries interior white paint specks that
must survive, and the stone frame's outer washes are pale/thin. erode=0 is the
edge protection: only pixels ≥246/≤18 sat are keyed, so the cut lands on the
near-white isophote and no morphological bite truncates the frame's wash
gradient. Gates (wrongly-removed-pixels precedent): (i) hard-fail if any
α<255 pixel violates the pure-white predicate (mn≥246, spread≤18) —
construction-guaranteed, but it tripwires parameter drift; (ii) removed set
must contain zero components not touching the raster border (catches leaks
through pale frame gaps into interior whites); (iii) junction review — magenta
and neutral-fill underlay crops at arch shoulders + bottom strip, NEAREST
8–12×, eyeballed. Also clip the keyed alpha by silhouette_mask (and holes):
overlay_socket.png shows the rect overhanging the panel's left edge, and
composite_back pastes AFTER the silhouette re-mask — unclipped, the arch's
left stones would repaint outside the panel (invisible under A's white rect,
a real defect under C).

**Q3 gate rescope — restriction, not weakening.** Byte-exact: domain =
{keyed α==255} ∩ placement footprint, same single native→target LANCZOS
resize; gate stays max|Δ|==0 over every fully-opaque pixel. Report separately:
feather-ring max|Δ| (existing 1 px art-side feather, now following the arch
contour), wrongly_removed_px (0), outside_silhouette_post_px (0). Registration:
expected footprint becomes the keyed-arch bbox plus the mask dilation, still
measured on the untouched candidate, tolerance unchanged at 1.5 px, fail-pre-fix
exit semantics unchanged. metrics.json gains alpha_domain_px, feather_ring_px,
wrongly_removed_px so the rescope is explicit in every record.
