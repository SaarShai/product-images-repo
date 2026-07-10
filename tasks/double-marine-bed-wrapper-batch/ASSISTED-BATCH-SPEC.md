# Assisted background-removal batch spec

`run_assisted_batch.py` accepts only an explicit `assisted-bg-batch-spec/v1` JSON file. It does not discover images, infer pairings, or promote outputs.

```json
{
  "schema": "assisted-bg-batch-spec/v1",
  "cases": [
    {
      "id": "image14",
      "source": {
        "path": "/absolute/path/image14.png",
        "sha256": "0000000000000000000000000000000000000000000000000000000000000000",
        "size_wh": [941, 1672]
      },
      "legacy_rgba_proposal": {
        "path": "/absolute/path/image14-legacy-x4.png",
        "resample": "lanczos"
      },
      "corrections": {"path": "/absolute/path/image14-corrections.png"},
      "output_dir": "/absolute/path/Images/candidates/assisted/image14"
    }
  ]
}
```

Replace the all-zero digest with the source file's actual SHA-256.

Use `proposal: {"path": "..."}` for an exact native-size mask/alpha image. Use `legacy_rgba_proposal` only for a larger proportional RGBA image; its alpha is explicitly downsampled to a native-size `L` PNG. Corrections, when present, must be genuine native-size RGBA.

```bash
python3 tasks/double-marine-bed-wrapper-batch/run_assisted_batch.py \
  --spec /absolute/path/batch.json \
  --aggregate /absolute/path/batch-report.json \
  --backend vitmatte \
  --device mps \
  --correction-unlock-radius 110 \
  --dry-run
```

Remove `--dry-run` to execute. Repeat `--case CASE_ID` for an exact ordered subset. A completed case resumes only when its input, normalized-proposal, core, runner, configuration, and output hashes still match. Any mismatch requires explicit `--overwrite`. Every output remains `candidate-unapproved`; paths containing `final` or `finals` are rejected.
