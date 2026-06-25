#!/usr/bin/env python3
"""Self-test for outer_loop.py — drives the loop with stub generator+oracle and
asserts the spec gates. Spends NO budget. Run: python3 scripts/test_outer_loop.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import outer_loop as ol  # noqa: E402


def _sets():
    tr = ol.FrozenSet("training", [f"t{i}" for i in range(8)])
    ho = ol.FrozenSet("held_out", [f"h{i}" for i in range(6)])
    fr = ol.FrozenSet("fresh", [f"f{i}" for i in range(4)])
    return tr, ho, fr


def test_oracle_never_leaks_heldout_to_generator():
    """The generator_view must carry NO held-out number, ever. We capture every
    view the generator receives and assert the barrier."""
    captured = []

    def gen(view):
        captured.append(view)
        # The barrier asserter would have raised already; double-check here too.
        ol._assert_no_heldout_leak(view, "captured_view")
        n = len(view.get("prior_patches", []))
        return {"patch": f"p{n}", "patch_id": f"patch-r{n+1}"}

    rounds = {"n": 0}

    def surr(prompts, patch):
        if patch:
            rounds["n"] += 1
        m = 0.80 + 0.02 * rounds["n"]
        return {"per_prompt": {p: m for p in prompts}, "median": m}

    # Oracle reaches the gate on round 1 (median high) so prior_patches gets a PASS.
    def orc(held, patch, prev):
        return ol.OracleResult(pass_bit=True, median_scalar=0.90,
                               style_ok=True, per_prompt_nonregression_ok=True)

    tr, ho, fr = _sets()
    cfg = ol.LoopConfig(task="t", training=tr, held_out=ho, fresh=fr,
                        generator=gen, surrogate=surr, oracle=orc)
    ol.run_loop(cfg)
    assert captured, "generator was never called"
    # No view may contain the oracle median 0.90 anywhere.
    for v in captured:
        flat = repr(v)
        assert "0.9" not in flat, f"oracle median leaked into generator view: {flat}"
        assert "oracle" not in flat.lower(), f"oracle key leaked: {flat}"
    print("PASS: oracle never passes any held-out number to the generator")


def test_nonregression_gate_trips_on_planted_regression():
    """Plant a per-prompt non-regression failure: oracle median is high and style
    is fine, but a previously-passing prompt dropped <0.85 → gate must NOT pass."""
    def gen(view):
        n = len(view.get("prior_patches", []))
        return {"patch": "p", "patch_id": f"patch-r{n+1}"}

    rounds = {"n": 0}

    def surr(prompts, patch):
        if patch:
            rounds["n"] += 1
        m = 0.80 + 0.03 * rounds["n"]
        return {"per_prompt": {p: m for p in prompts}, "median": m}

    def orc(held, patch, prev):
        # median high, style fine, but non-regression FAILS (the tail regressed)
        return ol.OracleResult(pass_bit=True, median_scalar=0.92,
                               style_ok=True, per_prompt_nonregression_ok=False)

    tr, ho, fr = _sets()
    cfg = ol.LoopConfig(task="t", training=tr, held_out=ho, fresh=fr,
                        generator=gen, surrogate=surr, oracle=orc)
    recs = ol.run_loop(cfg)
    passed = [r for r in recs if r.decision == "PASS_PROPOSE_PATCH"]
    assert not passed, "planted per-prompt regression must block the final gate"
    assert any(r.decision == "REJECT_ORACLE_FAIL" for r in recs), \
        "should record an oracle reject for the regression"
    assert any("per-prompt non-regression" in (r.note or "") for r in recs), \
        "should name the non-regression reason"
    # Direct unit check of the gate predicate too.
    bad = ol.OracleResult(pass_bit=True, median_scalar=0.92, style_ok=True,
                          per_prompt_nonregression_ok=False)
    assert ol._final_gate(bad) is False
    bad_style = ol.OracleResult(pass_bit=True, median_scalar=0.92, style_ok=False,
                                per_prompt_nonregression_ok=True)
    assert ol._final_gate(bad_style) is False, "style regression must block the gate"
    print("PASS: non-regression gate trips on a planted regression (and style co-gate)")


def test_stop_on_two_no_improve_rounds():
    """Round 1 establishes a baseline (surrogate rises from cold start), then the
    surrogate goes FLAT → no rise → stop after 2 consecutive no-improve rounds.
    The oracle never passes the final gate (median < 0.85) so the loop relies on
    the no-improve stop, not the success stop."""
    def gen(view):
        n = len(view.get("prior_patches", []))
        return {"patch": "p", "patch_id": f"patch-r{n+1}"}

    rounds = {"n": 0}

    def surr(prompts, patch):
        if patch:
            rounds["n"] += 1
        # Round 1 → 0.80 (rises from -1 baseline); rounds 2+ stay flat at 0.80.
        return {"per_prompt": {p: 0.80 for p in prompts}, "median": 0.80}

    def orc(held, patch, prev):
        # Never reaches the gate, so round 1's surrogate rise still doesn't end the loop.
        return ol.OracleResult(pass_bit=False, median_scalar=0.70,
                               style_ok=True, per_prompt_nonregression_ok=True)

    tr, ho, fr = _sets()
    cfg = ol.LoopConfig(task="t", training=tr, held_out=ho, fresh=fr,
                        generator=gen, surrogate=surr, oracle=orc)
    recs = ol.run_loop(cfg)
    # Round 1 rises (oracle fail, no_improve=1), round 2 flat (no_improve=2) → stop.
    assert "no improvement 2 consecutive rounds" in (recs[-1].note or ""), \
        f"expected no-improve stop, got: {[r.decision for r in recs]} / {recs[-1].note!r}"
    assert any(r.decision == "REJECT_SURROGATE_NO_RISE" for r in recs), \
        "a flat surrogate round must be recorded as no-rise"
    assert len(recs) < ol.MAX_ITERATIONS, "must stop before max_iterations"
    print("PASS: stop triggers on 2 consecutive no-improve rounds")


def test_budget_cap_enforced():
    """With a held-out set sized so two oracle calls would exceed the cap, the loop
    must stop on budget rather than spend over the cap."""
    def gen(view):
        n = len(view.get("prior_patches", []))
        return {"patch": "p", "patch_id": f"patch-r{n+1}"}

    rounds = {"n": 0}

    def surr(prompts, patch):
        if patch:
            rounds["n"] += 1
        # Always rises so the oracle is invoked each round.
        return {"per_prompt": {p: 0.80 + 0.02 * rounds["n"] for p in prompts},
                "median": 0.80 + 0.02 * rounds["n"]}

    calls = {"oracle": 0}

    def orc(held, patch, prev):
        calls["oracle"] += 1
        return ol.OracleResult(pass_bit=False, median_scalar=0.82,
                               style_ok=True, per_prompt_nonregression_ok=True)

    tr = ol.FrozenSet("training", [f"t{i}" for i in range(4)])
    ho = ol.FrozenSet("held_out", [f"h{i}" for i in range(10)])  # 10 calls/round
    fr = ol.FrozenSet("fresh", [f"f{i}" for i in range(2)])
    cfg = ol.LoopConfig(task="t", training=tr, held_out=ho, fresh=fr,
                        generator=gen, surrogate=surr, oracle=orc,
                        max_image_gen_calls=15)  # 10 ok, 20 over → 2nd round stops
    recs = ol.run_loop(cfg)
    total = max((r.image_gen_calls_used for r in recs), default=0)
    assert total <= 15, f"image-gen calls {total} exceeded cap 15"
    assert any(r.decision == "STOP_BUDGET" for r in recs), "budget stop must fire"
    assert calls["oracle"] == 1, f"oracle should run once before the cap, ran {calls['oracle']}"
    print("PASS: budget cap enforced (stopped before exceeding image-gen cap)")


def test_held_out_cap_rejected():
    """A held-out set larger than 12 prompts must be refused (would blow 60-call cap)."""
    tr, _, fr = _sets()
    big = ol.FrozenSet("held_out", [f"h{i}" for i in range(13)])
    cfg = ol.LoopConfig(task="t", training=tr, held_out=big, fresh=fr,
                        generator=lambda v: {"patch": "p", "patch_id": "x"},
                        surrogate=lambda p, q: {"per_prompt": {}, "median": 0.0},
                        oracle=lambda h, p, pp: ol.OracleResult(True, 0.9, True, True))
    try:
        ol.run_loop(cfg)
    except ol.BudgetError:
        print("PASS: held-out set > 12 prompts rejected (60-call cap protection)")
        return
    raise AssertionError("held-out > 12 should raise BudgetError")


def test_frozen_set_immutable():
    s = ol.FrozenSet("held_out", ["a", "b"])
    s.freeze()
    try:
        s.mutate("c")
    except RuntimeError:
        print("PASS: frozen set refuses mutation (test-set contamination blocked)")
        return
    raise AssertionError("frozen set mutate() must raise")


def test_advisor_needs_consent():
    """Advisor (cross-vendor egress) must be skipped without consent (R12b)."""
    advisor_called = {"n": 0}

    def adv(ctx):
        advisor_called["n"] += 1
        ol._assert_no_heldout_leak(ctx, "advisor_ctx")
        return "try a different geometry-contract"

    def gen(view):
        return {"patch": "p", "patch_id": "x"}

    def surr(prompts, patch):
        return {"per_prompt": {p: 0.80 for p in prompts}, "median": 0.80}  # flat → stuck

    def orc(held, patch, prev):
        return ol.OracleResult(False, 0.5, True, True)

    tr, ho, fr = _sets()
    # No consent → advisor skipped.
    cfg = ol.LoopConfig(task="t", training=tr, held_out=ho, fresh=fr,
                        generator=gen, surrogate=surr, oracle=orc, advisor=adv,
                        consent=False)
    recs = ol.run_loop(cfg)
    assert advisor_called["n"] == 0, "advisor must NOT egress without consent"
    assert any("advisor SKIPPED" in (r.note or "") for r in recs)
    # With consent → advisor consulted (feeds generator only; never gates).
    advisor_called["n"] = 0
    tr2, ho2, fr2 = _sets()
    cfg2 = ol.LoopConfig(task="t", training=tr2, held_out=ho2, fresh=fr2,
                         generator=gen, surrogate=surr, oracle=orc, advisor=adv,
                         consent=True)
    recs2 = ol.run_loop(cfg2)
    assert advisor_called["n"] >= 1, "advisor should be consulted under consent"
    assert any(r.advisor_consulted for r in recs2)
    print("PASS: advisor egress gated on consent (R12b); fed generator, never the gate")


if __name__ == "__main__":
    tests = [
        test_oracle_never_leaks_heldout_to_generator,
        test_nonregression_gate_trips_on_planted_regression,
        test_stop_on_two_no_improve_rounds,
        test_budget_cap_enforced,
        test_held_out_cap_rejected,
        test_frozen_set_immutable,
        test_advisor_needs_consent,
    ]
    failed = 0
    for t in tests:
        try:
            t()
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"FAIL: {t.__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
