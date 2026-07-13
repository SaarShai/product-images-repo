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
