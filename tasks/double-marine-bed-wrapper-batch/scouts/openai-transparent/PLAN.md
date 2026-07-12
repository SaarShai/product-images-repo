# OpenAI-native transparency and alpha-safe x8 scout

## Goal and scope

Test whether the subscription OpenAI image route can return a genuine,
composition-faithful transparent PNG for native image 14, then measure three x8
alpha-handling routes. Outputs remain candidates. No final is written.

Inputs:

- authoritative source: `ChatGPT Image Jul 7, 2026, 11_22_35 AM.png`
  (`941x1672`, RGB, SHA256
  `925c34a39a0e2b5a09ad92ba39dace87f652bcc90ff8e063e2a6f644e735df9d`)
- fallback controlled fixture only:
  `bg-assisted-v1/image14/assisted-r110-vitmatte/image14-assisted-r110-rgba.png`
  (`941x1672`, RGBA, 27.83% soft alpha; visually haloed and not accepted art)
- RealESRGAN ncnn binary:
  `tasks/marine-pod-upscale/tools/realesrgan-full/realesrgan-ncnn-vulkan`

Output root:

`.../images/Images/candidates/openai-transparent-image14/`

## Style and reference-input contract (frozen before calls)

The source is flat artwork, not a product photo. It is the sole image input and
has these roles: composition, exact object/layout inventory, watercolor medium,
palette, edge language, and detail density. Borrow everything except its white
paper/background. Do not attach prior magenta regeneration, masks, checker
previews, or substrate imagery.

Style:

> professional children's picture-book illustration; hand-painted watercolor;
> soft translucent washes; gentle pigment granulation; delicate controlled
> edges; muted pastel coral, purple, orange, sage-green and blue palette; soft
> ambient light; dense but airy marine detail.

Anti-style/content drift:

> no photorealism, 3D, felt/fabric, new/missing objects, crop/reframe,
> composition change, recoloring, text, white matte, halo.

Call 1 is a strict edit: change only paper/background into genuine PNG alpha,
including enclosed negative spaces. Call 2 is allowed only if call 1 is opaque
or structurally poor; it regenerates the same locked scene natively on alpha.
Both use `scripts/subgen.py --provider openai -i <original> --retries 1`.

## Alpha-upscale experiment

1. Probe ncnn once with a tiny synthetic straight-RGBA fixture to learn actual
   channel behavior.
2. Preferred split route: require explicit decontaminated-straight-RGB
   acknowledgement; extend foreground color beneath alpha-zero pixels; upscale
   RGB x4 with ncnn; Lanczos-upsample RGB x2 and alpha independently x8;
   recombine straight RGBA.
3. Direct route: record what ncnn does with RGBA, without assuming it is safe.
4. Two-plate route: composite over black and white, apply identical upscaling,
   recover alpha/premultiplied foreground jointly, and avoid division below a
   guarded alpha floor. Quantify nonlinear-SR error.
5. Compare with synthetic known alpha and controlled real crop boards on black,
   white, gray, and magenta. A single colored plate is intentionally excluded.

## Gates

- OpenAI results are inspected from actual PNG mode/alpha, dimensions, and
  side-by-side vision; generated prose is not evidence.
- Source hash remains unchanged.
- CLI rejects any output path containing an `Images/finals` component and
  requires explicit decontaminated-input acknowledgement for split/direct.
- Exact x8 dimensions; RGBA; nondegenerate soft alpha; finite bounded hidden
  RGB; known-alpha MAE; black/magenta halo error; white/black recomposition.
- Command construction is unit-tested without running the binary.
- New gates have negative tests.
- `/root` is the separate visual/code verifier.

```loop
name: openai-transparent-and-alpha-upscale-fixed-scout
topology: closed · inner · single
generator: scout_openai_transparent_writer
verifier: root_separate_verifier
gate: PYTHONDONTWRITEBYTECODE=1 .venv-gen/bin/python -B tasks/double-marine-bed-wrapper-batch/tests/test_alpha_aware_upscale.py
stop: done after at most two actual OpenAI renders, one ncnn RGBA probe, fresh tests, metrics, and vision boards; blocked on authentication or both no-image calls
budget: max_iterations=2 image calls; max_wallclock=90m
```

The loop budget counts actual image-render processes. Wrapper retries are set to
one, so the wrapper cannot silently exceed the two-call ceiling.

## Recorded verdict

- Both allowed OpenAI renders produced opaque RGB with a baked checkerboard,
  not transparency. Call 1 was `940x1673`; call 2 was `941x1672`. Both also
  changed source detail; neither is accepted.
- Codex 0.144 writes `exec-*.png`, while `scripts/subgen.py` discovers only
  `ig_*.png`. The wrapper falsely reported no image; exact session artifacts
  were recovered and validated. No third render was made.
- The one ncnn RGBA probe returned RGBA `256x256`; its internal alpha is closest
  to bicubic (`0.329/255` MAE, maximum 6), but that behavior is undocumented.
- Split RGB/alpha is preferred. Direct ncnn alpha is close on the synthetic
  fixture (`0.414/255` MAE) but delegates alpha policy to the binary. Two-plate
  recovery is rejected for nonlinear RealESRGAN: synthetic alpha MAE is
  `2.465/255` (maximum 49); on the r110 crop its soft-edge black/magenta errors
  are `15.31/11.12`, and subject texture visibly leaks into recovered alpha.
- r110 remained a rejected controlled fixture. No full-image final was made.
