# Inpaint→delta probe (GLM #2) — image14 results

Date: 2026-07-09  
Choice: user picked generative BG inpaint → delta mask over CFD.

## What was tried

1. **OpenCV Telea/NS inpaint** over dilated art erase mask → delta threshold  
   - Effectively ≈ constant-white fill (paper is already white).  
   - cut00/fringe still show white rim / jagged hard cut. Not a win.

2. **Codex full erase-to-paper** (quarter-res, no mask lock)  
   - Produced blank textured paper (mean ~249).  
   - Paper **grain ≠ original**, so `|src−paper|` speckles the whole canvas (opaque% 66–99 depending on thr). Unusable without alignment/lock.

3. **Codex masked erase** (keep black-mask pixels)  
   - Kept region locked correctly.  
   - Inside erase: only ~half the pixels moved toward white; mean RGB stayed colored (~231,216,214). **Did not reconstruct blank paper.**  
   - Delta then either overcuts pale paint or leaves BG.

4. **CV locked inpaint** (original outside erase; Telea inside) + delta thr=5  
   - Cleaner mechanically (delta outside erase = 0).  
   - Still the same visual failure class on cut00/fringe (white rim / hard edge). Architecture does not magically solve paint-white vs paper-white at the rim.

## Verdict

**Inpaint→delta is not the complete solution** with current tools:
- Classical inpaint doesn't invent true paper under large art; it bleeds neighbors.
- Codex erase either invents mismatched paper texture or fails to fully erase under a mask.
- Delta still needs a threshold → same pale-paint vs paper tradeoff.

## Artifacts

- `Images/candidates/image14-research/fusion-inpaint-v11/`
- Review: `REVIEW/image14-bg/USER_REVIEW/18-*`, `19-*`, `20-*`

## Next (needs user call)

- Try a **true LaMa / diffusion inpaint** with mask lock (not installed here), or  
- Accept that **pixel-only auto** may be ill-posed for this art and move to **semi-auto** (user marks sure-FG / sure-BG) + algebraic unmatte, or  
- Restart from **source generation** with transparent BG / cleaner edges.
