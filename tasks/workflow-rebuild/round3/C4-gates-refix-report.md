# C4 Gates Refix Report

## 1. Per-bug diff summary

### S150-1: `content_gate.py` overlay default wrote beside raws

Before: `content_gate.py` defaults `--overlay` to `image_path.with_name(...)`, which means a caller that omits `--overlay` writes `*-content-gate-overlay.png` next to the raw image.

After: `scripts/round_runner.py:404-410` builds `gates/<stem>-content-gate-overlay.png` and invokes `content_gate.py` with `--overlay`. The targeted regression test now asserts `--overlay` is present and points under the round `gates/` directory at `tests/test_round_runner.py:292-299`.

Evidence:

```text
$ find tasks/workflow-rebuild/round3/raws -maxdepth 1 -type f ! -name 'arm-?_s?.png' -print | sort
```

No output: `round3/raws/` contains only the expected 10 raw PNGs.

Raw immutability hash check after the rerun:

```text
$ shasum -a 256 -c /private/tmp/round3_raws_before.sha
tasks/workflow-rebuild/round3/raws/arm-g_s1.png: OK
tasks/workflow-rebuild/round3/raws/arm-g_s2.png: OK
tasks/workflow-rebuild/round3/raws/arm-g_s3.png: OK
tasks/workflow-rebuild/round3/raws/arm-g_s4.png: OK
tasks/workflow-rebuild/round3/raws/arm-g_s5.png: OK
tasks/workflow-rebuild/round3/raws/arm-l_s1.png: OK
tasks/workflow-rebuild/round3/raws/arm-l_s2.png: OK
tasks/workflow-rebuild/round3/raws/arm-l_s3.png: OK
tasks/workflow-rebuild/round3/raws/arm-l_s4.png: OK
tasks/workflow-rebuild/round3/raws/arm-l_s5.png: OK
```

### S150-2: `gates.py --outdir` reused shared filenames across raws

Before: `gates.py` always wrote `<panel>-<stage>-bundle.json`, `<panel>-<stage>-overlay.png`, and shared dual-metric JSON filenames under one outdir. `round_runner.py` tried to move the shared bundle/overlay after each run, but the bundle internals and metric JSON paths still came from shared names.

After: `scripts/gates.py:458-462` adds `--output-stem`; `scripts/gates.py:470-487` uses it for bundle, overlay, and dual-metric JSON outputs. `scripts/round_runner.py:339-356` passes `--output-stem <raw-stem>-door-finish` and writes result rows from the bundle's actual per-raw paths. The targeted runner test asserts that `gates.py` receives `--output-stem arm-a_s1-door-finish` at `tests/test_round_runner.py:301-305`.

Path distinctness check after rerun:

```text
$ PYTHONDONTWRITEBYTECODE=1 python3 -c 'import json; from pathlib import Path; p=Path("tasks/workflow-rebuild/round3/round3-results.json"); rows=json.loads(p.read_text()); print("rows", len(rows)); print("distinct_bundle_paths", len({r.get("gates_bundle_path") for r in rows})); print("distinct_overlay_paths", len({r.get("overlay_path") for r in rows}));\
for r in rows:\
    b=Path(r["gates_bundle_path"]); data=json.loads(b.read_text()); print(Path(r["raw_path"]).name, "row_bundle_exists", b.exists(), "bundle_path_matches", data.get("bundle_path")==str(b), "overlay_matches", data.get("overlay_path")==r.get("overlay_path"), "dual_svg", data.get("dual_geometry",{}).get("svg"), "region_json", data.get("dual_geometry",{}).get("region_iou",{}).get("json_path"))'
rows 10
distinct_bundle_paths 10
distinct_overlay_paths 10
arm-l_s1.png row_bundle_exists True bundle_path_matches True overlay_matches True dual_svg /Users/za/Documents/product images repo/tasks/marriott-hospital/geometry/v3/door-panel.svg region_json /Users/za/Documents/product images repo/tasks/workflow-rebuild/round3/gates/arm-l_s1-door-finish-region-iou.json
arm-l_s2.png row_bundle_exists True bundle_path_matches True overlay_matches True dual_svg /Users/za/Documents/product images repo/tasks/marriott-hospital/geometry/v3/door-panel.svg region_json /Users/za/Documents/product images repo/tasks/workflow-rebuild/round3/gates/arm-l_s2-door-finish-region-iou.json
arm-l_s3.png row_bundle_exists True bundle_path_matches True overlay_matches True dual_svg /Users/za/Documents/product images repo/tasks/marriott-hospital/geometry/v3/door-panel.svg region_json /Users/za/Documents/product images repo/tasks/workflow-rebuild/round3/gates/arm-l_s3-door-finish-region-iou.json
arm-l_s4.png row_bundle_exists True bundle_path_matches True overlay_matches True dual_svg /Users/za/Documents/product images repo/tasks/marriott-hospital/geometry/v3/door-panel.svg region_json /Users/za/Documents/product images repo/tasks/workflow-rebuild/round3/gates/arm-l_s4-door-finish-region-iou.json
arm-l_s5.png row_bundle_exists True bundle_path_matches True overlay_matches True dual_svg /Users/za/Documents/product images repo/tasks/marriott-hospital/geometry/v3/door-panel.svg region_json /Users/za/Documents/product images repo/tasks/workflow-rebuild/round3/gates/arm-l_s5-door-finish-region-iou.json
arm-g_s1.png row_bundle_exists True bundle_path_matches True overlay_matches True dual_svg /Users/za/Documents/product images repo/tasks/marriott-hospital/geometry/v3/door-panel.svg region_json /Users/za/Documents/product images repo/tasks/workflow-rebuild/round3/gates/arm-g_s1-door-finish-region-iou.json
arm-g_s2.png row_bundle_exists True bundle_path_matches True overlay_matches True dual_svg /Users/za/Documents/product images repo/tasks/marriott-hospital/geometry/v3/door-panel.svg region_json /Users/za/Documents/product images repo/tasks/workflow-rebuild/round3/gates/arm-g_s2-door-finish-region-iou.json
arm-g_s3.png row_bundle_exists True bundle_path_matches True overlay_matches True dual_svg /Users/za/Documents/product images repo/tasks/marriott-hospital/geometry/v3/door-panel.svg region_json /Users/za/Documents/product images repo/tasks/workflow-rebuild/round3/gates/arm-g_s3-door-finish-region-iou.json
arm-g_s4.png row_bundle_exists True bundle_path_matches True overlay_matches True dual_svg /Users/za/Documents/product images repo/tasks/marriott-hospital/geometry/v3/door-panel.svg region_json /Users/za/Documents/product images repo/tasks/workflow-rebuild/round3/gates/arm-g_s4-door-finish-region-iou.json
arm-g_s5.png row_bundle_exists True bundle_path_matches True overlay_matches True dual_svg /Users/za/Documents/product images repo/tasks/marriott-hospital/geometry/v3/door-panel.svg region_json /Users/za/Documents/product images repo/tasks/workflow-rebuild/round3/gates/arm-g_s5-door-finish-region-iou.json
```

### S150-3: dual-metric geometry lookup expected `door.svg`

Before: direct `gates.py` defaulted `--svg` to `<geom>/<panel>.svg`; the actual geometry is `door-panel.svg`.

After: `scripts/gates.py:170-176` resolves explicit `--svg`, then `<panel>.svg`, then `<panel>-panel.svg`. `scripts/gates.py:452-457` documents the fallback. The new regression test at `tests/test_gate_defaults.py:189-203` renames `toy.svg` to `toy-panel.svg` and confirms dual geometry still runs.

Direct fallback smoke, with no `--svg` passed:

```text
$ PYTHONDONTWRITEBYTECODE=1 python3 -c 'import json, shutil, subprocess, sys; from pathlib import Path; out=Path("/private/tmp/gates_svg_fallback_smoke"); shutil.rmtree(out, ignore_errors=True); out.mkdir(parents=True); cmd=[sys.executable,"scripts/gates.py","--cand","tasks/workflow-rebuild/round3/raws/arm-l_s1.png","--geom","tasks/marriott-hospital/geometry/v3","--panel","door","--outdir",str(out),"--stage","finish","--output-stem","fallback-smoke"]; p=subprocess.run(cmd,capture_output=True,text=True); print("returncode", p.returncode); print(p.stderr.strip()); data=json.loads(p.stdout); print(json.dumps({"dual_available": data["dual_geometry"]["available"], "dual_svg": data["dual_geometry"].get("svg"), "bundle_path": data["bundle_path"], "overlay_path": data["overlay_path"], "files": sorted(x.name for x in out.iterdir())}, indent=2))'
returncode 2

{
  "dual_available": true,
  "dual_svg": "/Users/za/Documents/product images repo/tasks/marriott-hospital/geometry/v3/door-panel.svg",
  "bundle_path": "/private/tmp/gates_svg_fallback_smoke/fallback-smoke-bundle.json",
  "overlay_path": "/private/tmp/gates_svg_fallback_smoke/fallback-smoke-overlay.png",
  "files": [
    "fallback-smoke-bundle.json",
    "fallback-smoke-overlay.png",
    "fallback-smoke-region-iou.json",
    "fallback-smoke-white-iou.json"
  ]
}
```

## 2. Re-run gate table

Command used for the clean all-raw rerun:

```text
$ PYTHONDONTWRITEBYTECODE=1 python3 -c '<run_gates over arm-l_s1..s5 and arm-g_s1..s5 with geom=tasks/marriott-hospital/geometry/v3, panel=door, callouts=tasks/marriott-hospital/style-spec/feature-callouts-v1.yaml>'
raw,door_fill,gates_overall,gates_bundle_path,overlay_path
arm-l_s1.png,0.9971,FAIL,/Users/za/Documents/product images repo/tasks/workflow-rebuild/round3/gates/arm-l_s1-door-finish-bundle.json,/Users/za/Documents/product images repo/tasks/workflow-rebuild/round3/gates/arm-l_s1-door-finish-overlay.png
arm-l_s2.png,0.9945,FAIL,/Users/za/Documents/product images repo/tasks/workflow-rebuild/round3/gates/arm-l_s2-door-finish-bundle.json,/Users/za/Documents/product images repo/tasks/workflow-rebuild/round3/gates/arm-l_s2-door-finish-overlay.png
arm-l_s3.png,0.9584,FAIL,/Users/za/Documents/product images repo/tasks/workflow-rebuild/round3/gates/arm-l_s3-door-finish-bundle.json,/Users/za/Documents/product images repo/tasks/workflow-rebuild/round3/gates/arm-l_s3-door-finish-overlay.png
arm-l_s4.png,0.987,FAIL,/Users/za/Documents/product images repo/tasks/workflow-rebuild/round3/gates/arm-l_s4-door-finish-bundle.json,/Users/za/Documents/product images repo/tasks/workflow-rebuild/round3/gates/arm-l_s4-door-finish-overlay.png
arm-l_s5.png,0.964,FAIL,/Users/za/Documents/product images repo/tasks/workflow-rebuild/round3/gates/arm-l_s5-door-finish-bundle.json,/Users/za/Documents/product images repo/tasks/workflow-rebuild/round3/gates/arm-l_s5-door-finish-overlay.png
arm-g_s1.png,0.9877,FAIL,/Users/za/Documents/product images repo/tasks/workflow-rebuild/round3/gates/arm-g_s1-door-finish-bundle.json,/Users/za/Documents/product images repo/tasks/workflow-rebuild/round3/gates/arm-g_s1-door-finish-overlay.png
arm-g_s2.png,0.9743,FAIL,/Users/za/Documents/product images repo/tasks/workflow-rebuild/round3/gates/arm-g_s2-door-finish-bundle.json,/Users/za/Documents/product images repo/tasks/workflow-rebuild/round3/gates/arm-g_s2-door-finish-overlay.png
arm-g_s3.png,0.9796,FAIL,/Users/za/Documents/product images repo/tasks/workflow-rebuild/round3/gates/arm-g_s3-door-finish-bundle.json,/Users/za/Documents/product images repo/tasks/workflow-rebuild/round3/gates/arm-g_s3-door-finish-overlay.png
arm-g_s4.png,0.9864,FAIL,/Users/za/Documents/product images repo/tasks/workflow-rebuild/round3/gates/arm-g_s4-door-finish-bundle.json,/Users/za/Documents/product images repo/tasks/workflow-rebuild/round3/gates/arm-g_s4-door-finish-overlay.png
arm-g_s5.png,0.969,FAIL,/Users/za/Documents/product images repo/tasks/workflow-rebuild/round3/gates/arm-g_s5-door-finish-bundle.json,/Users/za/Documents/product images repo/tasks/workflow-rebuild/round3/gates/arm-g_s5-door-finish-overlay.png
```

Table:

| raw filename | door_fill metric | gates_overall verdict |
|---|---:|---|
| arm-l_s1.png | 0.9971 | FAIL |
| arm-l_s2.png | 0.9945 | FAIL |
| arm-l_s3.png | 0.9584 | FAIL |
| arm-l_s4.png | 0.987 | FAIL |
| arm-l_s5.png | 0.964 | FAIL |
| arm-g_s1.png | 0.9877 | FAIL |
| arm-g_s2.png | 0.9743 | FAIL |
| arm-g_s3.png | 0.9796 | FAIL |
| arm-g_s4.png | 0.9864 | FAIL |
| arm-g_s5.png | 0.969 | FAIL |

## 3. Full `verify_round_artifacts.py` output

Help checked first:

```text
$ python3 scripts/verify_round_artifacts.py --help
usage: verify_round_artifacts.py [-h] [--task TASK]
                                 [--review-root REVIEW_ROOT]
                                 round_dir
...
CLI:
  python3 scripts/verify_round_artifacts.py <round_dir> [--task NAME]
...
```

Run output:

```text
$ python3 scripts/verify_round_artifacts.py tasks/workflow-rebuild/round3 --task workflow-rebuild
{
  "pass": true,
  "missing": []
}
```

## 4. Full targeted pytest output

```text
$ python3 -m pytest tests/test_round_runner.py tests/test_gates_runner.py tests/test_gate_defaults.py tests/test_content_gate.py
============================= test session starts ==============================
platform darwin -- Python 3.9.6, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/za/Documents/product images repo
configfile: pytest.ini
plugins: anyio-4.12.1, hypothesis-6.141.1
collected 23 items

tests/test_round_runner.py ..........                                    [ 43%]
tests/test_gates_runner.py ...                                           [ 56%]
tests/test_gate_defaults.py ......                                       [ 82%]
tests/test_content_gate.py ....                                          [100%]

============================== 23 passed in 5.29s ==============================
```

READY FOR JUDGING
