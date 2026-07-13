# Round 5 — medium outlines (R22) + aggressive keying (R23)

Response to round-4 feedback: outlines too thick; stray green survived keying.

Dual track:
1. **Prompt fix** — new MEDIUM contour block (fine felt-tip weight instead of
   3× pencil). Two fresh gpt-image-2 gens: `H-G2-MED-GREEN-r1/r2`.
2. **Keying fix** — new `scripts/green_purge.py` aggressive pass (edge-band
   green suppression, 1px edge erode, near-key kill, baked-in speck kill,
   trapped-background removal with shape-based art protection, final dulling
   sweep). Applied to BOTH the new gens and the round-4 thick candidates
   (`H-G2-GREEN-r1/r2-repurged`) so you can compare like for like.

All 4 candidates: gate battery clean (no hard FAILs), 0 stray strong-green
pixels outside legitimate green art, converged purge.

Known residual: very faint olive traces between the fan filaments in MED-r1
(color blends that overlap legit seaweed shadows — removing them blind would
eat seaweed detail). Visible only at zoom. If it matters, the robust fix is
prompt-side: forbid bright pure-green art elements when generating on green
(so ALL green can be keyed unconditionally) — say the word and round 6 does that.

## Files

- `board-round5-dark.png` — 2 medium + 2 re-keyed thick, on dark
- `fullres/` — final RGBA + on-dark/on-white composites per candidate
- `zoom-MED-r1-edge.png` — medium-outline edge + fan closeup

## Questions

1. Medium outline weight — right now, or go thinner/thicker?
2. MED-r1 vs MED-r2 pick?
3. Residual faint olive in fan gaps at zoom level — acceptable, or lock the
   "no pure-green art on green key" prompt rule (round 6)?
