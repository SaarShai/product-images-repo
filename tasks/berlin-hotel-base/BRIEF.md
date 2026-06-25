# BRIEF — fix the Ritz/Beisheim tower BASE in the Berlin watercolor (shared packet)

All method-agents read this. Your method-specific instructions + output dir come in your dispatch prompt.

## GOAL
Replace the broken ground-floor / base section of the right-hand tower (The Ritz-Carlton Berlin / Beisheim Center) in the Berlin skyline watercolor so that the base reads as a **natural continuation of the building down to the water**, matches the artwork's exact style, and integrates **seamlessly** (no seam, no reframe, everything outside the edited region byte-stable).

DONE MEANS (the gate a separate verifier will apply):
1. Only the base region is changed — outside-region pixels identical (measured diff ≈ 0).
2. Style matches the artwork: fine architectural **watercolor + ink linework**, soft transparent washes, pale limestone, muted palette, soft daylight, **flat near-frontal elevation**.
3. The base is a **continuation of the facade** (vertical stone piers + regular windows continuing down to a modest ground floor meeting the stone quay/water). NOT a glass high-ceiling hall. NOT a canopy/marquee/porte-cochère. NO legible text/logos.
4. No reframe / no scale change / no perspective change vs the source.

## FILES (working copy — never touch Google Drive)
- SOURCE (read-only working copy): `tasks/berlin-hotel-base/work/src.png` (4192x3848). This is the full artwork.
- Convenience crop of the base area: `tasks/berlin-hotel-base/work/crop_base.png` (1070x420) = source region (3050,2480)-(4120,2900).

## GEOMETRY (full-source pixel coords, 4192x3848)
- Tower footprint (x): **3162 – 4082** (width ~920).
- BASE REGION TO REPLACE (the bad glass / ghost-canopy band): **y 2582 – 2828** (down to quay top). This is the only region you may change.
- KEEP UNTOUCHED: upper tower (y < 2582), stone quay coping + water (y > 2828), brick bridge + trees on the left (x < 3162).
- The CLEAN facade to continue is directly above: y ~2350–2580 — pale limestone, vertical piers, regular tall-window bays, floor period ≈ 88 px.
- In crop_base (1070x420) local coords, the band is x 112–1030, y 102–348.

## REFERENCES (feed these as IMAGES to engines — hard rule: never prose-only)
- `tasks/berlin-hotel-base/work/building_artwork_guide.png` — the artwork's OWN building (crown→base). Primary STYLE + PERSPECTIVE + PROPORTION anchor.
- `tasks/berlin-hotel-base/work/tower_facade_above.png` — the artwork's facade rhythm you must continue downward.
- `tasks/berlin-hotel-base/refs/ritz_cahill2.jpg` — BEST real full-tower photo (limestone, vertical pilasters, stepped crown, left podium, base).
- `tasks/berlin-hotel-base/refs/ritz_cahill1.jpg`, `ritz_cahill3.jpg` — more real tower views.
- `tasks/berlin-hotel-base/refs/ritz_streetlevel.png` — clean real BASE / ground-floor view.
NOTE: the user DROPPED the canopy idea. The base is just the limestone facade continuing down. `refs/entrance.png` and `refs/canopy_bahnhof.jpg` are historical — do NOT add a canopy.

## TOOLS (keys already in .secrets/)
- `scripts/falgen.py --mode {fill,kontext,flux2edit,eraser}` — fal Flux. `fill` = masked inpaint (in-frame, framing-safe); `kontext` = instruction edit; `--mask`, `--mask-box`, `--seed`, `--maxside`, `--cache`.
- `scripts/falref_apply.py` — fal flux-2-pro/edit with reference images (image_urls). High ref fidelity but TENDS TO REFRAME — counter with explicit flat-elevation wording. (`--src --crop x0,y0,x1,y1 --ref R --ref R --prompt-file P --out O`)
- `scripts/subgen.py --provider {openai,nano}` — subscription gpt-image / Nano Banana; multiple `-i` input images. openai gives tall 1024x1536; nano squares + reframes.
- `scripts/controlnet_sdxl_gen.py` + `scripts/measure_sdxl_cn.py` — local SDXL inpaint + canny ControlNet on a lineart guide (geometry-exact). MPS VAE grey-tint → white-out holes if any.
- `scripts/automask.py` (SAM-3 text→mask), `scripts/compose_fairy.py --diffmask` (region-only composite, outside delta must be 0), `scripts/judge.py` (VLM check / pairwise).
- PIL is fine for procedural work (tiling, warp, homography, masks).

## CONSTRAINTS (inlined — hooks do NOT fire inside you; obey anyway)
- REFERENCE-BEATS-PROSE: drive generation with the reference IMAGES, never description alone.
- NO REFRAME: keep the flat near-frontal elevation, same scale and framing as the source. Reject your own outputs that zoom/rotate/3-D the building.
- REGION-ONLY: change only y2582–2828 within x3162–4082; everything else must stay byte-identical. Use a feathered mask / diffmask composite and MEASURE the outside-region delta.
- VERIFY BEFORE CLAIMING: actually open every image you produce and report what you SEE. Never claim "done".
- Terse reporting.

## OUTPUT
Write ALL your files under your assigned dir `tasks/berlin-hotel-base/work/<your-m-dir>/`. Produce BOTH:
(a) the raw/standalone generation(s), and (b) at least one version composited into the FULL artwork (paste your base into a copy of src.png, region-only) named `<m>_composited.png`, plus a base zoom `<m>_zoom.png`.

## REPORT CONTRACT (your final message — end with "READY FOR JUDGING", never "done")
- Every candidate file path + a one-line visual verdict (what you actually see).
- Your recommended pick and why.
- Exact engine + params/prompt used for the pick.
- Attempts tried and abandoned (approach → outcome → why).
- Assumptions made where this brief was silent.
- Failures / blockers.
