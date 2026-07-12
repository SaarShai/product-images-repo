# Correction overlay metrics

Fresh command:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -B tasks/double-marine-bed-wrapper-batch/scouts/hard-case-corrections/validate_corrections.py
```

| Case | Dimensions | Mode | Red | Blue | Alpha-zero unknown | Partial alpha | Label fraction | Red on candidate alpha < 64 | Source hash unchanged | Structural verdict |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| image15 | 1536 x 1024 | RGBA | 5,752 | 0 | 1,567,112 | 0 | 0.3657% | 86.68% | yes | PASS |
| sample08 | 1634 x 962 | RGBA | 135 | 0 | 1,571,773 | 0 | 0.0086% | 72.59% | yes | PASS |

Allowed opaque label colors are exactly `(255, 0, 0, 255)` and `(0, 0, 255, 255)`. Every other pixel is exactly `(0, 0, 0, 0)`. A built-in negative fixture using `(1, 2, 3, 255)` trips `invalid_label_colors` as expected.

Overlay SHA-256:

- image15: `3844233597003b0d485ffd08add4815f307fdd1d7a2d4020f22459a6f68eddfa`
- sample08: `e27517fc64d33dc8ec4e7e0bafe0901f12eef725e38ccf292dc53a3fe8b9acd0`

Source SHA-256 rechecked unchanged:

- image15: `bf6f2deb7bce6e2b76a644d0caa7e3ae6519837c4d0842d47c548bc4fb650e72`
- sample08: `8b0111dab8fb19887a83b8aaf8c6140e89d1b3e93b8b61265ab94e6ac3416af2`
