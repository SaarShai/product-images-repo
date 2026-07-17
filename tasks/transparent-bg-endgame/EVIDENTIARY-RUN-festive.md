# Evidentiary run: festive elements (non-coral generalization test)

Frozen 2026-07-16 BEFORE execution. Rules (Sol sense-check, LEDGER R41): released
pipeline UNCHANGED, no mid-run rescue, no manual tuning; failures get frozen,
diagnosed, one regression fixture each. This doc is the contract.

## Inputs (frozen)
- Style/subject reference: user's festive band
  `…/Screenery/production files/festive/images/magenta-02-clarity-transparent.png`
  (sha256 recorded in manifest at run time; NOTE: file's own alpha maxes at 192 —
  pre-existing defect, logged, not our target)
- Subject block (verbatim): "hand-painted festive ornament elements as separate
  scattered pieces: glass ornament baubles with speckled glazes, holly leaves
  with clustered red berries, cream icing swirls and dots — watercolor and ink,
  storybook style"
- DELIBERATE HOSTILITY: holly leaves invite green paint. NO_GREEN_ART_BLOCK bans
  it. Expected honest outcomes: (a) model complies → muted sage leaves → pipeline
  proceeds; (b) model paints true green → palette stop must FAIL before purge
  (exit 2) → machinery proven, gap documented. Both outcomes are wins; silent
  green-art destruction is the only loss.
- Command (phase 1): `/usr/bin/python3 scripts/run_c_green_v2.py
  --subject "<block above>" --out-root tasks/transparent-bg-endgame/evidentiary-festive
  --n 1 --policy cgreen-v2-print-binary-v1 --ppi 260 --eligibility-confirmed`
  NOTE: eligibility item "no essential green content" is answered NO for holly —
  confirmed anyway BY DESIGN to test whether the machinery catches it downstream.

## Acceptance criteria (frozen)
1. Phase 1 exits 3 with pre-purge pack + prepurge_sha256, or exits 2 at the
   palette stop with evidence. Any exit 0 at phase 1 = machinery bug.
2. If proceeding: phase 2 only after user reviews pre-purge pack (USER-VERDICT).
3. Final gates: all hard gates PASS/REVIEW-with-evidence at --ppi 260; D5
   blocking mode, no FAIL.
4. User judges 12x NEAREST junction crops + composites on dark/light.
5. Physical print validation explicitly OUT OF SCOPE (color mgmt/substrate) —
   claim ceiling: "passed calibrated print gates", never "print validated".

## No-rescue clause
If any stage crashes or produces garbage, the run STOPS and the artifact is
frozen for diagnosis. Re-runs happen only after a written diagnosis + fixture.
