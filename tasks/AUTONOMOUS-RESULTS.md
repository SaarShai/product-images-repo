# REVIEW — all results (links, contour overlays, cross-model verdicts)

How to read: **SET** = assembled 3-panel preview. **OVERLAY** = that panel fit into the real die-cut
template with guides drawn (lime = panel contour/dome, magenta = saloon arch + cut features, red =
keep-clear). **Cross-model** = codex GPT-5.5 + GLM-5.2 objective check (one image per call).

---
## A. READING CORNER  (theme = "magic of reading"; studied refs; creative elements OK)

### Complete sets — pick one (towers are shared; swap the door freely)
- castle-portal: [SET-reading-corner-v2.png](skyline-reading-corner/plan/SET-reading-corner-v2.png)
- book-library: [SET-reading-corner-library.png](skyline-reading-corner/plan/SET-reading-corner-library.png)
- cozy tree-nook: [SET-reading-corner-nook.png](skyline-reading-corner/plan/SET-reading-corner-nook.png)
Cross-model on v2: door_in_arch ✓✓; codex no hard crop; GLM flagged the open BOOK low at the bottom die-cut
+ wizard/knight near the narrow center lanes; codex: center panel busy. (advisory)

### Door candidates  (raw · contour overlay)
- A castle-portal: [raw](skyline-reading-corner/sub/RC-door-geoA1.png) · [overlay](skyline-reading-corner/plan/check-RC-door-geoA1.png)
- B book-library: [raw](skyline-reading-corner/sub/RC-door-geoB1.png) · [overlay](skyline-reading-corner/plan/ov-RC-door-geoB1.png)
- C cozy tree-nook: [raw](skyline-reading-corner/sub/RC-door-geoC1.png) · [overlay](skyline-reading-corner/plan/ov-RC-door-geoC1.png)
- board: [BOARD-door-directions.png](skyline-reading-corner/plan/BOARD-door-directions.png) · alternates: RC-door-geoA2; artwork-only RC-door-A1/A2/B1/B2

### Narrow panels  (raw · overlay)
- LEFT wizard tower: [raw](skyline-reading-corner/sub/RC-left-geoW2.png) · [overlay](skyline-reading-corner/plan/ov-RC-left-geoW2.png) (alt RC-left-geoW1)
- RIGHT knight tower: [raw](skyline-reading-corner/sub/RC-right-geoK2.png) · [overlay](skyline-reading-corner/plan/ov-RC-right-geoK2.png) (alt RC-right-geoK1)

---
## B. GINGERBREAD  (watercolor gingerbread house + candy towers)

### Complete sets — pick one
- single-door house: [SET-gingerbread-v2.png](skyline-gingerbread/plan/SET-gingerbread-v2.png)
- double-door + gingerbread people: [SET-gingerbread-characters.png](skyline-gingerbread/plan/SET-gingerbread-characters.png)
Cross-model on v2: door_in_arch ✓✓; codex keep-clear CLEAN (v2 patch worked); GLM flagged minor candy at the
seams + slight L/R asymmetry. (advisory)

### Door candidates  (raw · overlay)
- 1 single arched door: [raw](skyline-gingerbread/sub/GB-door-geo1.png) · [overlay](skyline-gingerbread/plan/ov-GB-door-geo1.png)
- 2 double door (matches 2-flap split): [raw](skyline-gingerbread/sub/GB-door-geo2.png) · [overlay](skyline-gingerbread/plan/ov-GB-door-geo2.png)
- B double door + gingerbread people: [raw](skyline-gingerbread/sub/GB-door-geoB1.png) · [overlay](skyline-gingerbread/plan/ov-GB-door-geoB1.png)
- board: [BOARD-door-directions.png](skyline-gingerbread/plan/BOARD-door-directions.png) · alternates: artwork-only GB-door-A1/A2/A3

### Narrow panels  (raw · overlay) — keep-clear-patched (candy-cane stripe on center, focal in side columns)
- LEFT tower: [raw](skyline-gingerbread/sub/GB-narrow-v2a.png) · [overlay](skyline-gingerbread/plan/ov-GB-narrow-v2a.png)
- RIGHT tower: [raw](skyline-gingerbread/sub/GB-narrow-v2b.png) · [overlay](skyline-gingerbread/plan/ov-GB-narrow-v2b.png)
- alternates (pre-patch, centered candy): GB-narrow-geo1/2/3/4

---
## C. PRINCESS — fixing / improvement
- **Improved narrow-01 (all 3 fairy anatomies fixed + composited):** [narrow01-improved-all.png](princess-improve/sub/narrow01-improved-all.png)
- Anatomy donors: door [PA-dpBL](princess-improve/sub/PA-dpBL-anat.png) / [PA-dpBR](princess-improve/sub/PA-dpBR-anat.png); narrow-01 [PA-n1TL](princess-improve/sub/PA-n1TL-anat.png) / [PA-n1ML](princess-improve/sub/PA-n1ML-anat.png) / [PA-n1R](princess-improve/sub/PA-n1R-anat.png); narrow-02 [PA-n2ML](princess-improve/sub/PA-n2ML-anat.png) / [PA-n2LR](princess-improve/sub/PA-n2LR-anat.png)
- Geometry-tighten: narrow-02 production already fits its die-cut (geom PASS, fill 0.903).
- Learnings (easy/hard per change-type): [LEARNINGS.md](princess-improve/LEARNINGS.md)

---
## Method / tooling
- `scripts/skyline_panel.py` (geometry guide to feed gen + overlay check) · `scripts/codex_judge.sh` (codex vision judge)
- Cross-model judge panel + one-image rule: `docs/JUDGING_PROTOCOL.md`
