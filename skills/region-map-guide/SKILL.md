---
name: region-map-guide
description: Use when a generation must place several distinct elements in specific zones of a fixed die-cut/template panel, when per-element proportions keep coming back wrong (repeated regen/registration mismatch, art stretching, elements drifting), or when the user gives zone requirements ("door here, lamps there, nothing near the knobs") — build a semantic color-region map PNG (each flat color = one element's placement, avoid-zones as prohibitions) plus its auto-matched color→meaning legend prompt, feed map as image-1 + style ref + legend to the generator
status: proposed
source: /Users/za/Downloads/Wanderland-Packet-2026-07-11
learned_at: 2026-07-11
requires_tools: python3
disable-model-invocation: false
model-invocation-override: "user-directed 2026-07-12 — user explicitly asked for agent-suggested use ('make it also agent suggested where relevant and helpful'); telemetry lifecycle still applies (status stays proposed until promote gate clears; demote on >=3 consecutive aborts)"
auto-install: false
refined_at: 2026-07-12
---

# region-map-guide

> **Proposed skill** — born from `/learn`. Model-invocation enabled early by
> explicit user direction (see `model-invocation-override` above) instead of the
> normal telemetry-gated promotion; usage telemetry still governs promotion to
> `trusted` and demotion:
> `python3 skills/learn-skill/tools/learn.py promote --name region-map-guide` (needs N
> consecutive recorded hits, no trailing abort — see `learn-skill/SKILL.md` → Trust).

## When to Use
A generation must place several distinct elements in specific zones of a fixed panel (die-cut, template) and plain geometry guides or prose keep producing wrong per-element proportions — the symptom is repeated regen/registration mismatch (art stretches or elements drift). Also when the user hands you zone requirements ('door here, lamps there, no windows near the knobs') that need to become a generator-readable reference. Proven origin: Wanderland fire-station door — 5 regens failed, the color map cut registration distortion from ~26% to ~5%.

## Procedure
1. Get the panel silhouette from the REAL geometry source (SVG render / keyed PNG mask) — never hand-draw the contour (geometry-spec-single-source). 2. Author a region manifest JSON (see skills/region-map-guide/examples/wanderland-door.manifest.json): per region — name, means (plain-language element identity, used verbatim in the legend), shape (rect|circle|arch|band|dots|polygon in canvas coords), color as a PALETTE NAME (pink/grey/orange/blue/green/black/yellow/purple/cyan/brown — legend uses color words; one color = one meaning), avoid:true for keep-out zones. Region placement comes from user requirements and/or agent layout logic reading the die-line. 2b. If the target zone's aspect exceeds what the generator can output, expand the map canvas to the exact FULL-PANEL aspect and cover already-occupied zones with avoid-dots — the output then maps 1:1 onto the panel with no crop math (provider-specific evidence: gpt-image caps at 1536x1024, and the marine bedwrapper panel at 1.496:1 matched it almost exactly; reef strip below an existing turtle succeeded this way first try). 3. Build: python3 skills/region-map-guide/tools/build_region_map.py --manifest m.json --out map.png --legend-out legend.txt --expect-aspect W:H  (flat fills only; exits 2 on aspect mismatch, duplicate/unknown color, out-of-canvas region). 4. Feed to the generator: map as image-1 (locks aspect + per-element placement, per geoguide-input-locks-aspect), style reference as image-2, and the emitted legend.txt as the text prompt. 5. Gate the result with the standard overlay/geometry check (result-vision-judge / skyline_panel check) before accepting.

## Pitfalls
Do NOT draw strokes/outlines/text in the map — bold internal lines get traced into the art (guide-no-flap-outlines-trapezoid). Do NOT reuse a color for two meanings, including band vs inner region. Do NOT let the map's aspect drift from the panel spec — image-1 locks output aspect, so a wrong map poisons every gen (that is why the gate is exit-2, not a warning). Colors are arbitrary labels — the legend words carry the content (grey zone can mean a red door); never pick colors hoping the model paints that color. The map is a REGION reference, not art: always say 'do not draw the map's colors or outlines' (the emitted legend includes this). Region boundaries are SOFT for the generator — tops especially: in the marine reef run the left coral peak was painted ~500pt above its zone top into a cutout area (one observation; the user liked it, but it exceeded spec). If a ceiling is strict, lower the region top to leave margin, extend avoid-dots down to the ceiling, and reject via the overlay gate. PROVIDER DISCIPLINE: the map only locks aspect + zones on a geometry-disciplined provider (openai/gpt-image, subgen --provider openai). Nano/Gemini (subgen --provider nano) was tested 2026-07-12 and REJECTED — it ignored the zones, painted over the keep-clear dots, centered the tallest element instead of following the map left-cluster, did not lock aspect (output 1.792 vs map 1.500), and did not match the reference style. Do NOT use nano for region maps.

## Verification
python3 skills/region-map-guide/tools/test_build_region_map.py (happy path + 4 negative gate tests must pass). For a real panel: build with --expect-aspect from the panel spec, then eyeball the downscaled map against the die-line overlay before spending a generation. After generation, run the standard geometry/overlay gate.

<!-- Rationale (why this earns a skill) — scored by write-gate before commit:
User-requested agent-executable builder for the proven Wanderland color-region-map pattern; map + legend generated together so they cannot drift; aspect gate fails fast because a wrong-aspect map poisons every downstream generation.
-->
