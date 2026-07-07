# ENFORCEMENT MATRIX — every rule mapped to a mechanism (2026-07-06)

Legend: HOOK = main-loop tool-boundary guard (artifact_guard.py; leader-edited only).
LINT = deterministic preflight script. GATE = per-candidate pipeline gate.
RUNNER = round_runner.py single entry point (refuses to run without preflights).
TEST = pytest. CANARY = drift probe. VISION = leader vision + .approved marker file.

| # | Rule (source) | Was | Now enforced by |
|---|---|---|---|
| 1 | Geometry judged by overlay+metric only (user law) | prose | GATE door_fill (overlay always emitted) + RUNNER (results row requires overlay_path) + overlay_board pairs in every review board |
| 2 | No readable text in any ref (leak risk) | leader eye | LINT ref_lint.py (VLM text check) wired INTO build_style_handle — build fails on text |
| 3 | No open doors / white voids in refs | leader eye | LINT ref_lint.py open-door VLM check |
| 4 | Hold-out (no own-panel prior gen as ref) | prose | LINT in build_style_handle: provenance path patterns (round*/raws, outputs/) vs target panel → reject |
| 5 | One role per ref | code ✓ | build_style_handle validator (already) |
| 6 | No dashes / no text / stripes omitted in model guides | TEST ✓ | test_layout_ref (already) |
| 7 | Guide vision-gate before gen (S3b) | process | RUNNER preflight: refuses guides without sibling .approved marker (leader writes marker after vision review) |
| 8 | Callout zones clear stripes + anchor | one-off check | LINT callouts_lint.py in RUNNER preflight + TEST |
| 9 | Door fills true anchor (door-IS-the-arch) | none | GATE door_fill_gate (PASS/WARN/FAIL + overlay) |
| 10 | Flap area = door content only; door ends above bottom | prose | GATE content_gate.py flap-zone check |
| 11 | No sky/scenery — outside-silhouette near-white | prompt only | GATE content_gate.py outside-contour whiteness metric |
| 12 | Emblem count re-run POST-restyle | prose | RUNNER: any repair step auto re-runs emblem_gate (pipeline ordering) |
| 13 | Never overwrite/ruin a good raw | prose | HOOK artifact_guard: block Write/Edit/cp onto existing */raws/*.png |
| 14 | Round artifact contract (raws+overlays+boards+INPUTS+results.json+REVIEW copies) | briefs | LINT verify_round_artifacts.py — RUNNER exit gate + verifier lanes run it |
| 15 | Gen budget caps / stop conditions | briefs | RUNNER --max-calls counter, hard stop |
| 16 | Nano ban on tall panels (aspect enum) | memory | CODE falgen nbpro aspect assert (refuse <0.75 w/o --force) |
| 17 | Whitespace-only edits, zsh glob, done-claims | CANARY ✓ | compliance-canary probes (already) |
| 18 | Edit-without-read, ad-hoc cp into Images | HOOK ✓ | artifact_guard (already) |
| 19 | Subgen as ONLY subscription-gen path | memory | RUNNER is sole gen entry; leader Bash never calls codex/agy directly (canary-visible) |
| 20 | Inputs visible every round | SOP | RUNNER: inputs_board.py mandatory step |

Not mechanized (inherently judgment): style verdicts, complete-building aesthetics
(rubric axis = VLM-scored, human-decided), spec iteration. These stay leader/user.

Owners: E1=round_runner+verify_round_artifacts; E2=ref_lint+build_style_handle wiring;
E3=callouts_lint+content_gate; E4=falgen aspect guard; leader=artifact_guard raw-protect,
.approved markers, this matrix.
