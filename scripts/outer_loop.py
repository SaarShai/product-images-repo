#!/usr/bin/env python3
"""outer_loop.py — SCAFFOLD for the verdict-feedback outer loop.

Refines the geometry generator skill from accumulated graded runs. This is the
loop SHELL with every gate from .brainer/outer-loop-plan.md encoded as CODE; the
expensive image-gen + result-vision-judge calls sit behind an INJECTABLE callable
boundary so the whole control flow is unit-testable WITHOUT spending budget.

Spec source (verbatim authority): ../.brainer/outer-loop-plan.md — twice
adversarially reviewed. The loop spec below is loop_lint-ready and is what
`loop_lint.py scripts/outer_loop.py` parses.

STATUS: scaffold. The real image-gen round, carving the prompt sets from
results.jsonl, and any git commit are DEFERRED (not done here). Round 1 must be
run MANUALLY (human adopts/rejects the patch) before any unattended round.

THE TWO-TIER GATE (CoEvoSkills arXiv:2604.01687; tightened by 2nd-pass review):
  - Surrogate tier (cheap, every round): region_iou on the candidate/TRAINING set.
    Deterministic. The generator advances only if surrogate median rises.
  - Oracle tier (expensive, only on surrogate-pass): full result-vision-judge on a
    FROZEN HELD-OUT set the patch-proposer never sees. THE ORACLE RETURNS NOTHING
    TO THE GENERATOR — not per-panel iou, not the delta map, not judge critiques,
    and NOT the held-out median scalar. Only {pass_bit, median_scalar} flow to the
    GATE, the LOG, and the HUMAN. If the generator wants finer signal it re-runs
    the CHEAP surrogate on the TRAINING set — never the held-out set.

THREE FROZEN SETS, never mutated after round 1:
  (a) TRAINING       — the cluster-analysis evidence the generator may see.
  (b) HELD-OUT oracle — ≤12 prompts NOT used to derive clusters; oracle-only.
  (c) FRESH (cross-template) — a DIFFERENT task/template distribution; the only
      thing that catches a global-surface patch silently regressing other templates.

```loop
name: outer-loop-geometry-refine
topology: outer closed single
generator: learn-skill refinement agent — reads clustered FAIL modes from the TRAINING surrogate, proposes ONE patch to svg-template-style-agent/SKILL.md targeting filled-contract placement; never sees any held-out number
verifier: result-vision-judge run on the FROZEN held-out set (separate actor from the generator); emits only pass_bit + median scalar to gate/log/human
gate: two-tier — surrogate region_iou median rises on TRAINING (python3 scripts/geom_iou.py), then oracle held-out region_iou median >= 0.85 AND no style_score regression AND per-prompt non-regression (no prompt passing >=0.85 drops below 0.85)
stop: held-out region_iou median >= 0.85, OR no improvement 2 consecutive rounds, OR max_iterations reached
budget: max_iterations = 5; max image-gen calls = 60
anchor_files: tasks/<t>/RESULTS/outer-loop-log.jsonl, skills/svg-template-style-agent/SKILL.md
state_store: tasks/<t>/RESULTS/outer-loop-log.jsonl
recall: read prior rounds from outer-loop-log.jsonl before proposing
writeback: append per round to tasks/<t>/RESULTS/outer-loop-log.jsonl — proposed patch diff, verifier verdict, region_iou delta, decision (immutable)
stuck: on no-improvement, request structurally-different geometry-contract strategies from the advisor (feeds generator only, never the gate)
advisor: cross-vendor panel via skills/_shared/model_roster.py proposing divergent geometry-contract strategies; read-only; separate from the verifier
redaction: model_roster.render_prompt scrubs secrets/.env/keys/PII before any cross-vendor egress (GPT-vision crosscheck / advisor)
consent: cross-vendor egress requires --consent / MODEL_ROSTER_EGRESS_CONSENT=1
output_actions: propose-skill-patch:1/round (default-deny; human approves adoption; never auto-merge)
egress: cross-vendor GPT-vision crosscheck inside result-vision-judge + advisor panel
```
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

# --- Constants from the spec (hard caps; do not loosen without re-review) -----
MAX_ITERATIONS = 5
MAX_IMAGE_GEN_CALLS = 60
HELD_OUT_PROMPT_CAP = 12          # held-out set ≤ 12 prompts × 5 rounds = 60
FINAL_IOU_THRESHOLD = 0.85
NO_IMPROVE_STOP_ROUNDS = 2
PROPOSE_PATCH_CAP_PER_ROUND = 1   # output_actions allowlist {propose-skill-patch:1/round}


# --- Frozen-set guard --------------------------------------------------------

class FrozenSet:
    """A prompt set frozen at round 1. Any mutation attempt after freeze raises —
    test-set contamination (adding a 'harder held-out panel' mid-loop) is a spec
    violation, not a tuning knob."""

    def __init__(self, name: str, prompts: list[str]):
        self.name = name
        self._prompts = tuple(prompts)   # tuple => immutable storage
        self._frozen = False

    def freeze(self) -> None:
        self._frozen = True

    @property
    def prompts(self) -> tuple[str, ...]:
        return self._prompts

    def __len__(self) -> int:
        return len(self._prompts)

    def mutate(self, *_a, **_k):
        raise RuntimeError(
            f"FrozenSet '{self.name}' is immutable after round 1 — "
            "mutating a frozen held-out/fresh set is test-set contamination (spec R: NEVER mutate).")


# --- Oracle result: the ONLY two values that may leave the oracle -------------

@dataclass(frozen=True)
class OracleResult:
    """What the oracle (held-out result-vision-judge) returns. By construction this
    is the ENTIRE oracle surface: a pass bit + a single median scalar. Per-panel
    iou, delta maps, judge critiques, per-prompt numbers DO NOT EXIST on this
    object, so they CANNOT be passed to the generator even by accident.

    The median scalar goes to the GATE / LOG / HUMAN only. It is never put into any
    structure handed to the generator (see _generator_view, which strips it)."""
    pass_bit: bool
    median_scalar: float          # held-out region_iou median — gate/log/human ONLY
    style_ok: bool                # no style_score regression on held-out
    per_prompt_nonregression_ok: bool  # no previously-passing prompt dropped <0.85


# --- Injectable callable boundary (the expensive surface) --------------------
# Generator: proposes ONE skill patch from the TRAINING surrogate signal only.
# Surrogate: cheap region_iou over a set of prompts (deterministic; runs every round).
# Oracle:    expensive held-out result-vision-judge; returns ONLY an OracleResult.
# Advisor:   cross-vendor divergent panel; feeds the generator on stuck, never the gate.

GeneratorFn = Callable[[dict], dict]          # (generator_view) -> {"patch": str, "patch_id": str}
SurrogateFn = Callable[[tuple, dict], dict]   # (prompts, patch) -> {"per_prompt": {p: iou}, "median": float}
OracleFn = Callable[[tuple, dict, dict], OracleResult]  # (held_out, patch, prev_pass_map) -> OracleResult
AdvisorFn = Callable[[dict], str]             # (redacted_context) -> divergent strategy text


@dataclass
class LoopConfig:
    task: str
    training: FrozenSet
    held_out: FrozenSet
    fresh: FrozenSet
    generator: GeneratorFn
    surrogate: SurrogateFn
    oracle: OracleFn
    advisor: Optional[AdvisorFn] = None
    consent: bool = False                    # cross-vendor egress consent (R12b)
    dry_run: bool = True
    log_path: Optional[Path] = None
    max_iterations: int = MAX_ITERATIONS
    max_image_gen_calls: int = MAX_IMAGE_GEN_CALLS


@dataclass
class RoundRecord:
    round: int
    patch_id: str
    surrogate_median: float
    surrogate_delta: float
    surrogate_passed: bool
    oracle_invoked: bool
    oracle_pass_bit: Optional[bool]
    oracle_median: Optional[float]       # gate/log/human surface — NOT generator
    style_ok: Optional[bool]
    per_prompt_nonregression_ok: Optional[bool]
    decision: str
    image_gen_calls_used: int
    advisor_consulted: bool = False
    note: str = ""


class BudgetError(RuntimeError):
    pass


class ConsentError(RuntimeError):
    pass


# --- Information-isolation barrier --------------------------------------------

def _generator_view(cfg: LoopConfig, training_surrogate: dict, prior_rounds: list[RoundRecord]) -> dict:
    """Build the ONLY dict the generator is ever handed. It contains:
      - the cluster summary + TRAINING surrogate per-prompt iou (the generator MAY
        re-run the cheap surrogate on TRAINING for finer signal),
      - prior PROPOSED patches + their TRAINING-side deltas and DECISIONS.
    It contains NO held-out number — not per-prompt, not the median scalar. This
    function is the single chokepoint; the oracle median is never threaded in.

    Asserts the invariant before returning so a future edit that leaks a held-out
    field trips the self-test immediately."""
    view = {
        "task": cfg.task,
        "training_per_prompt_iou": dict(training_surrogate.get("per_prompt", {})),
        "training_median": training_surrogate.get("median"),
        "prior_patches": [
            {
                "patch_id": r.patch_id,
                "training_surrogate_median": r.surrogate_median,
                "training_surrogate_delta": r.surrogate_delta,
                "decision": r.decision,
                # DELIBERATELY ABSENT: oracle_median, oracle_pass_bit, per-prompt held-out.
            }
            for r in prior_rounds
        ],
    }
    _assert_no_heldout_leak(view)
    return view


_FORBIDDEN_GENERATOR_KEYS = (
    "oracle", "held_out", "heldout", "held-out", "oracle_median", "oracle_pass_bit",
    "per_panel", "delta_map", "judge_critique", "fresh_set", "cross_template",
)


def _assert_no_heldout_leak(obj, _path: str = "view") -> None:
    """Recursively assert no forbidden held-out/oracle key reaches the generator.
    Raised as AssertionError so the self-test asserts the barrier holds."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            kl = str(k).lower()
            for bad in _FORBIDDEN_GENERATOR_KEYS:
                assert bad not in kl, f"held-out leak into generator view at {_path}.{k}"
            _assert_no_heldout_leak(v, f"{_path}.{k}")
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            _assert_no_heldout_leak(v, f"{_path}[{i}]")


# --- Writeback (R8) ----------------------------------------------------------

def _writeback(cfg: LoopConfig, rec: RoundRecord, patch_diff: str) -> None:
    """Append one immutable round record to outer-loop-log.jsonl. Records the
    PROPOSED patch diff, verifier verdict, region_iou delta, decision."""
    if cfg.log_path is None:
        return
    cfg.log_path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": time.time(),
        "task": cfg.task,
        "round": rec.round,
        "patch_id": rec.patch_id,
        "patch_diff": patch_diff,
        "surrogate_median": rec.surrogate_median,
        "surrogate_delta": rec.surrogate_delta,
        "surrogate_passed": rec.surrogate_passed,
        "oracle_invoked": rec.oracle_invoked,
        "oracle_pass_bit": rec.oracle_pass_bit,
        "oracle_median": rec.oracle_median,            # log surface — allowed
        "style_ok": rec.style_ok,
        "per_prompt_nonregression_ok": rec.per_prompt_nonregression_ok,
        "decision": rec.decision,
        "image_gen_calls_used": rec.image_gen_calls_used,
        "advisor_consulted": rec.advisor_consulted,
        "note": rec.note,
        "human_gate": "PENDING — adoption is human-approved; loop never auto-merges",
    }
    with cfg.log_path.open("a") as f:
        f.write(json.dumps(entry) + "\n")


# --- The gate ----------------------------------------------------------------

def _final_gate(oracle: OracleResult) -> bool:
    """Final gate (numeric, command-runnable):
      held-out region_iou median >= 0.85
      AND no style_score regression
      AND per-prompt non-regression (no prompt passing >=0.85 drops below 0.85)."""
    return (oracle.pass_bit
            and oracle.median_scalar >= FINAL_IOU_THRESHOLD
            and oracle.style_ok
            and oracle.per_prompt_nonregression_ok)


# --- The loop ----------------------------------------------------------------

def run_loop(cfg: LoopConfig) -> list[RoundRecord]:
    """Run the outer loop shell. Returns the per-round records (also written back).

    Control flow per round:
      1. budget check (image-gen calls).
      2. generator proposes ONE patch from the generator_view (training-only).
      3. surrogate on TRAINING — advance only if median rises.
      4. on surrogate-pass: oracle on FROZEN held-out (counts image-gen calls).
      5. final gate on the oracle's {pass_bit, median, style_ok, nonregression}.
      6. writeback; decide stop.
    Held-out numbers never re-enter the generator (chokepoint: _generator_view)."""
    # Freeze all three sets — no mutation after the loop starts, ever.
    cfg.training.freeze()
    cfg.held_out.freeze()
    cfg.fresh.freeze()

    if len(cfg.held_out) > HELD_OUT_PROMPT_CAP:
        raise BudgetError(
            f"held-out set has {len(cfg.held_out)} prompts > cap {HELD_OUT_PROMPT_CAP} "
            f"(would exceed {MAX_IMAGE_GEN_CALLS} image-gen calls over {cfg.max_iterations} rounds).")

    records: list[RoundRecord] = []
    image_gen_calls = 0
    best_surrogate_median = -1.0
    no_improve_streak = 0
    prev_pass_map: dict[str, bool] = {}   # held-out per-prompt pass map kept INSIDE the gate boundary

    for rnd in range(1, cfg.max_iterations + 1):
        # 1. Budget: each oracle call regenerates the held-out set (≤12 calls).
        if image_gen_calls + len(cfg.held_out) > cfg.max_image_gen_calls:
            records.append(RoundRecord(
                round=rnd, patch_id="(none)", surrogate_median=best_surrogate_median,
                surrogate_delta=0.0, surrogate_passed=False, oracle_invoked=False,
                oracle_pass_bit=None, oracle_median=None, style_ok=None,
                per_prompt_nonregression_ok=None, decision="STOP_BUDGET",
                image_gen_calls_used=image_gen_calls,
                note="image-gen budget would be exceeded by the next oracle call"))
            break

        # 2. Generator proposes ONE patch from the training-only view.
        training_surrogate = cfg.surrogate(cfg.training.prompts, {})  # baseline training signal
        gview = _generator_view(cfg, training_surrogate, records)
        proposal = cfg.generator(gview)
        patch = {"patch": proposal.get("patch", ""), "patch_id": proposal.get("patch_id", f"patch-r{rnd}")}

        # 3. Cheap surrogate on TRAINING with the proposed patch applied.
        surr = cfg.surrogate(cfg.training.prompts, patch)
        surr_median = float(surr.get("median", 0.0))
        surr_delta = surr_median - best_surrogate_median if best_surrogate_median >= 0 else surr_median
        surrogate_passed = surr_median > best_surrogate_median

        rec = RoundRecord(
            round=rnd, patch_id=patch["patch_id"], surrogate_median=surr_median,
            surrogate_delta=surr_delta, surrogate_passed=surrogate_passed,
            oracle_invoked=False, oracle_pass_bit=None, oracle_median=None,
            style_ok=None, per_prompt_nonregression_ok=None, decision="",
            image_gen_calls_used=image_gen_calls)

        if not surrogate_passed:
            # No improvement on the surrogate this round.
            no_improve_streak += 1
            rec.decision = "REJECT_SURROGATE_NO_RISE"
            # On stuck, consult the advisor (feeds GENERATOR next round only).
            if cfg.advisor is not None and no_improve_streak >= 1:
                _maybe_consult_advisor(cfg, rec)
            _writeback(cfg, rec, patch["patch"])
            records.append(rec)
            if no_improve_streak >= NO_IMPROVE_STOP_ROUNDS:
                rec.note = (rec.note + " | ").lstrip(" |") + "STOP: no improvement 2 consecutive rounds"
                break
            continue

        # Surrogate rose — spend the EXPENSIVE oracle tier on the FROZEN held-out set.
        image_gen_calls += len(cfg.held_out)
        oracle = cfg.oracle(cfg.held_out.prompts, patch, dict(prev_pass_map))
        rec.oracle_invoked = True
        rec.oracle_pass_bit = oracle.pass_bit
        rec.oracle_median = oracle.median_scalar         # gate/log/human ONLY
        rec.style_ok = oracle.style_ok
        rec.per_prompt_nonregression_ok = oracle.per_prompt_nonregression_ok
        rec.image_gen_calls_used = image_gen_calls

        # 4/5. Final gate.
        if _final_gate(oracle):
            best_surrogate_median = surr_median
            no_improve_streak = 0
            rec.decision = "PASS_PROPOSE_PATCH"   # PROPOSE only; human adopts (R7)
            # Update the inside-the-gate held-out pass map for next round's non-regression check.
            prev_pass_map = {p: True for p in cfg.held_out.prompts}
            _writeback(cfg, rec, patch["patch"])
            records.append(rec)
            rec.note = "STOP: held-out median >= 0.85 (gate satisfied) — awaiting human adoption"
            break
        else:
            # Surrogate rose but oracle failed → escalation: surrogate was too lax.
            # We DO NOT mutate the frozen held-out/fresh sets. We record that the
            # SURROGATE/TRAINING tests should be tightened before the next round.
            best_surrogate_median = surr_median   # surrogate did rise; record it
            no_improve_streak += 1
            reasons = []
            if not oracle.pass_bit or oracle.median_scalar < FINAL_IOU_THRESHOLD:
                reasons.append("held-out median < 0.85")
            if not oracle.style_ok:
                reasons.append("style_score regression")
            if not oracle.per_prompt_nonregression_ok:
                reasons.append("per-prompt non-regression tripped")
            rec.decision = "REJECT_ORACLE_FAIL"
            rec.note = ("ESCALATE: tighten SURROGATE/TRAINING (raise iou threshold / add harder "
                        "TRAINING panel) — never mutate frozen held-out/fresh. reasons: "
                        + "; ".join(reasons))
            if cfg.advisor is not None:
                _maybe_consult_advisor(cfg, rec)
            _writeback(cfg, rec, patch["patch"])
            records.append(rec)
            if no_improve_streak >= NO_IMPROVE_STOP_ROUNDS:
                rec.note += " | STOP: no improvement 2 consecutive rounds"
                break

    return records


def _maybe_consult_advisor(cfg: LoopConfig, rec: RoundRecord) -> None:
    """Cross-vendor divergent advisor (R11). Feeds the GENERATOR only, never the
    gate. Requires consent for egress (R12b); redaction is enforced in
    model_roster.render_prompt (R12a)."""
    if not (cfg.consent or os.environ.get("MODEL_ROSTER_EGRESS_CONSENT", "").strip().lower()
            in {"1", "true", "yes", "on"}):
        rec.note = (rec.note + " | ").lstrip(" |") + (
            "advisor SKIPPED — cross-vendor egress needs --consent / "
            "MODEL_ROSTER_EGRESS_CONSENT=1 (R12b)")
        return
    # Redacted context only (R12a). The advisor never receives held-out numbers.
    ctx = {"task": cfg.task, "stuck_reason": rec.decision}
    _assert_no_heldout_leak(ctx, "advisor_ctx")
    try:
        cfg.advisor(ctx)  # divergent strategy text — would feed the generator next round
        rec.advisor_consulted = True
    except Exception as e:  # noqa: BLE001 — advisor is best-effort, never gates
        rec.note = (rec.note + " | ").lstrip(" |") + f"advisor error (non-fatal): {e}"


# --- Dry-run stub wiring (no budget spent) -----------------------------------

def _build_dry_run_config(task: str = "space-np01-front-bottom-02",
                          log_path: Optional[Path] = None) -> LoopConfig:
    """A self-contained dry-run config with deterministic stub callables. Spends
    NO budget: the 'oracle' is a pure function, no image-gen, no network."""
    training = FrozenSet("training", [f"train-{i}" for i in range(8)])
    held_out = FrozenSet("held_out", [f"held-{i}" for i in range(6)])
    fresh = FrozenSet("fresh", [f"fresh-{i}" for i in range(4)])

    # Stub generator: proposes a patch id each round; sees only the training view.
    def gen(view: dict) -> dict:
        n = len(view.get("prior_patches", []))
        return {"patch": f"--- skill patch round {n+1} ---", "patch_id": f"patch-r{n+1}"}

    # Stub surrogate: training median climbs a little each round.
    state = {"round": 0}

    def surr(prompts, patch):
        if patch:  # a real proposal evaluation (not the baseline call)
            state["round"] += 1
        base = 0.80 + 0.02 * state["round"]
        return {"per_prompt": {p: base for p in prompts}, "median": base}

    # Stub oracle: held-out median tracks but does NOT reach 0.85 → loop runs out.
    def orc(held, patch, prev_pass):
        return OracleResult(pass_bit=False, median_scalar=0.82,
                            style_ok=True, per_prompt_nonregression_ok=True)

    return LoopConfig(task=task, training=training, held_out=held_out, fresh=fresh,
                      generator=gen, surrogate=surr, oracle=orc, advisor=None,
                      consent=False, dry_run=True, log_path=log_path)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="outer_loop",
                                 description="Outer loop scaffold (verdict-feedback skill refinement).")
    ap.add_argument("--dry-run", action="store_true",
                    help="run the loop shell with deterministic stub callables; spends NO budget.")
    ap.add_argument("--consent", action="store_true",
                    help="authorize cross-vendor egress (advisor/GPT-vision crosscheck). R12b.")
    ap.add_argument("--task", default="space-np01-front-bottom-02")
    ap.add_argument("--log", default="", help="path to outer-loop-log.jsonl (writeback target)")
    args = ap.parse_args(argv)

    if not args.dry_run:
        print("refusing to run for real: real image-gen + result-vision-judge are gated. "
              "Use --dry-run for the scaffold, or wire real callables and run round 1 MANUALLY "
              "(human adopts/rejects the patch).", file=sys.stderr)
        return 2

    log_path = Path(args.log) if args.log else None
    cfg = _build_dry_run_config(task=args.task, log_path=log_path)
    cfg.consent = args.consent
    records = run_loop(cfg)
    print(f"outer-loop dry-run: {len(records)} round(s)")
    for r in records:
        print(f"  round {r.round}: surrogate_median={r.surrogate_median:.3f} "
              f"oracle_invoked={r.oracle_invoked} decision={r.decision}")
        if r.note:
            print(f"      note: {r.note}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
