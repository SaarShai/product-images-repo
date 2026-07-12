# Green-key shoot-out — VERDICT

Source raw: `REVIEW/marine-bed-transparent/chroma-lane/raws/raw_green_P1.png`  
ΔE implementation: `skimage.color.deltaE_cie76`

## Ranked table (fewest gate failures first)

| Candidate | residual-green | deleted-art | rim | despill-confine | recomposition | bubbles | border-occ | # FAILS |
|---|---|---|---|---|---|---|---|---|
| A_keyed-v3 | PASS | PASS | FAIL | PASS | PASS | FAIL | FAIL | 3 |
| C_vitmatte | PASS | FAIL | FAIL | PASS | PASS | FAIL | PASS | 3 |
| D1_bria-rmbg | FAIL | FAIL | FAIL | PASS | PASS | PASS | PASS | 3 |
| E_ffmpeg-chroma | FAIL | PASS | FAIL | PASS | PASS | FAIL | PASS | 3 |
| B_classic | PASS | FAIL | FAIL | PASS | FAIL | FAIL | PASS | 4 |
| D2_birefnet | FAIL | FAIL | FAIL | PASS | PASS | FAIL | PASS | 4 |

## Per-candidate defect summary

- **A_keyed-v3**: rim halo Δgreenness 41.6; bubble greenish tint detected; border occupancy 2.35%
- **C_vitmatte**: deleted art 2.855% of art (max blob 25px); rim halo Δgreenness 18.3; bubble greenish tint detected
- **D1_bria-rmbg**: residual green 162px (max blob 37px); deleted art 18.742% of art (max blob 46500px); rim halo Δgreenness 53.3
- **E_ffmpeg-chroma**: residual green 1804px (max blob 7px); rim halo Δgreenness 172.3; bubble greenish tint detected
- **B_classic**: deleted art 1.927% of art (max blob 26px); rim halo Δgreenness 51.1; bg alpha leak 2.57%; bubble greenish tint detected
- **D2_birefnet**: residual green 105px (max blob 37px); deleted art 16.854% of art (max blob 26315px); rim halo Δgreenness 57.0; bubble greenish tint detected
