# Transparent-BG Endgame — Full Session Report (on the record)

Date: 2026-07-13 · Session: 9e28116f · Commits: 1e3c438 … d5b8e30 · Status: Route validated by user ("best yet — bank it"), banked.

Audience: any agent generating product images and/or removing backgrounds in this repo. Read this before starting such a task. The operational recipe lives in `skills/transparent-product-image-gen/SKILL.md` (Routes P and C-green v2); this report is the evidence record behind it.

---

## 1. Problem statement

Print production needs high-res RGBA product illustrations with **faultless** transparent backgrounds:
- no bright/semi-transparent edge halos (D1/D2),
- no holes punched in art by removal (D5),
- no trapped background pockets in concavities (D3),
- no stray background-colored pixels at any zoom (D6-class spill).

Multiple prior sessions (Claude desktop + Codex) attempted this and failed in repeated ways. This session mined those failures, researched, then ran 7 generation/keying rounds to a user-validated route.

## 2. What prior-session review found (session mining, R5)

- ML background removers (BRIA, BiRefNet) **delete art** — up to 18.7% of thin-branch strokes gone. Never use on fine watercolor art.
- Naive keyers (magick/ffmpeg one-threshold) leave 864–1559 green flecks.
- `scripts/chroma_key.py` (global Lab ΔE, two-threshold, band-confined despill) was the only method in a 6-way frozen-mask shoot-out with 0 residual green AND 0 deleted art.
- Halo'd output had repeatedly been shipped as "done" — agents are artifact-blind at board scale. Root fix this session: calibrated detector battery + high-zoom judging (see §5, §6).
- Non-anti-aliased-edge prompting had **never actually been tried** before this session, despite being discussed.

## 3. Route landscape (validated this session)

Two complementary routes, chosen by model capability:

**Route P — native alpha (primary when supported).**
`gpt-image-1`, `gpt-image-1.5`, `chatgpt-image-latest` accept `background=transparent` and return real alpha. Yield ~1/3 through the print gate battery. gpt-image-2 proper returns HTTP 400 on `background=transparent` (empirically confirmed) — hence Route C-green.

**Route C-green v2 — flat key background + removal (for models without native alpha).**
This session's main product. Validated on gpt-image-2 via Responses API async job (`background:true`; sync connection dies ~75s; `input_fidelity` 400s). Green `#00FF00` beats magenta: ~2× ΔE separation (11.5 vs 6.8), and round-4 A/B showed green ≈4× less halo-prone.

## 4. The seven rounds (what failed, what fixed it)

| Round | Change | User verdict / finding |
|---|---|---|
| 1-3 | Native-alpha O-route, HARD non-AA edge prompt levels, rich-style push | O1/O2 edges "perfect"; C-route leaked green; direction = thicker outlines + richer style |
| 4 | gpt-image-2 on GREEN/MAGENTA flat key + THICK contour | "Improvement, but": outlines excessive; stray green px survive keying |
| 5 | MEDIUM contour + new `scripts/green_purge.py` (erode, edge-band suppression, speck kill, shape-protected trapped-bg removal) | Good except thin-branch coral junction artifacts; still a few strays |
| 6 | `NO_FILAMENT_BLOCK` (bans hair-thin strand fans) + `NO_GREEN_ART_BLOCK` (bans pure-green art) + purge `--no-green-art` | User zoomed further: dark-green fringe at junctions/notches persists |
| 6b | purge v3: `--erode 2 --band 6`, band declamp, global green cap, olive-notch kill, dark-khaki neutralize | Still stray greenish px; user challenged: "why any strays if edges are non-AA?" |
| 7 | `SIGNIFICANT_CONTOUR_BLOCK` — mandatory, non-negotiable visible slim dark ink contour on every silhouette | **"best yet! bank it"** — all non-advisory gates PASS; D5 advisory REVIEW; overall battery verdict REVIEW/exit 3; user accepted both candidates after reviewing D5 crops and 12× junction crops. |

## 5. Root causes discovered (the durable knowledge)

1. **Generation models cannot paint true non-anti-aliased edges.** Boundary pixels are always fully-opaque art⊕background color *blends* — not semi-transparent alpha. No prompt makes them binary. Therefore stray key-colored pixels are inevitable **unless the blend lands on dark ink instead of art color** → mandatory visible dark contour. Prompt phrasing matters: round 5's polite "fine felt-tip outline" was under-painted; round 7's "NON-NEGOTIABLE … if any part of the silhouette lacks a visible dark contour line the image is wrong" was obeyed. Wiki: `wiki/concepts/mandatory-ink-outline-edge-defense.md`.
2. **Legit key-colored art is colorimetrically inseparable from trapped key background.** Sampled seaweed at RGB [1,137,0] vs key #00FF00 — no color-only rule separates them. Two working resolutions: (a) ban the hue in the prompt (`NO_GREEN_ART_BLOCK`) → purge may kill green unconditionally; (b) shape-based separation — max inscribed radius ≥7px marks solid legit mass (bbox-fill solidity FAILS on wavy/thin leaves). Wiki: `wiki/concepts/key-colored-art-vs-trapped-background.md`.
3. **Judging must happen at 12× NEAREST on junction/notch crops**, not board scale, not 4× only. User caught defects at zooms the review boards hid, twice.

## 6. Tools built/hardened this session

- `scripts/green_purge.py` (NEW): post-key stray-pixel eliminator. Passes: alpha erode → edge-band green-dominance repaint → (`--no-green-art`: band declamp, global green cap, geometry-restricted olive-notch kill, dark-khaki neutralize) → small-component near-key ΔE00 kill → strong-green speck kill (inscribed-radius-protected) → trapped-bg removal → converging dulling sweep. Validated flags: `--no-green-art --erode 2 --band 6`.
- `scripts/gates/gate_battery.py` (v4): D1 halo, D2 soft alpha, D3 pockets/retained bg, D4 aura, D5 holes (advisory), D6 spill, D7 border, D8 alpha sanity. Exit 0/3/2 = PASS/REVIEW/FAIL. Calibrated on known-good art (no false FAIL); caught a real ground-tuft defect in round 3. On 2026-07-16, the exact command `/usr/bin/python3 -m pytest tests/ skills/_shared/ -q 2>&1 | tail -1` reported 396 passed, 3 xfailed, and 180 warnings (399 collected), including `tests/test_green_purge.py` (6 focused tests: donor-safety, fail-closed residual-key exit, thin-branch-under-erode, in-place rejection, clean-passthrough regression). Caveat: the thin-branch test's core assertion is weak (`result[...].sum() >= 0`, i.e. non-negative — a sanity check, not a real lower bound on surviving alpha), so it does not tightly pin the erode/branch-survival contract.
- `scripts/dehalo_edge.py`: recovered from orphaned branch (R12), committed 1e3c438.
- Prompt block library (`tasks/transparent-bg-endgame/round*/gen_round*.py`): SUBJECT_V2, RICH_STYLE, SIGNIFICANT_CONTOUR, NO_FILAMENT, NO_GREEN_ART, EXCLUSIONS, key_bg_block(), HARD_EDGE, ANTI_AURA.

## 7. Validated pipeline (Route C-green v2, one line per step)

1. Compose prompt: SUBJECT + RICH_STYLE + **SIGNIFICANT_CONTOUR** + NO_FILAMENT + NO_GREEN_ART + EXCLUSIONS + key_bg_block(green) + HARD_EDGE.
2. Generate: gpt-image-2, Responses API async (`/usr/bin/python3`, NOT bare `python3` — PATH python lacks requests/PIL/numpy).
3. `scripts/chroma_key.py key in.png out.png --json k.json`
4. `scripts/decontam_binarize.py --rgba out.png --out d.png --bg-color '#00FF00'`
5. `scripts/green_purge.py d.png p.png --no-green-art --erode 2 --band 6 --json g.json`
6. `scripts/gates/gate_battery.py --rgba p.png --source raw.png --bg-color '#00FF00' --profile print --out-dir gates/`
7. Judge crops at 4× LANCZOS **and 12× NEAREST** at junctions/notches; user reviews boards + fullres in `REVIEW/<task>/`.

## 8. Failed approaches — DO NOT RE-TRY

- **Hue-snap** (force edge-band pixel hue to nearest interior donor): drove hue metric ~0 but caused visible color banding/saturation damage. Reverted (`git checkout 3b0d0c3 -- scripts/green_purge.py`).
- **Bbox-fill solidity** as legit-art test: false on wavy/thin shapes; use max inscribed radius.
- **ML matting on fine art** (BRIA/BiRefNet): deletes art.
- **Prompt-only non-AA edges without enforced contour**: physically impossible (§5.1).
- **Magenta key**: 2× worse ΔE separation, 4× more halo-prone than green.
- **Softly-worded outline instruction**: model under-paints; mandatory framing required.

## 9. Where things were banked

- Skill: `skills/transparent-product-image-gen/SKILL.md` → new "ROUTE C-green v2 — USER-VALIDATED recipe (2026-07-13)" section.
- Wiki: `wiki/concepts/mandatory-ink-outline-edge-defense.md`, `wiki/concepts/key-colored-art-vs-trapped-background.md` (+ L1 index, log).
- Auto-memory: `chroma-green-transparency-workflow` (UPGRADE paragraph → v2).
- Ledgers: `tasks/transparent-bg-endgame/LEDGER.md` R1–R28 (mirror in `.brainer/ledger/`).
- Commits: `074543a` (round7), `d5b8e30` (banking), this report.

## 10. Open items / remaining risks

- Recipe validated on ONE subject class (coral cluster). First run on a new product class must keep the 12× junction check and expect prompt-block tuning.
- **D5 hole gate is UNCONDITIONALLY advisory** (`CALIBRATION["D5_hole_gate"]["advisory"] = True` in `scripts/gates/gate_battery.py`, not conditional on `--no-green-art` or any flag) — it can never hard-fail/block a ship today, regardless of how much art it flags as deleted. Round-7 x4 `battery.json` (`tasks/transparent-bg-endgame/round7_outline/gates_x4/H-G2-OUT-GREEN-r1-x4/battery.json`) records `"truth": null` (no ground-truth reference supplied) and a source-heuristic-estimated `deleted_area_frac_of_expected` of **5.30%** (r1) / **4.86%** (r2) with `"pass": false` on that gate — yet overall `verdict` is `REVIEW` (exit 3), not `FAIL`, precisely because D5 is advisory. This is an open risk: a run that deleted real art on the order of ~5% of expected foreground area can still reach REVIEW/ship review without a hard block; only human 12× NEAREST review currently catches it.
- x4 print upscale: **honest restatement, not "VALIDATED."** `chroma_key_upscale.py --binary-alpha` is required for print (plain Lanczos alpha reintroduces soft px → D2 FAIL). Round-7 x4 outputs pass the PIXEL-fallback gates (D2 `soft_px: 0`, alpha strictly `{0,255}`) with overall verdict `REVIEW` (only advisory D5 blocking). But both `battery.json`s for round-7 x4 show `"units": {"physical_units": false, "units_advisory": "ppi/px-per-mm missing; mm thresholds reported as REVIEW-only fallbacks where needed"}` — D1 halo area (mm²), D2 fringe width (mm), and D4 shell width (mm) all fell back to PIXEL thresholds, not the calibrated physical (mm-based) print thresholds. `scripts/run_c_green_v2.py` does accept a `--ppi` flag (passed through to `gate_battery.py --ppi`), but the round-7 x4 runs that produced these gate files were not run with `--ppi`, so physical-unit print calibration for this recipe has NOT yet been demonstrated end-to-end. Re-run with `--ppi <panel ppi>` before treating x4 print output as calibrated for physical print tolerances.
- `/usr/bin/python3` requirement is enforced by ImportError guards in both scripts; bare `python3` exits 2 with a rerun message when numpy/PIL are unavailable.
- Geometry-adherence composition (R13) deferred — own round.
- Native-alpha Route P yield ~1/3 — acceptable, but batch accordingly.
