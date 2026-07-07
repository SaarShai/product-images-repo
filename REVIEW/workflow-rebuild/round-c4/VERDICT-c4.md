# C4 verdict — ComfyUI vs round-3 gpt-image baseline (2026-07-06)

Boards: `round-c4-HEADTOHEAD-board.jpg` (baseline vs best arms) · `round-c4-overlay-board.jpg` (all 7, raw|overlay).
All 7 arms PASS door_fill containment (0.943–1.0) — but containment ≠ quality; ranked by eye below.

## Ranking (vision + geometry)
1. **i2i-hybrid** (`i2id5_s100/s300`, df 0.991) — WINNER. Init = baseline arm-g_s1, denoise 0.5, CN lineart 1.0 + IP 0.8. Keeps ~90% of the baseline's richness (teddy, dome+clock, topiary, balloons) AND hard-locks the door to the exact lineart contour. Best of both worlds.
2. **combined from-scratch** (`combe8_s100/s300`, endpct 0.8, df 0.979) — clean, correct geometry, but plainer: loses the character detail (no teddy/dome). Use when no good init exists.
3. **dualregion** (`dr55`, `dr75`, df up to 1.0) — DEAD END. Muddy olive at 0.5/0.5 & 0.7/0.5, rainbow-mud at s300; matches the earlier 0.9/0.9 mud. Regional dual-IPAdapter over-conditions at every weight tried. Abandon this arm. (High door_fill here is meaningless — the whole panel is a wash that trivially "fills" the portal.)

## vs gpt-image baseline (done-means #3)
- **ComfyUI BEATS gpt-image on geometry lock:** ControlNet hard-conditions the door to the SVG-derived lineart. gpt-image can only be prompted toward it and drifts — this is the structural conditioning gpt-image cannot do.
- **ComfyUI LOSES on raw style fidelity:** baseline arm-g_s1 is slightly crisper/cleaner. i2i recovers most of it but is a touch more washed.
- **Recommended production recipe:** gpt-image generates the rich style → ComfyUI i2i hybrid locks geometry. Neither alone is as good as the pipeline.

## Not run / next candidates
- SDXL-native 832×1184 canny lane — verified FEASIBLE NOW (all models on disk, no downloads). Higher-res, better base quality than SD1.5. Strong next probe.
- in-graph hires-fix (RAM free now) on the i2i winner.
