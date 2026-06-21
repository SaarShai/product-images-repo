# C — Automated visual verification / judging of generated image edits

Research goal: stop eyeballing every edit. Automate four checks per result:
(a) element well-formed (no melted car, 5 fingers, no leftover text),
(b) matches surrounding watercolor style,
(c) nothing changed outside the mask (we already have a pixel gate — upgrade it),
(d) artwork fits the SVG contour / avoids cutouts (already covered by `geom_gate.py`).

Stack on hand: Claude + GPT (gpt-image/gpt-4o) + GLM (z.ai) vision; Apple M3 Max
(MPS) local; Python. Existing harness in `scripts/`: `judge_panel.py`,
`dup_detect.py`, `geom_gate.py`, `objective_gate_report.py`, `compose_fairy.py
--diffmask`, `geom_iou.py`.

All claims below are from sources fetched this session; URLs verified. Where a
claim is an inference (not in a source), it is tagged **[inference]**.

---

## 0. The single most important finding (drives every recommendation)

**Pairwise beats absolute/pointwise scoring for VLM judges — by a large,
measured margin — and the gain is biggest on the exact task we have (image
EDITING).** From GenArena (arXiv 2602.06013), off-the-shelf VLMs with NO
fine-tuning:

- Image **editing** (EditScore-Bench), Qwen3-VL-8B: **58.3% → 83.7%** accuracy
  just by switching pointwise → pairwise (**+25.4 pp**).
- Image generation (GenAI-Bench): 49.1% → 60.5% (+11.4 pp).
- Human-alignment correlation with LMArena: **0.36 (pointwise) → 0.86 (pairwise)**.
- Self-consistency (Krippendorff α): pointwise as low as **0.52**; the
  consistency-checked pairwise protocol reaches **0.86**.
- Recommended protocol: forced binary choice (NO ties — allowing ties caused
  "laziness bias", models picked neutral in ~40% of human-clear cases, dropping
  accuracy to 54.9%), **swap image order to detect position bias, keep only
  order-consistent verdicts**, aggregate with Elo / Bradley-Terry.

This is corroborated by MJ-Bench (arXiv 2407.04842) and the VLM-as-a-Judge
protocol survey (emergentmind): chain-of-thought analysis-before-score helps but
does not substitute for true multimodal grounding; naive multi-judge averaging
can *degrade* performance — a single reliable judge or reliability-weighted
aggregation beats undiscriminating voting.

**Implication for us:** our current judge is absolute/pointwise (the A–I rubric
in `judge_panel.py` returns PASS/FAIL + scores per candidate in isolation). The
highest-ROI change is to **judge each new candidate PAIRWISE against a known-good
reference (the approved prior edit, or the original pre-edit crop), forced binary,
run twice with the two images swapped, accept only if the verdict is consistent.**
This is cheap (2 VLM calls) and directly attacks the "VLMs cluster on genre, miss
artist-level refinement" failure we already banked in memory.

Sources:
- GenArena: https://arxiv.org/html/2602.06013 · https://arxiv.org/pdf/2602.06013
- MJ-Bench: https://arxiv.org/pdf/2407.04842
- VLM-as-a-judge protocol survey: https://www.emergentmind.com/topics/vlm-as-a-judge-protocol

---

## 1. VLM-as-judge for image quality — what works, failure modes

### What works
- **Pairwise, forced-choice, order-swapped, consistency-gated** (see §0). Single
  best lever.
- **Multi-criteria decomposition + chain-of-thought**: rubric = per-aspect
  natural-language criterion + discrete score levels (1–5 typical), judge reasons
  per aspect before scoring. CoT improves feedback quality and alignment.
- **Reference anchoring**: give the judge a reference assumed near-perfect to
  calibrate the scale. (Matches our existing "reference examples" practice.)
- **Per-aspect reporting**, not one blended number — over-aggregation conceals
  judge weaknesses (emergentmind).
- **Judge from hi-DPI tiles, not the downsampled full image** — already a banked
  lesson here; the literature backs the resolution-loss failure implicitly via
  "true multimodal grounding" emphasis. Keep tiling.

### Failure modes (verified)
- **Position / order bias** → mitigate with order-swap + consistency gate (GenArena).
- **Laziness / tie bias** → forbid ties, force binary (GenArena, ~40% neutral-when-clear).
- **Pointwise stochastic instability** → α as low as 0.52 across reruns (GenArena).
- **Scale insensitivity & aesthetics non-rankability** → our own evidence: 3 judges
  scored a poor- and good-style gen the SAME (~72–82) on style/proportions.
  Confirmed pattern: **never auto-PASS aesthetics; route style/taste to human,
  gate only objective/structural checks.** (Already encoded in `judge_panel.py`
  OBJECTIVE vs AESTHETIC split — keep it.)
- **Over/under-counting (duplicates)** → VLMs miss stacked duplicate elements;
  back the count with a deterministic detector (we already have `dup_detect.py`).
- **Shared-model bias across judges** → if ensembling, use *different vendors*
  (Claude + GPT + GLM), and prefer a single reliable judge over naive averaging.

### Judge-model picks (verified numbers)
- **GLM-4V-Flash (9B)** hit **87.2% on EditScore-Bench**, *beating GPT-5's 75.5%*
  on image editing (GenArena). We already have GLM (z.ai) wired via
  `glm-executor` — strong, cheap default judge for the editing task.
- Qwen3-VL (4B/8B/32B) best overall open model; 32B-FP8 = 68.0% overall.
- Prometheus-Vision: Pearson 0.836 on LLaVA-Bench (surpassed GPT-4V self-consistency 0.797).

| item | URL | license/cost | local/API | checks | effort | wire-in |
|---|---|---|---|---|---|---|
| Pairwise forced-choice protocol | arxiv 2602.06013 | paper (free) | N/A | style/quality/edit-fidelity ranking | **M** | new `judge_pairwise.py`: cand vs reference, 2 calls swapped, consistency gate |
| GLM-4V (z.ai) as judge | existing `glm-executor` | API, cheap | API | per-aspect + pairwise verdict | **S** | reuse subagent; feed hi-DPI crops |
| Multi-vendor cross-check | Claude+GPT+GLM | API | API | high-stakes disagreement resolution | **S** | only on disagreement (verify-before-completion already says this) |

---

## 2. Eval / test frameworks for image-gen QA (image inputs + LLM-judge + regression)

| name | URL | license/cost | local/API | image input? | LLM-judge? | regression/snapshot | effort |
|---|---|---|---|---|---|---|---|
| **promptfoo** | https://github.com/promptfoo/promptfoo · https://www.promptfoo.dev/docs/configuration/expected-outputs/model-graded/ | MIT, free | local CLI, calls any API | **Yes** — `llm-rubric` grades images; pass `rubricPrompt` in OpenAI chat format with `image_url`, vision provider (gpt-5/gpt-4o, Claude via OpenAI-format) | Yes (`llm-rubric`, `g-eval`) + deterministic asserts (regex/contains/`python`/`javascript`) | Yes — YAML test cases run in CI; deterministic asserts are the snapshot/regression layer | **M** |
| **DeepEval** | https://deepeval.com/docs/multimodal-metrics-image-coherence · https://deepeval.com/docs/introduction | Apache-2.0, free | local lib, any judge (OpenAI/Azure/Ollama/Anthropic/Gemini/LiteLLM) | **Yes** — `MLLMTestCase` + `MLLMImage(url/local)`; metrics: Image Coherence, Text-to-Image, Image Helpfulness/Reference, multimodal G-Eval | Yes (G-Eval/DAG/QAG) | Yes — pytest-style, CI-friendly | **M** |
| **OpenAI Evals** (incl. cookbook image-evals) | https://developers.openai.com/cookbook/examples/multimodal/image_evals · https://github.com/openai/openai-cookbook/blob/main/examples/multimodal/image_evals.ipynb | MIT-ish/free framework, API graders cost | API-centric | **Yes** — vision graders; or describe-then-grade-as-text | Yes — model graders return 0–1 | Yes — test-cases/runners/graders plug-ins | **M** |
| W&B Weave | (general LLM-eval; image logging) | free tier | API/SaaS | logging-focused, not a gate | partial | logging/comparison dashboards | **M** |
| custom Python harness | our `objective_gate_report.py` + `run_matrix.py` | ours | local | yes | yes (subagent) | yes (`results.jsonl`) | **S** (extend) |

**Recommendation for frameworks:** we already have a working custom harness
(`objective_gate_report.py`, `run_matrix.py`, `results.jsonl`, `dashboard.html`).
Do **not** rip it out. Either: (i) keep custom and add the pairwise judge +
metric gates as new scripts, or (ii) adopt **promptfoo** as the *thin CI/regression
wrapper* so a known-bad edit becomes a permanent failing test case (its
deterministic asserts + `python` assert can shell out to our metric scripts, and
`llm-rubric` does the vision judge). promptfoo is the lightest path to
"snapshot/regression testing" because it's MIT, runs locally, and calls our
existing Python via the `python` assertion. **[inference]** DeepEval is the
better fit if we want pytest-native multimodal G-Eval in-process.

---

## 3. Deterministic image metrics — change-nothing-else gate + similarity/quality

All are pure-PyTorch or numpy → run on **MPS** (set `PYTORCH_ENABLE_MPS_FALLBACK=1`
for any op not yet in Metal; LPIPS/DISTS use VGG/Alex convs that run on MPS, with
CPU fallback for stragglers — verified pattern, not a blocker on M3 Max).

| metric | lib / URL | license | local | ref type | good for | bad for | effort |
|---|---|---|---|---|---|---|---|
| **SSIM / MS-SSIM** | scikit-image `structural_similarity` https://scikit-image.org/docs/stable/auto_examples/transform/plot_ssim.html ; also piq | BSD / Apache | yes (CPU/MPS) | full-ref | cheap structural delta; **masked SSIM** by computing only inside/outside a region (no native mask arg → crop or covisibility-mask, documented workaround) | texture/style nuance; perceptual | **S** |
| **LPIPS** | richzhang/PerceptualSimilarity `pip install lpips` https://github.com/richzhang/PerceptualSimilarity ; also piq & torchmetrics | BSD-2 | yes (MPS) | full-ref | perceptual similarity that tracks human judgment; good "did the look change" signal | not localized; whole-patch | **S** |
| **DISTS** | torchmetrics https://lightning.ai/docs/torchmetrics/stable/image/dists.html ; piq | Apache-2.0 | yes (MPS) | full-ref | **structure+texture disentangled** — best for "same content, watercolor texture preserved?" | needs aligned pair | **S** |
| **DINOv2 cosine** | facebookresearch/dinov2 ; via torch.hub | Apache-2.0 | yes (MPS) | embedding | **local change / edit detection** — fine-grained geometry, 64% vs CLIP 28% on hard similarity; patch-level cosine separates edits well | semantic labels | **M** |
| **CLIP cosine** | open_clip / transformers | MIT/various | yes (MPS) | embedding | "is it still the same kind of thing" (semantic), text-image alignment | local/structural edits (weak; 28% on hard set) | **S** |
| **perceptual hash (pHash/dHash)** | JohannesBuchner/imagehash `pip install ImageHash` https://github.com/JohannesBuchner/imagehash | BSD | yes (CPU) | full-ref | ultra-cheap near-dup / "did anything move" smoke test (Hamming distance), invariant to blur/resize | not for fine quality | **S** |
| piq (one-stop) | https://github.com/photosynthesis-team/piq | Apache-2.0 | yes | FR+NR+FID | SSIM/MS-SSIM/LPIPS/DISTS/BRISQUE/CLIP-IQA/FID all in one import | — | **S** |

### Change-nothing-else gate upgrade (item c)
Today: `compose_fairy.py --diffmask` requires byte-exact outside the mask
(delta=0). That's correct as a **hard** gate and should stay. But two gaps:
1. It can't tell whether the *inside-mask* change is acceptable, only that
   outside is untouched.
2. When an instruction-edit engine repaints the whole crop (we banked: "81% of
   box drifted"), a feathered-rect outside-mask gate is blind to leakage near the
   seam. **Upgrade:** add a **DINOv2 patch-cosine map** between original and edit
   — high cosine everywhere *outside* the intended region = clean; a drop outside
   the mask = leakage the pixel gate's feather missed. DINOv2 (not CLIP) because
   it's the verified winner for local edit/change detection. Pair with masked
   **SSIM/DISTS** inside-region to confirm the edit landed without nuking texture.

---

## 4. Defect / anomaly detectors (item b — well-formedness)

| target | tool | URL | license | local | checks | effort | wire-in |
|---|---|---|---|---|---|---|---|
| **leftover text (residual "TAXI" after removal)** | **PaddleOCR** | https://github.com/PaddlePaddle/PaddleOCR | Apache-2.0 | yes | detect+read text in a crop; if any box found in the cleaned region → FAIL | **M** | run on the post-removal crop; assert zero text boxes (or none matching the removed string) |
| same (lighter) | **EasyOCR** | (pip easyocr) | Apache-2.0 | yes | simple API, good scene text on GPU/MPS | **S** | same |
| same (fastest, weakest) | **Tesseract** (pytesseract) | — | Apache-2.0 | yes | <0.3s init, fine for clean printed text, weak on rotation >5° | **S** | quick smoke pass |
| **hands / finger count** | **MediaPipe Hands** | https://mediapipe.readthedocs.io/en/latest/solutions/hands.html | Apache-2.0 | yes | 21 landmarks/hand; count extended fingers, flag anomalies | **M** | run on character crops with hands; **caveat: tuned for photos, watercolor hands may under-detect → use as advisory, not hard gate** [inference] |
| **duplicate objects** | our **`dup_detect.py`** (multi-scale template match + NMS) | repo | ours | yes | counts stacked/extra windows/doors | already built | keep as count-gate backstop behind VLM |
| **duplicate objects (general)** | YOLO + `supervision` count + NMS | https://roboflow.com/how-to-count/yolov8 | AGPL (YOLOv8) / check | yes | class-wise detection count w/ NMS | **L** | AGPL license risk; template-match (`dup_detect.py`) already covers our fixed elements — prefer it |

OCR accuracy ranking (verified): **PaddleOCR 0.93 avg confidence > Tesseract 0.89
> EasyOCR 0.85**; PaddleOCR best on rotated/scene text (angle classifier +8ms);
Tesseract fastest init but collapses past 5° rotation. For "did the removal leave
text?" PaddleOCR is the accuracy pick; the **gate is trivial: run OCR on the
edited region, FAIL if any text box overlaps where the element was removed.**

---

## 5. How teams QA AI image pipelines at scale (patterns to borrow)

Public write-ups are mostly enterprise/marketing (Grepsr, Scale AI, Crescendo),
but the reusable patterns are consistent and worth adopting:
- **Quality gates wired into CI** with failure routing (GitHub Actions/GitLab CI):
  define gates, block or route on fail. (Maps to: promptfoo/our harness as a CI gate.)
- **Shadow mode first**: log violations without blocking until the rule's accuracy
  is validated, then enforce. **Directly applicable** — run any new gate (DINOv2,
  OCR, pairwise judge) in advisory/log-only mode against past results, calibrate
  thresholds on a 2nd+ candidate (we already banked "code gates need calibration"),
  then promote to hard gate.
- **Automated disagreement detection + difficulty assessment** (Scale AI): when
  judges/metrics disagree, escalate to human — exactly our verify-before-completion
  cross-vendor escalation.
- **Cascade cheap→expensive**: deterministic asserts first (free/instant), then
  metrics, then the VLM judge last (promptfoo's explicit three-tier model).

Sources: https://www.grepsr.com/blog/enterprise-ai-image-quality-compliance-qa/ ·
https://www.acceldata.io/blog/how-ai-generated-data-quality-rules-scale-pipeline-operations ·
https://www.promptfoo.dev/docs/configuration/expected-outputs/

---

## RANKED RECOMMENDATIONS

Design the loop as a **cheap→expensive cascade** (borrowed from §5), each stage a
gate, VLM last. Run every NEW gate in **shadow mode** until calibrated on ≥2
candidates, then promote.

### (i) Auto style/quality judge — **best pick: pairwise forced-choice VLM judge (GLM-4V default), candidate vs reference, order-swapped + consistency-gated**
Why: the one change with the biggest measured win (+25.4 pp on editing; α 0.86 vs
0.52; human-corr 0.36→0.86). GLM-4V beat GPT-5 on editing (87.2% vs 75.5%) and we
already have it via `glm-executor` → near-zero cost. Keeps our OBJECTIVE-gate /
AESTHETIC-advisory split (never auto-PASS taste).
Minimal adoption:
1. New `scripts/judge_pairwise.py`: inputs = candidate crop + reference crop
   (approved prior edit, or original pre-edit) + per-aspect rubric. Forced binary
   ("which better preserves watercolor style / is better-formed; no ties").
2. Call the judge twice with images A,B then B,A; **accept only if both agree**;
   on disagreement escalate to a 2nd vendor (Claude/GPT), then human.
3. Feed hi-DPI tiles (keep existing tiling). Log verdict to `results.jsonl`.

### (ii) Auto leftover-text / defect check — **best pick: PaddleOCR zero-text gate on the edited region** (hard gate), MediaPipe Hands as advisory
Why: removal-heals-text is a named recurring failure; OCR makes "is the TAXI gone?"
a deterministic 0/1 check. PaddleOCR is the accuracy leader (0.93), Apache-2.0,
local. Hands are harder on watercolor → advisory only.
Minimal adoption:
1. `scripts/ocr_gate.py`: PaddleOCR over the post-removal region; FAIL if any text
   box overlaps the removed-element bbox (or matches the removed string).
2. Keep `dup_detect.py` as the duplicate-count backstop behind the VLM count.
3. (optional) `mediapipe` finger-count as an advisory flag on hand crops.

### (iii) Change-nothing-else metric upgrade — **best pick: keep `--diffmask` hard byte-gate, ADD a DINOv2 patch-cosine leakage map outside the mask**
Why: pixel-diff feathering is blind to whole-crop repaint near the seam (banked:
81% drift undetected). DINOv2 is the verified winner for local edit detection
(64% vs CLIP 28%) and gives a per-patch outside-mask similarity map that catches
leakage the feather hides; masked DISTS inside the region confirms texture
preserved.
Minimal adoption:
1. `scripts/change_gate.py`: (a) existing byte-exact outside-mask check stays as
   the hard floor; (b) DINOv2 patch cosine(orig, edit) — FAIL if any outside-mask
   patch cosine drops below a calibrated threshold; (c) masked DISTS/SSIM inside
   region as report.
2. `pip install piq lpips` (Apache/BSD, MPS-ok) for the metric primitives;
   `torch.hub` DINOv2 (Apache-2.0).

### Adoption order (smallest safe path)
1. **(i) pairwise GLM judge** — biggest win, ~S/M, reuses existing subagent.
2. **(ii) PaddleOCR text gate** — closes a named failure deterministically, S/M.
3. **(iii) DINOv2 leakage map** — upgrades the gate we trust most, M.
4. Optionally wrap all three as **promptfoo** assertions for CI/regression so each
   confirmed-bad edit becomes a permanent test (MIT, calls our Python).
Run each in shadow mode, calibrate on ≥2 candidates, then promote to hard gate.

---

## Sources (verified this session)
- GenArena (pairwise vs pointwise, editing +25.4pp): https://arxiv.org/html/2602.06013 · https://arxiv.org/pdf/2602.06013
- MJ-Bench (multimodal reward-model judges): https://arxiv.org/pdf/2407.04842
- VLM-as-a-judge protocol survey: https://www.emergentmind.com/topics/vlm-as-a-judge-protocol · https://www.emergentmind.com/topics/vlm-as-a-judge
- promptfoo: https://github.com/promptfoo/promptfoo · https://www.promptfoo.dev/docs/configuration/expected-outputs/model-graded/ · https://www.promptfoo.dev/docs/configuration/expected-outputs/
- DeepEval multimodal: https://deepeval.com/docs/multimodal-metrics-image-coherence · https://deepeval.com/docs/introduction
- OpenAI image evals: https://developers.openai.com/cookbook/examples/multimodal/image_evals · https://github.com/openai/openai-cookbook/blob/main/examples/multimodal/image_evals.ipynb
- piq: https://github.com/photosynthesis-team/piq · https://piq.readthedocs.io/en/latest/modules.html
- LPIPS: https://github.com/richzhang/PerceptualSimilarity
- DISTS (torchmetrics): https://lightning.ai/docs/torchmetrics/stable/image/dists.html
- LPIPS (torchmetrics): https://lightning.ai/docs/torchmetrics/stable/image/learned_perceptual_image_patch_similarity.html
- DINOv2 vs CLIP similarity: https://medium.com/aimonks/clip-vs-dinov2-in-image-similarity-6fa5aa7ed8c6 · https://arxiv.org/html/2412.16334v1
- scikit-image SSIM: https://scikit-image.org/docs/stable/auto_examples/transform/plot_ssim.html
- ImageHash (pHash): https://github.com/JohannesBuchner/imagehash
- OCR comparison (Paddle/EasyOCR/Tesseract): https://intuitionlabs.ai/articles/non-llm-ocr-technologies · https://www.codesota.com/ocr/paddleocr-vs-tesseract
- PaddleOCR: https://github.com/PaddlePaddle/PaddleOCR
- MediaPipe Hands: https://mediapipe.readthedocs.io/en/latest/solutions/hands.html
- YOLO counting: https://roboflow.com/how-to-count/yolov8
- MPS fallback for torch metrics: https://tillcode.com/apple-silicon-pytorch-mps-setup-and-speed-expectations/
- Scale-QA patterns: https://www.grepsr.com/blog/enterprise-ai-image-quality-compliance-qa/ · https://www.acceldata.io/blog/how-ai-generated-data-quality-rules-scale-pipeline-operations
