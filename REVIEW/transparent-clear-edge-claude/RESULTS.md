# Round 1 — clean-edge / color-hold prompt matrix (Claude lane)

Goal: same as the Codex "Improve transparent image workflow" session — find prompt structure/snippets that give clear contrasted edges on a solid background (+ optional color-hold outlines), tested by recreating the marine coral reference. This lane runs arms the Codex session did NOT.

Reference baseline: aura_index 0.145 (PASS). Codex arms: A white-control 0.132, B full colored-outline 0.080 (but VLM style 4.0 vs A's 4.6 — coloring-book drift).

## Arms (all share Codex's core content/style paragraphs for comparability; only edge/bg section varies)

| Arm | Edge/bg section | Verdict (metrics + keycheck) |
|---|---|---|
| M1 minimal color-hold | 2 sentences: closed local-color contours + tinted interior whites | aura 0.113/0.050 (≈ arm B) — clean key, no white ghosts. Compression holds. |
| M2 die-cut sticker framing | semantic "sticker" concept | aura ok BUT near-white corals survive as opaque ghosts — interior-white clause failed |
| M3 screen-print keyline framing | print-industry vocabulary | same interior-white failure (r1); high variance |
| M4 arm-B + style guard | full edge language + "watercolor pigment not ink; not a coloring book" | aura 0.111/0.097, clean key, style softer than bare arm-B |
| M5 color hold on #00FF00 | chroma-green background | BEST technically: keyed aura 0.026/0.031, borders clean (0.04% strip), interior whites become a non-issue |
| M6 selective contour (Sol's) | closed contour ONLY at silhouette/through-holes/junctions | aura 0.101/0.096, clean key, slightly airier crown |

Nano Banana ports (square-biased, recomposed): M1-nano 0.127, M4-nano 0.047 — data points only.

## Round-1 findings

1. The 3-paragraph arm-B edge block compresses to ~2 sentences (M1) with no measurable edge loss.
2. The load-bearing sentence is the interior-white one: "any white inside the illustration is a tinted off-white, never the background's pure white". Arms that rephrased it (M2/M3) shipped white-ghost defects.
3. Semantic framings (sticker/screen-print) are NOT better and carry the interior-white risk. Cut.
4. Chroma-green + color hold is the technically dominant combo (3× lower aura than any white arm, no white-vs-paint ambiguity). Style drift is the same as white arms.
5. Density/style drift is caused by the shared core ("dense but airy" → models paint dense), not by edge language. Round-2 fix = reference-authority core: "preserve the reference's silhouette, proportions, detail density; do not embellish".
6. aura_index is partly self-confirming (darker contours sharpen the detector's own edge signal) — style must be gated separately (pairwise, on keyed output).

## Files

- **fullres/raw/** — every full-size raw PNG (~2000×5000, 2.2MB each), labeled by arm
- **fullres/keyed/** — every keyed RGBA at full res (M5 = chroma-green, rest white-key)
- **fullres/REFERENCE.png** — the source coral image
- board_raw.jpg — thumbnail contact sheet of all raws (quick overview only)
- board_keycheck.jpg — keyed candidates on magenta (white ghosts visible in M2/M3)
- board_m6.jpg — M6 raw + keycheck
- metrics.md — full aura table
- Prompts: `tasks/transparent-clear-edge-claude/prompts/full-M*.txt`

## Round-1 user verdict (2026-07-12)

- **M1 minimal color-hold — WINNER.** Both r1 + r2 keyed = best options.
- **M3 screenprint r2 — also good** (but M3 high-variance; r1 weaker).
- **M6 selective-contour — mostly not good, EXCEPT r2-rgba = good** (high-variance arm).
- **M2 sticker — not great.** Cut.
- **M5 chroma-green — not good** despite best aura metrics → technical dominance ≠ user preference. Green path cut for this style.
- **General note (not priority):** all candidates still have *trapped* background regions — enclosed near-white gaps inside the illustration that the border-connected white-key leaves opaque. Keyer-side fix (interior-region reopen), deferred. Filed as background task.

Takeaway: the minimal 2-sentence edge block (M1) is the keeper. Verbose/semantic framings all lost. Winner is edge-language-minimal; the remaining lever is the CORE prose.

## Round 2 — LAUNCHED (core-swap test, white only, n=3 each)

Holds M1's winning minimal edge block constant; varies only the CORE to test finding #5 (density drift comes from core prose, not edges):
- **R2a-refauthority** — Sol's `[REFERENCE AUTHORITY]`+`[STYLE HOLD]` core (preserve reference density/proportions, do not embellish) + minimal edge. Full core swap.
- **R2b-m1-densitynudge** — M1 champion core verbatim + one sentence ("match reference proportions/density, do not embellish/densify"). Minimal change from champion.
- Compare both against reigning champion M1 r1/r2. Prompts: `prompts/full-R2{a,b}-*.txt`.

## Round-2 user verdict (2026-07-12)

- **All round-2 candidates equally great** — remaining differences are taste/style variation, not quality. Prompt problem effectively solved at the style/edge level.
- **New defect class — thin-branch keyability:** R2b-r1, R2a-r2, R2a-r3 each have a bottom-left coral with hair-thin branches that keyed badly (thin + pale = eaten/ragged). Zoom evidence: thin_branch_zoom.jpg.
- **New standing directive (banked to memory):** image-gen prompts must include keyability language when the subject could produce hard-to-key features (thin branches, hair, foliage). When fine detail is essential (forest etc.), direct the model to make it keyable instead of omitting it.

## Round 3 — LAUNCHED (keyability lane, white, n=3 each)

Base = R2a reference-authority prompt + one `[KEYABILITY]` module:
- **R3a-avoid-thin** — no hair-thin features at all; substantial widths, rounded tips, texture interior-only, chunky coral varieties.
- **R3b-keyable-fine** — fine branches allowed but full pigment strength, non-white mid-tone+, contoured, min stroke ~thick pencil, clustered into shared silhouettes.
- Judge: key → magenta composite → does the thin-branch defect disappear, and does R3b keep the airy character?
- Sol Ultra consulted in parallel on the general decision rule (avoid vs keyable-fine vs none) for the reusable directive.

## Round-3 result: 3/6 compliance → conflict diagnosed

Obeyed: R3a-r2 (chunky), R3b-r1/r3 (clustered fans). Ignored: R3a-r1/r3, R3b-r2 — thin skeleton returned with white ghosts. Cause: "preserve the reference's silhouette/motifs" vs "no thin features" is an internal contradiction (the reference HAS thin branches); the model picks a side at random. Sol confirms: prompt modules = probabilistic steering, not geometry guarantees; for essential fine detail change the extraction pipeline (native alpha > chroma > layer > matting), never rescue pale filaments with a white-key prompt.

## Round 4 — deviation authorization: 3/3 compliance. CLOSED.

One added sentence ("wherever the reference shows hair-thin branches, replace with a sturdier rounder variety of same color/position; keyability overrides reference fidelity for thin features only") took compliance from 3/6 → 3/3. r1/r3 keep the tall airy silhouette with sturdy keyable branches; r2 chunky; all keys clean. Board: board_round4_keycheck.jpg. Winning full prompt: `prompts/full-R4-deviation-authorized.txt`.

## Keyer upgrade (separate task, completed + adopted)

`scripts/white_key.py --reopen-interior` reopens trapped enclosed near-white background regions (purity+area guards protect tinted highlights). 4/4 tests; on R2a-r2: 48 regions / 33k px reopened, art intact. R4 keyed with it.

## Final deliverables

1. Winning prompt structure — `prompts/full-R4-deviation-authorized.txt` (reference-authority core + minimal edge block + keyability module + deviation authorization + exclusions).
2. Keyability decision rule — AVOID when fine detail optional; KEYABLE-FINE only when essential AND on chroma/native-alpha; neither when nothing keyed.
3. Upgraded keyer with interior reopen.
4. All banked to wiki + agent memory.
