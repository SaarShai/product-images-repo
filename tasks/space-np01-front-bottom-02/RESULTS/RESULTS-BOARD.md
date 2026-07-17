# RESULTS BOARD — space-np01-front-bottom-02

**Task:** Generate a watercolor illustration that fits EXACTLY inside SVG geometry (viewBox 767x2602, aspect ~1:3.4) with illustrated bevelled rims around 4 openings (3 hexagons + 1 slot).

**Gate:** region-IoU >= 0.85 (fill-agnostic placement metric). White-IoU measures hole cleanliness.

**Machine-readable data:** `results.jsonl` (one record per line, schema below).

---

## CALLOUTS

### Best Geometry (region-IoU)
**DREAM1** — dreamshaper-8 + lineart ControlNet + exact SVG clear → **region-IoU = 0.969**
> Local diffusers, MPS, 30 steps, 77.6s. Passes gate. Style = watercolor-leaning but still a flat SD wash; richer than vanilla SD1.5.

### Best Style (visual quality)
**BoN-nano-s3** — Nano Banana BoN sample → **region-IoU = 0.578** (below gate, confounded by aspect mismatch)
> Nano Banana outputs tend to have richer illustrative style but drift most from exact coordinates. All subscription BoN results are confounded by aspect mismatch (9:16 forced on 1:3.4 panel). Re-test needed.

### Hybrid Backstop (exact + model art)
**HYB1** — exact_bevel_composite.py + E1 model art → **region-IoU = 1.0 by construction**, white-IoU = 0.795
> Placement exact. Style degrades (smears controls near openings). Use only as fallback when nothing else passes gate.

### Best Confirmed PASS (geometry=exact, coverage metric)
**batch-np01-*/checkpoint/batch-bottom** — space-svg-exports-batch procedural runs → **PASS** (outside=0, cutout=0, coverage 98-100%)
> Different SVGs, procedural PIL (not model-painted). Geometry perfect. Style is simulated, not model-generated.

---

## LEGEND

| Column | Definition |
|---|---|
| `region-IoU` | Fill-agnostic: does the opening appear at the right location/shape regardless of fill? 0=nowhere, 1=exact. Measured by `scripts/geom_iou.py`. **GATE >= 0.85** |
| `white-IoU` | Are the openings actually white/empty? mean across openings. Measured by `scripts/svg_geometry_check.py`. |
| `outside_frac` | Fraction of panel paint outside the outer contour. Lower is better. |
| `verdict` | PASS = meets gate; FAIL = does not |
| `n/a` | Different metric used (batch: SVG mask coverage px=0) |
| `unknown` | Not measured |

---

## MASTER TABLE (sorted by region-IoU, top 30)

| id | method | model | region-IoU | judge-geom | judge-style | judge-verdict | gate |
|---|---|---|---|---|---|---|---|
| **FINAL-exact-frame** | unknown | unknown | 0.980 | 5 | 4 | ACCEPT | PASS |
| **CN-style-exact** | controlnet-style-sd15 | sd1.5 | 0.969 | unjudged | unjudged | unjudged | PASS |
| **RESEAT-rip-v2** | reseat-composite | unknown | 0.935 | 4 | 2 | LOCAL PATCH | PASS |
| **RESEAT-srcfinal-nb-s2** | unknown | unknown | 0.922 | 5 | 4 | ACCEPT | PASS |
| **CN-exact** | controlnet-lineart-sd15 | sd1.5 | 0.920 | unjudged | unjudged | unjudged | PASS |
| **RESEAT-rip-v1** | unknown | unknown | 0.910 | 4 | 3 | LOCAL PATCH | PASS |
| **RESEAT-srcfinal-nb-s4** | unknown | unknown | 0.898 | unjudged | unjudged | unjudged | PASS |
| **RESEAT-it2-nb-s4** | reseat-composite | unknown | 0.892 | 3 | 4 | ACCEPT | PASS |
| **RESEAT-reflayout-nano-s3** | nano-filled-contract | nano-banana | 0.883 | unjudged | unjudged | unjudged | PASS |
| **RESEAT-it3-nb-s4-thin** | reseat-composite | unknown | 0.882 | 4 | 4.5 | ACCEPT | PASS |
| **RESEAT-sparse-openai-s2** | gpt-image-best-of-n | gpt-image-2 | 0.881 | unjudged | unjudged | unjudged | PASS |
| **RESEAT-nb2-s1** | unknown | unknown | 0.880 | unjudged | unjudged | unjudged | PASS |
| **RESEAT-srcfinal-nb-s5** | unknown | unknown | 0.878 | unjudged | unjudged | unjudged | PASS |
| **RESEAT-nb2-s5** | unknown | unknown | 0.876 | unjudged | unjudged | unjudged | PASS |
| **RESEAT-it1-nb-s4** | reseat-composite | unknown | 0.876 | 4 | 4.5 | LOCAL PATCH | PASS |
| **RESEAT-bon2-s8** | unknown | unknown | 0.876 | unjudged | unjudged | unjudged | PASS |
| **RESEAT-nb-v3-s1-v2** | reseat-composite | unknown | 0.874 | 4 | 4 | ACCEPT | PASS |
| **RESEAT-bon2-s2-v2** | reseat-composite | unknown | 0.873 | 4 | 4 | ACCEPT | PASS |
| **RESEAT-srcfinal-nb-s1** | unknown | unknown | 0.872 | unjudged | unjudged | unjudged | PASS |
| **RESEAT-bon2-s8-v2** | reseat-composite | unknown | 0.866 | 4 | 4 | ACCEPT | PASS |
| **RESEAT-bon2-s2** | unknown | unknown | 0.862 | unjudged | unjudged | unjudged | PASS |
| **RESTYLE-nb-v1-s2** | restyle-locked | nano-banana | 0.856 | 5 | 5 | ACCEPT | PASS |
| RESEAT-oai-v3-s2-v2 | reseat-composite | unknown | 0.843 | 4 | 4 | ACCEPT | FAIL |
| RESEAT-oai-v3-s3-v2 | reseat-composite | unknown | 0.835 | 4 | 4 | ACCEPT | FAIL |
| RESEAT-sparse-openai-s3 | gpt-image-best-of-n | gpt-image-2 | 0.835 | unjudged | unjudged | unjudged | FAIL |
| RIP-openai-v1 | gpt-image-best-of-n | gpt-image-2 | 0.824 | unjudged | unjudged | unjudged | FAIL |
| RESTYLE-nb-v3-s3 | restyle-locked | nano-banana | 0.782 | 4 | 5 | ACCEPT | FAIL |
| RESEAT-nb-v3-s3-v2 | reseat-composite | unknown | 0.779 | 4 | 5 | ACCEPT | FAIL |
| RESEAT-nb-v3-s2-v2 | reseat-composite | unknown | 0.776 | 4 | 4 | ACCEPT | FAIL |
| RESTYLE-nb-v1-s1 | restyle-locked | nano-banana | 0.770 | 4 | 5 | ACCEPT | FAIL |

---

## METHOD GROUPS

### GROUP A1: ControlNet Lineart Clear (dreamshaper-8, local-diffusers)

| id | model | region-IoU | white-IoU | outside_frac | verdict | notes |
|---|---|---|---|---|---|---|
| DREAM1 | dreamshaper-8 | 0.524 | unknown | unknown | FAIL | geometry exact via SVG clear; STYLE flat navy wash, NO painted rims/controls/granulation — far from gorgeous target. Loc |

### GROUP A2: ControlNet Lineart SD1.5 (local-diffusers)

| id | model | region-IoU | white-IoU | outside_frac | verdict | notes |
|---|---|---|---|---|---|---|
| **CN-exact** | sd1.5 | 0.920 | unknown | unknown | PASS | region-IoU=0.920 |
| CN-hr | sd1.5 | 0.735 | unknown | unknown | FAIL | region-IoU=0.735 |
| CN1-controlnet | sd1.5 | 0.702 | 0.000 | 0.009 | FAIL | region-IoU=0.702. white-IoU=0.000. outside_frac=0.0089 |
| CN-s15 | sd1.5 | 0.689 | unknown | unknown | FAIL | region-IoU=0.689 |
| CN-s18 | sd1.5 | 0.678 | unknown | unknown | FAIL | region-IoU=0.678 |
| CN-s22 | sd1.5 | 0.670 | unknown | unknown | FAIL | region-IoU=0.670 |

### GROUP A3: ControlNet Style SD1.5 (local-diffusers)

| id | model | region-IoU | white-IoU | outside_frac | verdict | notes |
|---|---|---|---|---|---|---|
| **CN-style-exact** | sd1.5 | 0.969 | unknown | unknown | PASS | region-IoU=0.969 |
| STYLE1 | sd1.5 | 0.506 | unknown | unknown | FAIL | SD1.5 style injection with ref images, visual-only. region-IoU=0.506 |
| CN-style-drift | sd1.5 | 0.000 | unknown | unknown | FAIL | region-IoU=0.000 |

### GROUP A4: ControlNet Inpaint SD1.5 (local-diffusers)

| id | model | region-IoU | white-IoU | outside_frac | verdict | notes |
|---|---|---|---|---|---|---|
| CN-inpaint | sd1.5 | 0.000 | unknown | unknown | FAIL | region-IoU=0.000 |

### GROUP A5: ControlNet Canny SDXL (local-diffusers)

| id | model | region-IoU | white-IoU | outside_frac | verdict | notes |
|---|---|---|---|---|---|---|
| SDXL-scout | sdxl | unknown | unknown | unknown | unknown | SDXL + ControlNet canny scout. Model download (xinsir/controlnet-canny-sdxl-1.0) timed out. No output generated. |

### GROUP A6: ComfyUI Workflow (local-diffusers)

| id | model | region-IoU | white-IoU | outside_frac | verdict | notes |
|---|---|---|---|---|---|---|
| CW1-comfy | sd1.5 | unknown | unknown | unknown | unknown | ComfyUI workflow prepared (controlmap-lineart-512 + controlmap-canny-512) but no inference run executed. |

### GROUP B: Hybrid Composite (model art + code re-seating)

| id | model | region-IoU | white-IoU | outside_frac | verdict | notes |
|---|---|---|---|---|---|---|
| HYB1 | gpt-image-2+code | unknown | 0.795 | 0.000 | unknown | hybrid composite: gpt-image-2 art re-seated by exact_bevel_composite.py. white-IoU=0.795. outside_frac=0.0000 |

### GROUP C1: gpt-image-2 Best-of-N (codex)

| id | model | region-IoU | white-IoU | outside_frac | verdict | notes |
|---|---|---|---|---|---|---|
| **RESEAT-sparse-openai-s2** | gpt-image-2 | 0.881 | unknown | unknown | PASS | region-IoU=0.881 |
| RESEAT-sparse-openai-s3 | gpt-image-2 | 0.835 | unknown | unknown | FAIL | region-IoU=0.835 |
| RIP-openai-v1 | gpt-image-2 | 0.824 | 0.803 | 0.000 | FAIL | region-IoU=0.824. white-IoU=0.803. outside_frac=0.0003 |
| RESEAT-sparse-openai-s1 | gpt-image-2 | 0.761 | unknown | unknown | FAIL | region-IoU=0.761 |
| RESEAT-reflayout-openai-s1 | gpt-image-2 | 0.712 | unknown | unknown | FAIL | region-IoU=0.712 |
| E5-bestof-2 | gpt-image-2 | 0.507 | 0.474 | 0.086 | FAIL | Experiment E5-bestof-2. region-IoU=0.507. white-IoU=0.474. outside_frac=0.0855 |
| BoN-openai-s9 | gpt-image-2 | 0.453 | 0.438 | 0.003 | FAIL | gpt-image-2 BoN sample. AspectRatio forced 9:16 vs panel 1:3.4 (aspect mismatch).. region-IoU=0.453. white-IoU=0.438. ou |
| E5-bestof-1 | gpt-image-2 | 0.448 | 0.436 | 0.077 | FAIL | Experiment E5-bestof-1. region-IoU=0.448. white-IoU=0.436. outside_frac=0.0773 |
| E5-bestof-4 | gpt-image-2 | 0.434 | 0.394 | 0.084 | FAIL | Experiment E5-bestof-4. region-IoU=0.434. white-IoU=0.394. outside_frac=0.0844 |
| RESEAT-reflayout-openai-s3 | gpt-image-2 | 0.434 | unknown | unknown | FAIL | region-IoU=0.434 |
| RESEAT-reflayout-openai-s2 | gpt-image-2 | 0.434 | unknown | unknown | FAIL | region-IoU=0.434 |
| BoN2-openai-s1 | gpt-image-2 | 0.393 | 0.372 | 0.002 | FAIL | gpt-image-2 BoN round-2 letterboxed. region-IoU=0.393. white-IoU=0.372. outside_frac=0.0020 |
| BoN-openai-s4 | gpt-image-2 | 0.391 | 0.374 | 0.003 | FAIL | gpt-image-2 BoN sample. AspectRatio forced 9:16 vs panel 1:3.4 (aspect mismatch).. region-IoU=0.391. white-IoU=0.374. ou |
| BoN2-openai-s6 | gpt-image-2 | 0.388 | 0.374 | 0.002 | FAIL | gpt-image-2 BoN round-2 letterboxed. region-IoU=0.388. white-IoU=0.374. outside_frac=0.0023 |
| E5-bestof-5 | gpt-image-2 | 0.319 | 0.312 | 0.089 | FAIL | Experiment E5-bestof-5. region-IoU=0.319. white-IoU=0.312. outside_frac=0.0890 |
| BoN-openai-s5 | gpt-image-2 | 0.292 | 0.366 | 0.004 | FAIL | gpt-image-2 BoN sample. AspectRatio forced 9:16 vs panel 1:3.4 (aspect mismatch).. region-IoU=0.292. white-IoU=0.366. ou |
| BoN-openai-s7 | gpt-image-2 | 0.268 | 0.348 | 0.004 | FAIL | gpt-image-2 BoN sample. AspectRatio forced 9:16 vs panel 1:3.4 (aspect mismatch).. region-IoU=0.268. white-IoU=0.348. ou |
| BoN2-openai-s7 | gpt-image-2 | 0.240 | 0.238 | 0.003 | FAIL | gpt-image-2 BoN round-2 letterboxed. region-IoU=0.240. white-IoU=0.238. outside_frac=0.0028 |
| BoN2-openai-s5 | gpt-image-2 | 0.225 | 0.255 | 0.004 | FAIL | gpt-image-2 BoN round-2 letterboxed. region-IoU=0.225. white-IoU=0.255. outside_frac=0.0036 |
| BoN2-openai-s3 | gpt-image-2 | 0.191 | 0.222 | 0.002 | FAIL | gpt-image-2 BoN round-2 letterboxed. region-IoU=0.191. white-IoU=0.222. outside_frac=0.0017 |
| BoN-openai-s2 | gpt-image-2 | 0.184 | 0.366 | 0.004 | FAIL | gpt-image-2 BoN sample. AspectRatio forced 9:16 vs panel 1:3.4 (aspect mismatch).. region-IoU=0.184. white-IoU=0.366. ou |
| BoN-openai-s6 | gpt-image-2 | 0.076 | 0.311 | 0.005 | FAIL | gpt-image-2 BoN sample. AspectRatio forced 9:16 vs panel 1:3.4 (aspect mismatch).. region-IoU=0.076. white-IoU=0.311. ou |
| FIX-openai-v1 | gpt-image-2 | unknown | unknown | unknown | unknown | unknown |
| FIX-openai-v2 | gpt-image-2 | unknown | unknown | unknown | unknown | unknown |
| FIX-openai-v3 | gpt-image-2 | unknown | unknown | unknown | unknown | unknown |
| FIX-openai-v4 | gpt-image-2 | unknown | unknown | unknown | unknown | unknown |
| RIP-openai-v2 | gpt-image-2 | unknown | unknown | unknown | unknown | unknown |

### GROUP C2: gpt-image-2 Filled Contract (codex)

| id | model | region-IoU | white-IoU | outside_frac | verdict | notes |
|---|---|---|---|---|---|---|
| E1-filled-contract | gpt-image-2 | 0.409 | 0.371 | 0.084 | FAIL | Experiment E1-filled-contract. region-IoU=0.409. white-IoU=0.371. outside_frac=0.0836 |
| E11-filled-freeredraw | gpt-image-2 | 0.264 | 0.006 | 0.082 | FAIL | Ablation: no contract list. Catastrophic geometry loss.. region-IoU=0.264. white-IoU=0.006. outside_frac=0.0816 |

### GROUP C3: gpt-image-2 Lineart Contract (codex)

| id | model | region-IoU | white-IoU | outside_frac | verdict | notes |
|---|---|---|---|---|---|---|
| E3-lineart-contract | gpt-image-2 | 0.169 | 0.203 | 0.088 | FAIL | Experiment E3-lineart-contract. region-IoU=0.169. white-IoU=0.203. outside_frac=0.0880 |

### GROUP D1: Nano Banana Filled Contract (agy)

| id | model | region-IoU | white-IoU | outside_frac | verdict | notes |
|---|---|---|---|---|---|---|
| **RESEAT-reflayout-nano-s3** | nano-banana | 0.883 | unknown | unknown | PASS | region-IoU=0.883 |
| FIX-nano-v1 | nano-banana | 0.734 | 0.003 | 0.000 | FAIL | region-IoU=0.734. white-IoU=0.003. outside_frac=0.0002 |
| FIX-nano-v2 | nano-banana | 0.695 | 0.002 | 0.000 | FAIL | region-IoU=0.695. white-IoU=0.002. outside_frac=0.0002 |
| FIX-nano-v4 | nano-banana | 0.681 | 0.001 | 0.000 | FAIL | region-IoU=0.681. white-IoU=0.001. outside_frac=0.0002 |
| BoN2-nano-s8 | nano-banana | 0.676 | 0.676 | 0.000 | FAIL | Nano Banana BoN round-2 letterboxed. region-IoU=0.676. white-IoU=0.676. outside_frac=0.0002 |
| E2-filled-nano | nano-banana | 0.667 | 0.000 | 0.066 | FAIL | Experiment E2-filled-nano. region-IoU=0.667. white-IoU=0.000. outside_frac=0.0664 |
| BoN2-nano-s2 | nano-banana | 0.656 | 0.657 | 0.000 | FAIL | Nano Banana BoN round-2 letterboxed. region-IoU=0.656. white-IoU=0.657. outside_frac=0.0000 |
| BoN2-nano-s4 | nano-banana | 0.593 | 0.589 | 0.000 | FAIL | Nano Banana BoN round-2 letterboxed. region-IoU=0.593. white-IoU=0.589. outside_frac=0.0001 |
| BoN-nano-s3 | nano-banana | 0.578 | 0.006 | 0.000 | FAIL | Nano Banana BoN sample. AspectRatio forced 9:16 vs panel 1:3.4 (aspect mismatch).. region-IoU=0.578. white-IoU=0.006. ou |
| E4-lineart-nano | nano-banana | 0.573 | 0.036 | 0.071 | FAIL | Experiment E4-lineart-nano. region-IoU=0.573. white-IoU=0.036. outside_frac=0.0715 |
| BoN2-nano-s6 | nano-banana | 0.559 | 0.563 | 0.000 | FAIL | Nano Banana BoN round-2 letterboxed. region-IoU=0.559. white-IoU=0.563. outside_frac=0.0002 |
| BoN2-nano-s5 | nano-banana | 0.522 | 0.525 | 0.000 | FAIL | Nano Banana BoN round-2 letterboxed. region-IoU=0.522. white-IoU=0.525. outside_frac=0.0002 |
| RESEAT-sparse-nano-s3 | nano-banana | 0.521 | unknown | unknown | FAIL | region-IoU=0.521 |
| E2-filled-nano-s2 | nano-banana | 0.510 | 0.003 | 0.077 | FAIL | Experiment E2-filled-nano-s2. region-IoU=0.510. white-IoU=0.003. outside_frac=0.0774 |
| BoN-nano-s13 | nano-banana | 0.508 | 0.003 | 0.004 | FAIL | Nano Banana BoN sample. AspectRatio forced 9:16 vs panel 1:3.4 (aspect mismatch).. region-IoU=0.508. white-IoU=0.003. ou |
| RIP-nano-v2 | nano-banana | 0.493 | 0.000 | 0.001 | FAIL | region-IoU=0.493. white-IoU=0.000. outside_frac=0.0011 |
| BoN-nano-s4 | nano-banana | 0.489 | 0.001 | 0.002 | FAIL | Nano Banana BoN sample. AspectRatio forced 9:16 vs panel 1:3.4 (aspect mismatch).. region-IoU=0.489. white-IoU=0.001. ou |
| BoN-nano-s15 | nano-banana | 0.481 | 0.000 | 0.002 | FAIL | Nano Banana BoN sample. AspectRatio forced 9:16 vs panel 1:3.4 (aspect mismatch).. region-IoU=0.481. white-IoU=0.000. ou |
| BoN-nano-s6 | nano-banana | 0.477 | 0.003 | 0.002 | FAIL | Nano Banana BoN sample. AspectRatio forced 9:16 vs panel 1:3.4 (aspect mismatch).. region-IoU=0.477. white-IoU=0.003. ou |
| BoN-nano-s7 | nano-banana | 0.428 | 0.002 | 0.002 | FAIL | Nano Banana BoN sample. AspectRatio forced 9:16 vs panel 1:3.4 (aspect mismatch).. region-IoU=0.428. white-IoU=0.002. ou |
| BoN-nano-s8 | nano-banana | 0.421 | 0.368 | 0.002 | FAIL | Nano Banana BoN sample. AspectRatio forced 9:16 vs panel 1:3.4 (aspect mismatch).. region-IoU=0.421. white-IoU=0.368. ou |
| BoN-nano-s9 | nano-banana | 0.106 | 0.420 | 0.005 | FAIL | Nano Banana BoN sample. AspectRatio forced 9:16 vs panel 1:3.4 (aspect mismatch).. region-IoU=0.106. white-IoU=0.420. ou |
| BoN2-nano-s7 | nano-banana | 0.098 | 0.303 | 0.003 | FAIL | Nano Banana BoN round-2 letterboxed. region-IoU=0.098. white-IoU=0.303. outside_frac=0.0032 |
| BoN-nano-s2 | nano-banana | 0.079 | 0.033 | 0.004 | FAIL | Nano Banana BoN sample. AspectRatio forced 9:16 vs panel 1:3.4 (aspect mismatch).. region-IoU=0.079. white-IoU=0.033. ou |
| RESEAT-reflayout-nano-s1 | nano-banana | 0.066 | unknown | unknown | FAIL | region-IoU=0.066 |
| RESEAT-sparse-nano-s1 | nano-banana | 0.065 | unknown | unknown | FAIL | region-IoU=0.065 |
| RESEAT-sparse-nano-s2 | nano-banana | 0.064 | unknown | unknown | FAIL | region-IoU=0.064 |
| BoN-nano-s10 | nano-banana | 0.031 | 0.008 | 0.004 | FAIL | Nano Banana BoN sample. AspectRatio forced 9:16 vs panel 1:3.4 (aspect mismatch).. region-IoU=0.031. white-IoU=0.008. ou |
| RESEAT-reflayout-nano-s2 | nano-banana | 0.021 | unknown | unknown | FAIL | region-IoU=0.021 |
| BoN-nano-s1 | nano-banana | 0.019 | 0.064 | 0.005 | FAIL | Nano Banana BoN sample. AspectRatio forced 9:16 vs panel 1:3.4 (aspect mismatch).. region-IoU=0.019. white-IoU=0.064. ou |
| BoN-nano-s16 | nano-banana | 0.008 | 0.184 | 0.003 | FAIL | Nano Banana BoN sample. AspectRatio forced 9:16 vs panel 1:3.4 (aspect mismatch).. region-IoU=0.008. white-IoU=0.184. ou |
| BoN-nano-s12 | nano-banana | 0.004 | 0.155 | 0.005 | FAIL | Nano Banana BoN sample. AspectRatio forced 9:16 vs panel 1:3.4 (aspect mismatch).. region-IoU=0.004. white-IoU=0.155. ou |
| BoN-nano-s14 | nano-banana | 0.000 | 0.184 | 0.009 | FAIL | Nano Banana BoN sample. AspectRatio forced 9:16 vs panel 1:3.4 (aspect mismatch).. region-IoU=0.000. white-IoU=0.184. ou |
| BoN-nano-s5 | nano-banana | 0.000 | 0.001 | 0.005 | FAIL | Nano Banana BoN sample. AspectRatio forced 9:16 vs panel 1:3.4 (aspect mismatch).. region-IoU=0.000. white-IoU=0.001. ou |
| BoN-nano-s11 | nano-banana | 0.000 | 0.000 | 0.005 | FAIL | Nano Banana BoN sample. AspectRatio forced 9:16 vs panel 1:3.4 (aspect mismatch).. region-IoU=0.000. white-IoU=0.000. ou |
| BoN2-nano-s1 | nano-banana | 0.000 | 0.137 | 0.009 | FAIL | Nano Banana BoN round-2 letterboxed. region-IoU=0.000. white-IoU=0.137. outside_frac=0.0092 |
| BoN2-nano-s3 | nano-banana | 0.000 | 0.000 | 0.010 | FAIL | Nano Banana BoN round-2 letterboxed. region-IoU=0.000. white-IoU=0.000. outside_frac=0.0100 |
| FIX-nano-v3 | nano-banana | unknown | unknown | unknown | unknown | unknown |
| RIP-nano-v1 | nano-banana | 0.000 | 0.003 | 0.005 | FAIL | region-IoU=0.000. white-IoU=0.003. outside_frac=0.0050 |

### GROUP E1: SVG-Masked Procedural (local-python)

| id | model | region-IoU | white-IoU | outside_frac | verdict | notes |
|---|---|---|---|---|---|---|
| **batch-np01-back-bottom-batch-bottom-v1** | procedural-pil | n/a | n/a | 0 | PASS | space-svg-exports-batch procedural masking pass. Metric: SVG mask coverage (cutout+outside=0 pxl, ). PASS=PASS. Elements |
| **batch-np01-back-bottom-batch-bottom-v2** | procedural-pil | n/a | n/a | 0 | PASS | space-svg-exports-batch procedural masking pass. Metric: SVG mask coverage (cutout+outside=0 pxl, ). PASS=PASS. Elements |
| **batch-np01-front-bottom-batch-bottom-v1** | procedural-pil | n/a | n/a | 0 | PASS | space-svg-exports-batch procedural masking pass. Metric: SVG mask coverage (cutout+outside=0 pxl, ). PASS=PASS. Elements |
| **batch-np01-front-bottom-batch-bottom-v2** | procedural-pil | n/a | n/a | 0 | PASS | space-svg-exports-batch procedural masking pass. Metric: SVG mask coverage (cutout+outside=0 pxl, ). PASS=PASS. Elements |
| **batch-np02-back-bottom-batch-bottom-v1** | procedural-pil | n/a | n/a | 0 | PASS | space-svg-exports-batch procedural masking pass. Metric: SVG mask coverage (cutout+outside=0 pxl, ). PASS=PASS. Elements |
| **batch-np02-back-bottom-batch-bottom-v2** | procedural-pil | n/a | n/a | 0 | PASS | space-svg-exports-batch procedural masking pass. Metric: SVG mask coverage (cutout+outside=0 pxl, ). PASS=PASS. Elements |
| **batch-np02-front-bottom-batch-bottom-v1** | procedural-pil | n/a | n/a | 0 | PASS | space-svg-exports-batch procedural masking pass. Metric: SVG mask coverage (cutout+outside=0 pxl, ). PASS=PASS. Elements |
| **batch-np02-front-bottom-batch-bottom-v2** | procedural-pil | n/a | n/a | 0 | PASS | space-svg-exports-batch procedural masking pass. Metric: SVG mask coverage (cutout+outside=0 pxl, ). PASS=PASS. Elements |
| **batch-np01-back-top-checkpoint-v1** | procedural-pil | n/a | n/a | 0 | PASS | space-svg-exports-batch procedural masking pass. Metric: SVG mask coverage (cutout+outside=0 pxl, ). PASS=PASS. Elements |
| **batch-np01-front-bottom-checkpoint-v1** | procedural-pil | n/a | n/a | 0 | PASS | space-svg-exports-batch procedural masking pass. Metric: SVG mask coverage (cutout+outside=0 pxl, ). PASS=PASS. Elements |
| **batch-np01-back-bottom-checkpoint-bottom-v1** | procedural-pil | n/a | n/a | 0 | PASS | space-svg-exports-batch procedural masking pass. Metric: SVG mask coverage (cutout+outside=0 pxl, ). PASS=PASS. Elements |
| **batch-np01-back-bottom-checkpoint-bottom-v2** | procedural-pil | n/a | n/a | 0 | PASS | space-svg-exports-batch procedural masking pass. Metric: SVG mask coverage (cutout+outside=0 pxl, ). PASS=PASS. Elements |
| **batch-np01-front-bottom-space-style-v1** | procedural-pil | n/a | n/a | 0 | PASS | space-svg-exports-batch procedural masking pass. Metric: SVG mask coverage (cutout+outside=0 pxl, ). PASS=PASS. Elements |
| **batch-np01-front-bottom-space-style-v2** | procedural-pil | n/a | n/a | 0 | PASS | space-svg-exports-batch procedural masking pass. Metric: SVG mask coverage (cutout+outside=0 pxl, ). PASS=PASS. Elements |
| **batch-np01-front-top-checkpoint-v1** | procedural-pil | n/a | n/a | 0 | PASS | space-svg-exports-batch procedural masking pass. Metric: SVG mask coverage (cutout+outside=0 pxl, ). PASS=PASS. Elements |

### GROUP E2: SVG-Masked Style Rebuild (local-python)

| id | model | region-IoU | white-IoU | outside_frac | verdict | notes |
|---|---|---|---|---|---|---|
| **style-test-np01-back-top-locked-geometry-style-v1** | procedural-pil | n/a | n/a | 0 | PASS | Style rebuild on locked SVG geometry. coverage=99.53%, outside_px=0, cutout_px=0. PASS. |
| **style-test-np01-back-top-locked-packet-style-v2** | procedural-pil | n/a | n/a | 0 | PASS | Style rebuild on locked SVG geometry. coverage=99.51%, outside_px=0, cutout_px=0. PASS. |

### GROUP E3: Procedural PIL SVG Native (local-python)

| id | model | region-IoU | white-IoU | outside_frac | verdict | notes |
|---|---|---|---|---|---|---|
| **procedural-np01-back-top-watercolor-control-panel-candidate** | procedural-pil | n/a | n/a | 0 | PASS | PIL procedural watercolor control panel. coverage=100.0%, outside_px=0, cutout_px=0. PASS. |
| **procedural-np02-front-top-watercolor-control-panel-candidate** | procedural-pil | n/a | n/a | 0 | PASS | PIL procedural watercolor control panel. coverage=100.0%, outside_px=0, cutout_px=0. PASS. |

### GROUP F: Orphan raw model outputs (inputs unrecoverable)

Every gen image on disk is cataloged so none is dropped. Total **619** orphans (raw model gens + renders NOT already tied to an experiment dir, deduped by content hash). By model: gpt-image-2=506, nano-banana=113.
Per-image records (path + mtime) are in `results.jsonl` under id prefix `orphan-`. Listed as counts here to keep the board readable.

### GROUP X: unknown

| id | model | region-IoU | white-IoU | outside_frac | verdict | notes |
|---|---|---|---|---|---|---|
| **FINAL-exact-frame** | unknown | 0.980 | unknown | unknown | PASS | region-IoU=0.980 |
| **RESEAT-srcfinal-nb-s2** | unknown | 0.922 | unknown | unknown | PASS | region-IoU=0.922 |
| **RESEAT-rip-v1** | unknown | 0.910 | unknown | unknown | PASS | region-IoU=0.910 |
| **RESEAT-srcfinal-nb-s4** | unknown | 0.898 | unknown | unknown | PASS | region-IoU=0.898 |
| **RESEAT-nb2-s1** | unknown | 0.880 | unknown | unknown | PASS | region-IoU=0.880 |
| **RESEAT-srcfinal-nb-s5** | unknown | 0.878 | unknown | unknown | PASS | region-IoU=0.878 |
| **RESEAT-nb2-s5** | unknown | 0.876 | unknown | unknown | PASS | region-IoU=0.876 |
| **RESEAT-bon2-s8** | unknown | 0.876 | unknown | unknown | PASS | region-IoU=0.876 |
| **RESEAT-srcfinal-nb-s1** | unknown | 0.872 | unknown | unknown | PASS | region-IoU=0.872 |
| **RESEAT-bon2-s2** | unknown | 0.862 | unknown | unknown | PASS | region-IoU=0.862 |
| RESTYLE-nb-v1-s3 | nano-banana | 0.722 | 0.684 | 0.001 | FAIL | region-IoU=0.722. white-IoU=0.684. outside_frac=0.0013 |
| SRC-nb-s7 | nano-banana | 0.589 | 0.594 | 0.000 | FAIL | region-IoU=0.589. white-IoU=0.594. outside_frac=0.0004 |
| SRC-nb-s6 | nano-banana | 0.577 | 0.000 | 0.000 | FAIL | region-IoU=0.577. white-IoU=0.000. outside_frac=0.0002 |
| SRC-nb-s8 | nano-banana | 0.561 | 0.001 | 0.000 | FAIL | region-IoU=0.561. white-IoU=0.001. outside_frac=0.0003 |
| SRC-nb-s3 | nano-banana | 0.549 | 0.550 | 0.000 | FAIL | region-IoU=0.549. white-IoU=0.550. outside_frac=0.0001 |
| SRC-nb-s5 | nano-banana | 0.300 | 0.191 | 0.009 | FAIL | region-IoU=0.300. white-IoU=0.191. outside_frac=0.0088 |
| SRC-nb-s1 | nano-banana | 0.261 | 0.184 | 0.010 | FAIL | region-IoU=0.261. white-IoU=0.184. outside_frac=0.0099 |
| SRC-oai-s1 | gpt-image-2 | 0.189 | 0.192 | 0.002 | FAIL | region-IoU=0.189. white-IoU=0.192. outside_frac=0.0019 |
| RESEAT-nb2-s3 | unknown | 0.096 | unknown | unknown | FAIL | region-IoU=0.096 |
| RESEAT-nb2-s7 | unknown | 0.065 | unknown | unknown | FAIL | region-IoU=0.065 |
| RESEAT-nb2-s6 | unknown | 0.064 | unknown | unknown | FAIL | region-IoU=0.064 |
| RESEAT-srcfinal-nb-s3 | unknown | 0.064 | unknown | unknown | FAIL | region-IoU=0.064 |
| RESEAT-srcfinal-nb-s7 | unknown | 0.064 | unknown | unknown | FAIL | region-IoU=0.064 |
| RESEAT-srcfinal-nb-s6 | unknown | 0.064 | unknown | unknown | FAIL | region-IoU=0.064 |
| RESEAT-nb2-s8 | unknown | 0.063 | unknown | unknown | FAIL | region-IoU=0.063 |
| RESEAT-nb2-s4 | unknown | 0.062 | unknown | unknown | FAIL | region-IoU=0.062 |
| RESEAT-srcfinal-nb-s8 | unknown | 0.062 | unknown | unknown | FAIL | region-IoU=0.062 |
| RESEAT-nb2-s2 | unknown | 0.062 | unknown | unknown | FAIL | region-IoU=0.062 |
| SRC-nb-s4 | nano-banana | 0.030 | 0.010 | 0.011 | FAIL | region-IoU=0.030. white-IoU=0.010. outside_frac=0.0106 |
| BoN2-openai-s2 | unknown | unknown | unknown | unknown | unknown | Empty experiment directory — no outputs. |
| RESTYLE-ip-is60-cs15-prompt | unknown | unknown | unknown | unknown | unknown | unknown |
| RESTYLE-ip-is85-cs125 | unknown | 0.000 | unknown | unknown | FAIL | region-IoU=0.000 |
| RESTYLE-ip-is85-cs15 | unknown | 0.000 | unknown | unknown | FAIL | region-IoU=0.000 |
| RESTYLE-oai-v1-s2 | gpt-image-2 | unknown | unknown | unknown | unknown | unknown |
| RESTYLE-oai-v3-s4 | gpt-image-2 | unknown | unknown | unknown | unknown | unknown |
| RIMSPLIT-d14-s12345 | unknown | unknown | unknown | unknown | unknown | unknown |
| SRC-nb-s2 | nano-banana | 0.000 | 0.118 | 0.010 | FAIL | region-IoU=0.000. white-IoU=0.118. outside_frac=0.0103 |
| SRC-oai-s3 | gpt-image-2 | unknown | 0.277 | 0.001 | unknown | white-IoU=0.277. outside_frac=0.0011 |

### GROUP X: reseat-composite

| id | model | region-IoU | white-IoU | outside_frac | verdict | notes |
|---|---|---|---|---|---|---|
| **RESEAT-rip-v2** | unknown | 0.935 | 0.703 | unknown | PASS | region-IoU=0.935. white-IoU=0.703 |
| **RESEAT-it2-nb-s4** | unknown | 0.892 | unknown | 0.000 | PASS | region-IoU=0.892. outside_frac=0.0000 |
| **RESEAT-it3-nb-s4-thin** | unknown | 0.882 | unknown | 0.000 | PASS | region-IoU=0.882. outside_frac=0.0000 |
| **RESEAT-it1-nb-s4** | unknown | 0.876 | unknown | unknown | PASS | region-IoU=0.876 |
| **RESEAT-nb-v3-s1-v2** | unknown | 0.874 | 0.712 | unknown | PASS | region-IoU=0.874. white-IoU=0.712 |
| **RESEAT-bon2-s2-v2** | unknown | 0.873 | 0.707 | unknown | PASS | region-IoU=0.873. white-IoU=0.707 |
| **RESEAT-bon2-s8-v2** | unknown | 0.866 | 0.706 | unknown | PASS | region-IoU=0.866. white-IoU=0.706 |
| RESEAT-oai-v3-s2-v2 | unknown | 0.843 | 0.681 | unknown | FAIL | region-IoU=0.843. white-IoU=0.681 |
| RESEAT-oai-v3-s3-v2 | unknown | 0.835 | 0.644 | unknown | FAIL | region-IoU=0.835. white-IoU=0.644 |
| RESEAT-nb-v3-s3-v2 | unknown | 0.779 | 0.692 | unknown | FAIL | region-IoU=0.779. white-IoU=0.692 |
| RESEAT-nb-v3-s2-v2 | unknown | 0.776 | 0.688 | unknown | FAIL | region-IoU=0.776. white-IoU=0.688 |
| RESEAT-it4-nb-s2 | unknown | 0.654 | unknown | unknown | FAIL | geom_iou reads opening4(slot)=0.0 because the source's painted slot is offset-left+short vs the SVG slot; svg_geometry_c |
| RESEAT-oai-v3-s1-v2 | unknown | 0.000 | 0.688 | unknown | FAIL | region-IoU=0.000. white-IoU=0.688 |

### GROUP X: restyle-locked

| id | model | region-IoU | white-IoU | outside_frac | verdict | notes |
|---|---|---|---|---|---|---|
| **RESTYLE-nb-v1-s2** | nano-banana | 0.856 | 0.002 | 0.001 | PASS | region-IoU=0.856. white-IoU=0.002. outside_frac=0.0008 |
| RESTYLE-nb-v3-s3 | nano-banana | 0.782 | 0.753 | 0.001 | FAIL | region-IoU=0.782. white-IoU=0.753. outside_frac=0.0008 |
| RESTYLE-nb-v1-s1 | nano-banana | 0.770 | 0.749 | 0.001 | FAIL | region-IoU=0.770. white-IoU=0.749. outside_frac=0.0008 |
| RESTYLE-nb-v3-s1 | nano-banana | 0.728 | 0.737 | 0.001 | FAIL | region-IoU=0.728. white-IoU=0.737. outside_frac=0.0006 |
| RESTYLE-nb-v3-s2 | nano-banana | 0.677 | 0.640 | 0.001 | FAIL | region-IoU=0.677. white-IoU=0.640. outside_frac=0.0010 |
| RESTYLE-oai-v1-s1 | gpt-image-2 | 0.646 | 0.609 | 0.004 | FAIL | region-IoU=0.646. white-IoU=0.609. outside_frac=0.0043 |
| RESTYLE-oai-v3-s1 | gpt-image-2 | 0.479 | 0.571 | 0.003 | FAIL | region-IoU=0.479. white-IoU=0.571. outside_frac=0.0032 |
| RESTYLE-oai-v3-s2 | gpt-image-2 | 0.381 | 0.439 | 0.004 | FAIL | region-IoU=0.381. white-IoU=0.439. outside_frac=0.0038 |
| RESTYLE-oai-v3-s3 | gpt-image-2 | 0.342 | 0.328 | 0.003 | FAIL | region-IoU=0.342. white-IoU=0.328. outside_frac=0.0032 |
| RESTYLE-cn-cs16 | Lykon/dreamshaper-8 | 0.000 | unknown | unknown | FAIL | region-IoU=0.000 |

---

## SUMMARY: WHERE WE STAND

- Total records: **782**
- PASS (region-IoU >= 0.85 or procedural): **41**
- FAIL: **107**
- Unknown / stub: **634**

**Top-5 by region-IoU:**
- FINAL-exact-frame: region-IoU=0.980 (PASS)
- CN-style-exact: region-IoU=0.969 (PASS)
- RESEAT-rip-v2: region-IoU=0.935 (PASS)
- RESEAT-srcfinal-nb-s2: region-IoU=0.922 (PASS)
- CN-exact: region-IoU=0.920 (PASS)

**Open problem:** No method yet gives BOTH exact geometry (region-IoU >= 0.85) AND gorgeous model-painted watercolor style with illustrated bevel rims simultaneously.

**Critical next experiments:**
1. dreamshaper-8 + CN + IP-Adapter (style from ref images) — expected to solve style gap while keeping geometry locked.
2. Nano Banana + correct aspect (native tall ratio, letter-box) — aspect mismatch was the prime confound; re-test needed.
3. gpt-image-2 edit mode with letter-boxed DREAM1 output as base — combine subscription style with locked geometry.

---

## SCHEMA (results.jsonl fields)

```
id            — unique experiment identifier
method        — [controlnet-lineart-clear | controlnet-lineart-sd15 | gpt-image-best-of-n |
                  gpt-image-filled-contract | gpt-image-lineart-contract | gpt-image-free-redraw |
                  nano-filled-contract | nano-lineart-contract | hybrid-composite |
                  svg-masked-procedural | svg-masked-style-rebuild | procedural-pil-svg-native |
                  controlnet-style-sd15 | controlnet-inpaint | controlnet-style-clear]
model         — [sd1.5 | dreamshaper-8 | gpt-image-2 | nano-banana | procedural-pil | gpt-image-2+code]
platform      — [local-diffusers | codex | agy | local-python | codex+local]
reference_images — paths to style reference PNGs
svg           — path to source SVG template
prompt        — path to prompt file or inline text
control_map   — path to ControlNet conditioning map or genmap used as reference
region_iou    — fill-agnostic placement metric (geom_iou.py); "unknown" | "n/a" | float
white_iou     — mean opening emptiness (svg_geometry_check.py); "unknown" | "n/a" | float
outside_frac  — fraction of paint outside SVG contour; "unknown" | float
painted_max   — max hole painted_frac (highest contamination); "unknown" | "n/a" | float
image_path_raw  — generated image before any SVG clearing
image_path_exact — image after SVG punching (openings + outside cleared)
timestamp     — ISO-8601 file mtime
notes         — key takeaway, 1-2 sentences
verdict       — PASS | FAIL | unknown
```

---

*Auto-generated by `scripts/results_db.py`. Re-run to refresh. Source: all experiment dirs under `tasks/space-np01-front-bottom-02/experiments/` and `tasks/space-svg-exports-batch/`.*
