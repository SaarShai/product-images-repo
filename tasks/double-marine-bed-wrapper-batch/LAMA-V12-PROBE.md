# LaMa v12 probe (Fork 1) — image14

Date: 2026-07-09  
Engine: `simple-lama-inpainting` big-lama.pt on **MPS** (`map_location=cpu` then `.to(mps)`).

## Method

1. Erase mask = `~border_connected(paperish)`, dilated 3px, **outer paper locked**.
2. LaMa at max-side 2048 (1152×2048), upsample paper, restore original outside erase.
3. Delta soft alpha `|src−paper|` → RGBA + unblend on partials.
4. Tag **b** corrective: reuse tag-a paper; raise soft thr; kill near-paper + FG rim.

## Results

| tag | opaque% | cut00 | fringe_pink | enclosed_tri |
|-----|---------|-------|-------------|--------------|
| a   | 40.7    | **FAIL** white rim | **FAIL** white rim | mixed (holes punched, rim remains) |
| b   | 36.9    | **FAIL** white rim (slightly thinner, still present) | **FAIL** white rim | still rimmy |

LaMa **did run** (~1.7s MPS) and produced a paper estimate, but under a ~48% erase mask it **ghosts pale washes** instead of blank paper. Delta then keeps paper-tinted edge pixels → same white-rim class as Telea/Codex.

## Artifacts

- `Images/candidates/image14-research/fusion-lama-v12/`
- Review: `REVIEW/image14-bg/USER_REVIEW/21-lama-v12-{a,b}-*`
- Scripts: `fusion_lama_v12_mps.py`, `fusion_lama_v12_retry_b.py`
- Drive mirror: product `Images/candidates/image14-research/fusion-lama-v12/`

## Verdict

**FAIL** as complete BG solution. Real LaMa is installed and runnable; generative paper under large watercolor erase is still too weak for clean delta at cut00/fringe. Do not treat as production. Next options remain semi-auto sure-FG/BG or source-side transparent BG — not more flood/rim family.
