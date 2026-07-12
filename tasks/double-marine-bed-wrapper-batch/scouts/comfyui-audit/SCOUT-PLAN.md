# One bounded image14 scout: SAM 3.1 point topology → ViTMatte

**Spec version:** `1.1-exec` (2026-07-10)

**Supersedes:** independently held pre-execution v1.0, SHA-256 `65115cd1679447e2a43f00cce9da486dc9b5bc7a8277ebbc9cd2dc11e0be96a0`

**Status:** the authorized transport retry failed and was cleaned up; the graph was never executed.

**Goal:** test one genuinely different topology producer without installing a broad Comfy node pack or repeating an automatic remover.

**Output class:** candidate evidence only, never a product final.

## Why this route

The existing ViTMatte-S scout proved that soft matting works on MPS but inherits any wrong sure-foreground/sure-background topology. Native Comfy SAM 3.1 can use positive and negative pixel prompts through its point decoder. The scout therefore changes only the failed upstream primitive and reuses the already-working matting, foreground-color recovery, review-board, and benchmark code.

A concurrent paid text-prompted SAM3 scout returned one coarse binary mask that filled enclosed paper and dropped bubbles, fish, and tips. This plan does **not** repeat that route. It omits text conditioning entirely. In core source, text and point masks are unioned; feeding the failed coarse text silhouette alongside negative-point output could refill the very interior holes the negative points are meant to exclude.

This is different from prior CLI attempts:

- prior BRIA/BiRefNet/InSPyReNet/Photoshop proposals were class-agnostic automatic foreground estimates;
- this proposal uses the native point decoder and is explicitly supervised at known painted-sand and interior-paper locations;
- prior ViTMatte used a rejected automatic alpha as its trimap seed;
- this ViTMatte pass uses the SAM 3.1 point-supervised mask plus sparse sure-foreground corrections.

## Hard boundary

Execution authorization was received on 2026-07-10. This authorization permits exactly one official checkpoint download and one candidate through the fixed pipeline. Execution must not install a custom node pack, change Comfy source/venv, call a paid service, write to `Images/finals/`, weaken the frozen benchmark, or run a second candidate after failure.

### v1.1 execution amendment

- The output root is now the user-directed `Images/candidates/comfyui-sam31-image14/`.
- `--correction-unlock-radius` changes from `6` to `110`; no other matting threshold, SAM point, graph node, checkpoint, device, verifier, or budget changes.
- Evidence for `110`: the fresh real assisted candidate at `Images/candidates/bg-assisted-v1/image14/assisted-r110-vitmatte/metrics.json` records `correction_unlock_radius_px: 110`, recovered the frozen `fg-sand-watercolor-wash` guard at fraction `1.0` and median alpha `168`, and passed all 26 frozen sure-foreground/exterior-background/enclosed-background guards. That earlier candidate still failed two separate white-edge probes, so it is evidence for correction transport radius only, not a claimed complete pass; this SAM scout retains the unchanged frozen edge gates.

```loop
name: image14-comfy-sam31-vitmatte-scout
topology: closed inner single
generator: comfy_core_sam31_point_only_plus_repo_assisted_vitmatte
verifier: frozen_bg_benchmark_separate_reviewer
gate: python3 tasks/double-marine-bed-wrapper-batch/bg-benchmark/verify_bg_solution.py --manifest tasks/double-marine-bed-wrapper-batch/bg-benchmark/manifest.json --candidate image14=$OUT/image14-sam31-vitmatte-straight-rgba.png --json-report $OUT/benchmark-report.json --review-dir $OUT/benchmark-review
stop: done after exactly one candidate receives one frozen machine verdict and one independent native white/gray/black/magenta review request; blocked on download, license, server, MPS, dimension, or execution failure; failed candidates are recorded and never retried in this scout
budget: max_iterations=1
```

## Inputs and output root

```bash
set -euo pipefail
export SOURCE='/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/double Marine Bed Wrapper/images/ChatGPT Image Jul 7, 2026, 11_22_35 AM.png'
export CORRECTIONS='/Users/za/Documents/product images repo/tasks/double-marine-bed-wrapper-batch/scouts/image14-labels/image14-correction-labels-rgba.png'
export OUT='/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/double Marine Bed Wrapper/images/Images/candidates/comfyui-sam31-image14'
```

Frozen identity before any run:

- source dimensions: 941×1672 RGB;
- source SHA-256: `925c34a39a0e2b5a09ad92ba39dace87f652bcc90ff8e063e2a6f644e735df9d`;
- corrections dimensions: 941×1672 RGBA;
- corrections SHA-256: `18d695a2cada3a2e1fb9a7c72f2ec04ed90a9e89d6dfc1d8d96a73bd47ab6a61`;
- corrections contain five red sure-foreground strokes, zero blue sure-background strokes, and were created without benchmark access.

## One required download

| Artifact | Exact destination | Bytes/hash evidence | License |
|---|---|---|---|
| `sam3.1_multiplex_fp16.safetensors` | `/Users/za/ComfyUI/models/checkpoints/sam3.1_multiplex_fp16.safetensors` | 1,745,546,848 bytes; downloadable file SHA-256 `9ba99c92703c2e8b4f47de2d34a539bb8e18923049e238b780d70dbe6368eb03`; distinct Xet storage hash `f28913d2d02668c8bef2025d1d213008200379b72f483f98301be6ce6c77df60` | [SAM License](https://github.com/facebookresearch/sam3/blob/main/LICENSE); user must accept before download |

Official source: `https://huggingface.co/Comfy-Org/sam3.1/resolve/main/checkpoints/sam3.1_multiplex_fp16.safetensors`.
[Hugging Face file metadata](https://huggingface.co/Comfy-Org/sam3.1/blob/main/checkpoints/sam3.1_multiplex_fp16.safetensors) reports the downloadable SHA-256 separately from the Xet hash.

No other download is allowed. The cached ViTMatte-S model at revision `6a58ad7646403c1df626fbd746900aec7361ea1d` is already present and verified; `.venv-gen` already has its required runtime.

After a separately authorized download, block the run unless both frozen checks pass:

```bash
SAM31='/Users/za/ComfyUI/models/checkpoints/sam3.1_multiplex_fp16.safetensors'
test "$(stat -f '%z' "$SAM31")" = '1745546848'
test "$(shasum -a 256 "$SAM31" | awk '{print $1}')" = \
  '9ba99c92703c2e8b4f47de2d34a539bb8e18923049e238b780d70dbe6368eb03'
```

## Smallest Comfy graph: five core nodes

Use core only; launch with `--disable-all-custom-nodes --disable-api-nodes`. Do not use the official blueprint's text-conditioning branch for this scout.

| Order | Node ID | Fixed inputs | Output use |
|---|---|---|---|
| 1 | `LoadImage` | source filename from an input directory pointed at the product `images/` folder | native image |
| 2 | `CheckpointLoaderSimple` | `sam3.1_multiplex_fp16.safetensors` | `MODEL`; ignore CLIP/VAE outputs |
| 3 | `SAM3_Detect` | image + model + fixed positive/negative JSON; leave `conditioning` and `bboxes` disconnected; `threshold=0.5` (unused on the point path), `refine_iterations=2`, `individual_masks=false` | one point-supervised foreground mask |
| 4 | `MaskToImage` | raw SAM foreground mask; do **not** invert, grow, feather, blur, or threshold | white-foreground proposal image |
| 5 | `SaveImage` | prefix `image14-sam31-point-proposal` | proposal PNG fetched to `$OUT` |

Positive point JSON, in native `(x,y)` coordinates:

```json
[{"x":82,"y":1514},{"x":549,"y":1523},{"x":654,"y":1557},{"x":294,"y":1595},{"x":854,"y":1536},{"x":480,"y":1200},{"x":475,"y":600},{"x":263,"y":683},{"x":635,"y":833},{"x":775,"y":983},{"x":450,"y":1000},{"x":500,"y":1100},{"x":212,"y":178},{"x":660,"y":210},{"x":180,"y":400}]
```

The first five are centers of the independently created missing-sand correction strokes. The remainder are center pixels on visibly painted coral, seaweed, fish, or shells. Fresh native-pixel checks found chroma of 25–97 at every non-label positive center; none is a paper-white center.

Negative point JSON, in native `(x,y)` coordinates:

```json
[{"x":20,"y":20},{"x":920,"y":20},{"x":20,"y":1650},{"x":920,"y":1650},{"x":425,"y":400},{"x":325,"y":500},{"x":500,"y":550},{"x":600,"y":600},{"x":600,"y":1000},{"x":286,"y":1001}]
```

The first four are exterior paper. The remaining six are paper windows inside the broad coral/reef footprint, not frozen benchmark labels. Every negative has a native 9×9 neighborhood minimum of at least 251/255. The generator must not read `bg-benchmark/annotations/image14.json`.

Point-class validation is a blocking preflight, not a tunable gate:

- the first five positives must be exact opaque red at the same coordinates in `CORRECTIONS`;
- every other positive center must have native RGB chroma `max(R,G,B)-min(R,G,B) >= 25`;
- every negative 9×9 source neighborhood must have all channels `>=250`;
- coordinates in the two classes must be disjoint and inside 941×1672.

If any assertion changes or fails, stop `BLOCKED`; do not replace a point during the one-shot run.

`threshold` does not affect core's point-prompt branch; the source thresholds its point mask at logit zero. No mask polish is allowed in Comfy: ViTMatte needs the unhidden topology error and will create the soft boundary from a conservative trimap.

## Exact API workflow artifact

Before the server starts, materialize the following exact JSON as `$OUT/workflow-api.json` and run `jq empty "$OUT/workflow-api.json"`. This is the file passed to `scripts/comfy_run.py`; no workflow builder currently supports SAM3.

<!-- workflow-api:start -->
```json
{
  "1": {
    "class_type": "LoadImage",
    "inputs": {
      "image": "ChatGPT Image Jul 7, 2026, 11_22_35 AM.png"
    }
  },
  "2": {
    "class_type": "CheckpointLoaderSimple",
    "inputs": {
      "ckpt_name": "sam3.1_multiplex_fp16.safetensors"
    }
  },
  "3": {
    "class_type": "SAM3_Detect",
    "inputs": {
      "model": ["2", 0],
      "image": ["1", 0],
      "positive_coords": "[{\"x\":82,\"y\":1514},{\"x\":549,\"y\":1523},{\"x\":654,\"y\":1557},{\"x\":294,\"y\":1595},{\"x\":854,\"y\":1536},{\"x\":480,\"y\":1200},{\"x\":475,\"y\":600},{\"x\":263,\"y\":683},{\"x\":635,\"y\":833},{\"x\":775,\"y\":983},{\"x\":450,\"y\":1000},{\"x\":500,\"y\":1100},{\"x\":212,\"y\":178},{\"x\":660,\"y\":210},{\"x\":180,\"y\":400}]",
      "negative_coords": "[{\"x\":20,\"y\":20},{\"x\":920,\"y\":20},{\"x\":20,\"y\":1650},{\"x\":920,\"y\":1650},{\"x\":425,\"y\":400},{\"x\":325,\"y\":500},{\"x\":500,\"y\":550},{\"x\":600,\"y\":600},{\"x\":600,\"y\":1000},{\"x\":286,\"y\":1001}]",
      "threshold": 0.5,
      "refine_iterations": 2,
      "individual_masks": false
    }
  },
  "4": {
    "class_type": "MaskToImage",
    "inputs": {
      "mask": ["3", 0]
    }
  },
  "5": {
    "class_type": "SaveImage",
    "inputs": {
      "images": ["4", 0],
      "filename_prefix": "image14-sam31-point-proposal"
    }
  }
}
```
<!-- workflow-api:end -->

Create the output root and extract the frozen block above into the exact runner input; this avoids a manual JSON transcription:

```bash
export PLAN='/Users/za/Documents/product images repo/tasks/double-marine-bed-wrapper-batch/scouts/comfyui-audit/SCOUT-PLAN.md'
if test -e "$OUT"; then
  echo 'BLOCKED: scout output root already exists; do not overwrite or retry'
  exit 1
fi
mkdir -p \
  "$OUT/comfy-output" \
  "$OUT/comfy-temp" \
  "$OUT/comfy-user" \
  "$OUT/runtime-cache/xdg" \
  "$OUT/runtime-cache/hf" \
  "$OUT/runtime-cache/torch" \
  "$OUT/runtime-cache/mpl"
PLAN="$PLAN" OUT="$OUT" \
/Users/za/Documents/product\ images\ repo/.venv-gen/bin/python - <<'PY'
import os
import re
from pathlib import Path

text = Path(os.environ["PLAN"]).read_text(encoding="utf-8")
start = "<!-- workflow-api:" + "start -->"
end = "<!-- workflow-api:" + "end -->"
match = re.search(
    re.escape(start) + r"\s*```json\s*(.*?)\s*```\s*" + re.escape(end),
    text,
    re.DOTALL,
)
assert match, "frozen API workflow block not found"
Path(os.environ["OUT"], "workflow-api.json").write_text(
    match.group(1).strip() + "\n", encoding="utf-8"
)
PY
jq empty "$OUT/workflow-api.json"
```

Run the blocking point contract against that frozen graph and save its evidence before starting Comfy:

```bash
SOURCE="$SOURCE" CORRECTIONS="$CORRECTIONS" WORKFLOW="$OUT/workflow-api.json" \
/Users/za/Documents/product\ images\ repo/.venv-gen/bin/python - \
  > "$OUT/point-contract.log" 2>&1 <<'PY'
import json
import hashlib
import os
from pathlib import Path
from PIL import Image

source = Image.open(os.environ["SOURCE"]).convert("RGB")
labels = Image.open(os.environ["CORRECTIONS"]).convert("RGBA")
with open(os.environ["WORKFLOW"], encoding="utf-8") as handle:
    workflow = json.load(handle)
positive = json.loads(workflow["3"]["inputs"]["positive_coords"])
negative = json.loads(workflow["3"]["inputs"]["negative_coords"])
xy = lambda point: (point["x"], point["y"])

assert hashlib.sha256(Path(os.environ["SOURCE"]).read_bytes()).hexdigest() == \
       "925c34a39a0e2b5a09ad92ba39dace87f652bcc90ff8e063e2a6f644e735df9d"
assert hashlib.sha256(Path(os.environ["CORRECTIONS"]).read_bytes()).hexdigest() == \
       "18d695a2cada3a2e1fb9a7c72f2ec04ed90a9e89d6dfc1d8d96a73bd47ab6a61"
assert source.size == labels.size == (941, 1672)
assert len(positive) == 15 and len(negative) == 10
assert len({xy(point) for point in positive}) == len(positive)
assert len({xy(point) for point in negative}) == len(negative)
assert not ({xy(point) for point in positive} & {xy(point) for point in negative})
assert all(0 <= point["x"] < 941 and 0 <= point["y"] < 1672
           for point in positive + negative)
assert all(labels.getpixel(xy(point)) == (255, 0, 0, 255)
           for point in positive[:5])
assert all(max(source.getpixel(xy(point))) - min(source.getpixel(xy(point))) >= 25
           for point in positive[5:])
assert all(min(min(pixel) for pixel in
               source.crop((point["x"] - 4, point["y"] - 4,
                            point["x"] + 5, point["y"] + 5)).getdata()) >= 250
           for point in negative)
print("PASS: 15 positive and 10 negative points satisfy the frozen class contract")
PY
```

Any nonzero exit is `BLOCKED`; inspect the log but do not edit the point set inside this scout.

## Runtime isolation

Launch the real checkout on an unused local port with:

- product `images/` as read-only input directory;
- `$OUT/comfy-output`, `$OUT/comfy-temp`, and `$OUT/comfy-user` as write roots;
- `sqlite:///:memory:` database;
- custom/API nodes disabled;
- `PYTHONDONTWRITEBYTECODE=1`, Hugging Face/Transformers offline mode, and caches redirected under `$OUT/runtime-cache`.

In the same shell where the input exports, workflow extraction, and point contract ran, start the server in the background. The assertions prevent a new terminal with missing variables from silently targeting the wrong paths. A trap stops Comfy on any later shell exit or interruption; stdout/stderr goes to `$OUT/comfy-server.log`.

```bash
: "${SOURCE:?run the Inputs and output root export block first}"
: "${OUT:?run the Inputs and output root export block first}"
test -d "$OUT/comfy-user"
if lsof -nP -iTCP:8198 -sTCP:LISTEN >/dev/null 2>&1; then
  echo 'BLOCKED: port 8198 already has a listener'
  exit 1
fi
PYTHONDONTWRITEBYTECODE=1 \
XDG_CACHE_HOME="$OUT/runtime-cache/xdg" \
HF_HOME="$OUT/runtime-cache/hf" \
HF_HUB_OFFLINE=1 \
TRANSFORMERS_OFFLINE=1 \
TORCH_HOME="$OUT/runtime-cache/torch" \
MPLCONFIGDIR="$OUT/runtime-cache/mpl" \
/Users/za/ComfyUI/venv/bin/python /Users/za/ComfyUI/main.py \
  --listen 127.0.0.1 \
  --port 8198 \
  --disable-auto-launch \
  --disable-all-custom-nodes \
  --disable-api-nodes \
  --database-url sqlite:///:memory: \
  --input-directory "$(dirname "$SOURCE")" \
  --output-directory "$OUT/comfy-output" \
  --temp-directory "$OUT/comfy-temp" \
  --user-directory "$OUT/comfy-user" \
  --log-stdout \
  > "$OUT/comfy-server.log" 2>&1 &
COMFY_PID=$!
trap 'kill -INT "$COMFY_PID" 2>/dev/null || true; wait "$COMFY_PID" 2>/dev/null || true' EXIT INT TERM
```

Wait no more than 120 seconds for `/system_stats`, fail if the process exits, then make the two schema checks blocking:

```bash
for attempt in $(seq 1 120); do
  if curl -fsS 'http://127.0.0.1:8198/system_stats' >/dev/null; then
    break
  fi
  kill -0 "$COMFY_PID" 2>/dev/null || {
    echo 'BLOCKED: Comfy exited during startup'
    exit 1
  }
  sleep 1
done
curl -fsS 'http://127.0.0.1:8198/system_stats' >/dev/null || {
  echo 'BLOCKED: Comfy readiness timeout'
  exit 1
}
{
  curl -fsS 'http://127.0.0.1:8198/object_info/CheckpointLoaderSimple' |
    jq -e '.CheckpointLoaderSimple.input.required.ckpt_name[0] |
           index("sam3.1_multiplex_fp16.safetensors") != null'
  curl -fsS 'http://127.0.0.1:8198/object_info/SAM3_Detect' |
    jq -e '.SAM3_Detect.input.required.model and
           .SAM3_Detect.input.required.image and
           .SAM3_Detect.input.optional.positive_coords and
           .SAM3_Detect.input.optional.negative_coords'
} > "$OUT/comfy-schema-check.log" 2>&1
```

Only after those checks pass, submit the single graph. Use `scripts/comfy_run.py` to fetch the `SaveImage` result directly to:

```text
$OUT/image14-sam31-point-proposal.png
```

Exact runner command; capture its stdout/stderr as `$OUT/comfy-run.log`:

```bash
RUN_STATUS=0
/Users/za/ComfyUI/venv/bin/python \
  /Users/za/Documents/product\ images\ repo/scripts/comfy_run.py \
  --server 127.0.0.1:8198 \
  --workflow "$OUT/workflow-api.json" \
  --out "$OUT/image14-sam31-point-proposal.png" \
  --timeout 1800 \
  > "$OUT/comfy-run.log" 2>&1 || RUN_STATUS=$?
kill -INT "$COMFY_PID" 2>/dev/null || true
wait "$COMFY_PID" 2>/dev/null || true
trap - EXIT INT TERM
test "$RUN_STATUS" -eq 0
```

Run the exact pre-matting gate:

```bash
PROPOSAL="$OUT/image14-sam31-point-proposal.png" \
/Users/za/Documents/product\ images\ repo/.venv-gen/bin/python - \
  > "$OUT/proposal-contract.log" 2>&1 <<'PY'
import os
from PIL import Image, ImageChops

with Image.open(os.environ["PROPOSAL"]) as image:
    assert image.format == "PNG"
    assert image.size == (941, 1672)
    red, green, blue = image.convert("RGB").split()
assert ImageChops.difference(red, green).getbbox() is None
assert ImageChops.difference(red, blue).getbbox() is None
low, high = red.getextrema()
assert low < 128 <= high
print(f"PASS: PNG 941x1672, RGB channels equal, value range {low}..{high}")
PY
```

Any server/model/MPS/dimension/proposal-contract failure is `BLOCKED`; do not switch checkpoints, prompts, thresholds, or devices inside this scout.

## Reuse the proven ViTMatte/decontamination stage

Run exactly once, without `--allow-fallback`, `--binary`, or `--overwrite`:

```bash
/Users/za/Documents/product\ images\ repo/.venv-gen/bin/python \
  /Users/za/Documents/product\ images\ repo/tasks/double-marine-bed-wrapper-batch/assisted_bg_remove.py \
  --source "$SOURCE" \
  --proposal "$OUT/image14-sam31-point-proposal.png" \
  --corrections "$CORRECTIONS" \
  --output "$OUT/image14-sam31-vitmatte-straight-rgba.png" \
  --metrics "$OUT/metrics.json" \
  --manifest "$OUT/candidate-manifest.json" \
  --review-board "$OUT/review-board-white-gray-black-magenta.png" \
  --backend vitmatte \
  --device mps \
  --proposal-fg-threshold 0.95 \
  --proposal-bg-threshold 0.05 \
  --inner-distance 3 \
  --outer-distance 3 \
  --correction-unlock-radius 110
```

This stage builds a conservative 0/0.5/1 trimap, applies the sparse sure-foreground corrections, runs cached ViTMatte-S, clamps sure sets, estimates background color, recovers straight foreground RGB, and creates the four-background board.

## Frozen gate and stop

Run the existing independent verifier once:

```bash
python3 /Users/za/Documents/product\ images\ repo/tasks/double-marine-bed-wrapper-batch/bg-benchmark/verify_bg_solution.py \
  --manifest /Users/za/Documents/product\ images\ repo/tasks/double-marine-bed-wrapper-batch/bg-benchmark/manifest.json \
  --candidate "image14=$OUT/image14-sam31-vitmatte-straight-rgba.png" \
  --json-report "$OUT/benchmark-report.json" \
  --review-dir "$OUT/benchmark-review"
```

Acceptance for the scout requires all of the following:

1. frozen source identity and 941×1672 straight-RGBA structure pass;
2. non-degenerate alpha plus reconstruction bounds pass;
3. all sure-foreground, exterior-background, enclosed-background, and edge probes pass without editing the benchmark;
4. a separate reviewer inspects native crops and the full candidate on white, gray, black, and magenta for pale-paint retention, interior-paper deletion, bubble/coral continuity, white fringe, dark premultiplication, and natural soft watercolor transitions.

Machine PASS remains `PENDING_HUMAN_REVIEW`; it is not production approval. Any machine failure, MPS failure, or human rejection ends this scout and preserves the evidence. Budget remains one: no prompt tweak, threshold sweep, repair pass, CPU fallback, alternate checkpoint, or upscale.

## Execution outcome — 2026-07-10

The one authorized official checkpoint transfer was attempted at `2026-07-10T11:37:35Z`. It ended after 30.002 seconds with `curl` exit `28` (`SSL connection timeout`), HTTP code `000`, and zero bytes downloaded. Neither the final checkpoint nor a `.part` file exists. Per the frozen stop condition, the lane stopped without a retry: Comfy was not launched, the graph was not submitted, ViTMatte was not run, and the benchmark was not invoked. Exact evidence is preserved in `$OUT/model-download.log` and `execution/LANE-REPORT.md`.

### Parent-loop transport retry authorization

The parent loop subsequently authorized exactly one network-transfer retry with a materially longer connection timeout. This is a transport-only resume after a zero-byte failure: it does not change the materialized five-node workflow, point arrays, checkpoint identity, radius `110`, MPS device, candidate budget, output root, or frozen benchmark. If this second transfer fails, remove `.part`, preserve `model-download-retry.log`, and stop permanently; if it verifies, submit the already-materialized graph exactly once.

The retry began at `2026-07-10T11:48:10Z` with a 300-second connection timeout and no curl retry flag. The official CDN connection returned HTTP `200` and transferred 1,305,342,008 of 1,745,546,848 expected bytes before `curl` exit `56` (`Recv failure: Connection reset by peer`) at 293.999 seconds. The incomplete file failed the fixed size/SHA gate and was removed; both final and `.part` checkpoint paths are absent. The lane is permanently stopped without launching Comfy or consuming the one graph candidate.

## Expected candidate artifacts

```text
$OUT/workflow-api.json
$OUT/point-contract.log
$OUT/model-download.log
$OUT/model-download-retry.log
$OUT/comfy-server.log
$OUT/comfy-schema-check.log
$OUT/comfy-run.log
$OUT/image14-sam31-point-proposal.png
$OUT/proposal-contract.log
$OUT/image14-sam31-vitmatte-straight-rgba.png
$OUT/metrics.json
$OUT/candidate-manifest.json
$OUT/review-board-white-gray-black-magenta.png
$OUT/benchmark-report.json
$OUT/benchmark-review/
```

No file is copied to `Images/finals/`; no alpha-aware upscaling occurs in this scout.

**STATUS: FINAL NETWORK BLOCKER; SECOND TRANSFER FAILED CLEANLY, NO CANDIDATE GENERATED.**

**READY FOR JUDGING.**
