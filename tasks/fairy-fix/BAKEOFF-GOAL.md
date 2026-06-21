# GOAL — bottom-left fairy bake-off: best engine + recipe (fal-focused) + local comparison

Same fairy (door-v5 BL, bbox 160,2660,480,3110; ctx crop 60,2560,720,3300). "Change nothing else" gate = compose_fairy.py outside_max_delta==0 (mandatory). Reimagine: cute children's-book fairy, big head/eyes, small nose, MODEST dress (covered shoulders+legs), same watercolor style/palette/soft outlines; fix face/hands(5 fingers)/toes.

## Independent pieces (fan out)
1. **fal Kontext variants** (my rec) — prompt/guidance/hand-focus combos.
2. **fal Fill variants** — masked inpaint combos.
3. **fal OTHER models** — survey fal catalog (Qwen-Image-Edit, Flux.2-pro/edit, SeedEdit, nano-banana, recraft, upscalers) + run the promising ones.
4. **LOCAL** — localgen.py (SDXL-inpaint + watercolor LoRA + IP-Adapter) + mflux (flux2-edit/kontext/fill/qwen-edit) for a free comparison vs fal. (serial on MPS)
5. **Judge + synthesize** — composite all, gate, Claude+GLM judge on hi-DPI crops, present ALL full-size with filename links.

## Rules
- ALL candidates composited + gate-checked (outside_max_delta==0) before judging.
- Present every candidate full-size, link text = filename.
- Engines so far ranked: Flux Kontext (fal) > Fill ≈ OpenAI > nano. Try to beat Kontext.
- Hands remain the open weakness → hand-focus prompt + (later) targeted hand pass.

## done means
- [ ] ≥3 new fal Kontext/Fill variants + ≥2 other fal models tried, composited, judged
- [ ] ≥1 local (SDXL or mflux-flux2) candidate, composited, judged
- [ ] ranked comparison presented full-size w/ filename links + cost notes
- [ ] recommendation for engine+recipe to apply to the other 4 fairies
