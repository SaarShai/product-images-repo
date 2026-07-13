# Defect Detector Battery Calibration

Command shape used for the sweep:

```bash
PYTHONPYCACHEPREFIX=/tmp/pycache-gate-battery python3 scripts/gates/gate_battery.py --rgba <png> --out-dir tasks/transparent-bg-endgame/calibration-runs/<label>
```

Evidence JSON and failed-gate crops are under `tasks/transparent-bg-endgame/calibration-runs/`.

## Blocking Thresholds

| Gate | Active threshold | Calibration result |
|---|---:|---|
| D1 halo | edge-band L* p99 <= 16.0 and mean <= 3.5 | Calibrated. Known-bad API halos measured p99 35.8256-38.6544; keyed-v3 chroma candidates measured p99 8.4261-9.0956. |
| D2 soft alpha | soft profile ratio <= 2.75, p95 width <= 4.0; print profile soft px == 0 | Calibrated for soft route. Known-bad API halos measured ratio 11.7486-12.7212; keyed-v3 chroma candidates measured 1.1299-1.4332. |
| D3 pockets | enclosed alpha-zero component count <= 4 | Calibrated as a defect tripwire, not a topology judge. The synthetic five-pocket fixture fails; the synthetic one-hole good fixture passes. API-bad files have 57-84 enclosed components and fail. Coral keyed candidates have 224-276 legitimate/ambiguous negative-space holes, so D3 crops still need human interpretation on dense coral art. |
| D4 aura | `scripts/aura_gate.py` default aura_index <= 0.20 | Reused existing calibrated logic. API-bad files measured 0.3561-0.5186; keyed-v3 chroma candidates measured 0.0322-0.0422. |
| D7 border | 3px border alpha occupancy == 0 | Deterministic policy gate. API-bad files with cropped/edge-touching art fail; keyed-v3 candidates also fail here, so they are not clean border-good examples. |
| D8 alpha sanity | reject flat alpha and checker ratio > 0.25 | Synthetic degenerate-alpha fixture fails; clean binary-alpha pytest fixture passes. |

## Sweep Table

| Label | Expected role | D1 p99 | D2 ratio | D3 count | D4 aura | D7 occ | Failed gates |
|---|---|---:|---:|---:|---:|---:|---|
| bad_api_seed1 | known bad halo/aura | 38.5462 | 12.7212 | 84 | 0.3666 | 0.00019577 | D1, D2, D3, D4, D7 |
| bad_api_seed2 | known bad halo/aura | 38.6544 | 12.5935 | 77 | 0.3561 | 0.00013051 | D1, D2, D3, D4, D7 |
| bad_api_gpt15_seed1 | known bad halo/aura | 38.2267 | 11.7486 | 57 | 0.5186 | 0.11687549 | D1, D2, D3, D4, D7 |
| bad_api_gpt15_seed2 | known bad halo/aura | 35.8256 | 12.3235 | 72 | 0.4531 | 0.12216132 | D1, D2, D3, D4, D7 |
| good_keyed_green_p1 | good for D1/D2/D4 only | 8.6862 | 1.4332 | 276 | 0.0322 | 0.04515792 | D3, D7 |
| good_keyed_green_p2 | good for D1/D2/D4 only | 9.0956 | 1.1802 | 244 | 0.0422 | 0.12163926 | D3, D7 |
| good_keyed_green_p3 | good for D1/D2/D4 only | 8.4261 | 1.1299 | 224 | 0.0403 | 0.13397285 | D3, D7 |
| synthetic_good_fixture | synthetic good pocket baseline | 0.0 | 1.9282 | 1 | 0.9091 | 0.0 | D4 |
| synthetic_negative_degenerate_alpha | synthetic bad alpha | 0.0 | 0.0 | 0 | 0.068 | 1.0 | D7, D8 |

## Advisory Gates

D5 `hole_gate` and D6 `spill_gate` are implemented but remain `advisory=true` in `CALIBRATION`.

Paired runs against `raw_green_P1/P2/P3` plus `keyed_green_P1/P2/P3` showed that the available paired data is not clean calibration ground truth for blocking thresholds:

| Label | D5 deleted frac | D5 max blob | D6 OKLab delta | D6 bg projection | D5/D6 verdict |
|---|---:|---:|---:|---:|---|
| paired_green_P1 | 0.083260 | 592 | 0.048096 | 0.044673 | fail/fail |
| paired_green_P2 | 0.668486 | 935286 | 0.049694 | 0.045357 | fail/fail |
| paired_green_P3 | 0.017242 | 42 | 0.052613 | 0.047001 | fail/fail |

Those results are useful warnings, but not enough to promote D5/D6 to blocking because source/delivered art mismatch and known green-tint review findings confound the calibration set.

## v2 Detector Battery Notes

Implemented in `scripts/gates/gate_battery.py` v2 from `advisor-sol-ultra.md` section 4.

- Overall verdict is now tri-state: `PASS`, `FAIL`, or `REVIEW`. CLI exits are `0` for all pass, `2` for any hard fail, and `3` for review-only failures.
- D1 halo is donor-referenced: it builds a component-constrained inward donor field from the 0.15-0.35 mm band, composites observed and donor colors in linear light over black, `#111111`, dark navy, magenta, and any user-supplied panels, then reports `H_L`, `H_area`, and optional matte-pull `H_key`.
- Missing `--ppi` / `--px-per-mm` keeps px fallback metrics with an advisory flag. D1 does not hard-evaluate mm area without physical scale; `H_area_px` remains reported.
- D2 reports transition width, trusted-contour displacement when `--truth` is supplied, and perimeter-excess ratio against a 0.15 mm smoothed contour.
- D4 reports shell geometry around the material core: boundary wrap fraction plus median/p95 shell width. The legacy `aura_gate.py` result is preserved as a secondary signal.
- D5 adds `--truth <rgba>` recall mode by component and thickness/pale strata. Source/background heuristic mode remains REVIEW-only evidence.
- D6 is donor-relative OKLab key-direction excess in the transition band and remains REVIEW-only pending clean-edge calibration.

Regression evidence:

```bash
PYTHONPYCACHEPREFIX=/tmp/pyc python3 -m pytest -q tests/test_gate_battery.py
# 6 passed

MPLCONFIGDIR=/tmp/mpl PYTHONPYCACHEPREFIX=/tmp/pyc python3 scripts/gates/gate_battery.py \
  --rgba REVIEW/marine-bed-transparent/chroma-lane/final-candidate/marine_green_P1_keyed_x4.png \
  --profile soft --out-dir /tmp/gate-battery-marine-v2
# overall FAIL from non-D1 gates; D1_halo_gate PASS, H_L=0.0, H_area_px=13293
```

## v3 Detector Battery Notes

Implemented in `scripts/gates/gate_battery.py` v3 after the approved marine-bed calibration failure.

- D3 is split into two sub-checks. `D3a_alpha_pockets` reports enclosed `alpha==0` topology pockets as advisory-only evidence with a minimum area filter of `max(9px, 0.02mm^2)` when scale is known and a count-per-megapixel metric. It never emits `FAIL`; above the high seed threshold it emits `REVIEW`.
- `D3b_retained_background` is the blocking trapped-background detector. It requires `--bg-color`, finds enclosed foreground pixels with `alpha>0.5` and `deltaE00(fg,bg)<tau_B`, and reports count, max area, total area, and crops. Without `--bg-color`, it is skipped with an advisory note and does not block.
- D7 now accepts `--border-policy {forbid,allow,auto}` with default `auto`. `auto` emits `REVIEW` for nonzero border occupancy because full-bleed wrapper art can legitimately touch the canvas edge. `forbid` preserves the previous hard-fail behavior for isolated-subject generations.

Regression evidence:

```bash
MPLCONFIGDIR=/tmp/mpl PYTHONPYCACHEPREFIX=/tmp/pyc python3 scripts/gates/gate_battery.py \
  --rgba REVIEW/marine-bed-transparent/chroma-lane/final-candidate/marine_green_P1_keyed_x4.png \
  --profile soft --out-dir /tmp/gate-battery-marine-v3
# verdict REVIEW, exit_code 3
# D3a_alpha_pockets PASS: component_count=3143, component_count_per_mpx=124.8916
# D3b_retained_background PASS/skipped: --bg-color not provided
# D7_border_gate REVIEW: border_policy=auto, border_alpha_occupancy=0.04810762
```
