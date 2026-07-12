# OpenAI transparency and alpha-safe upscale scout

The two OpenAI subscription calls did not return genuine transparency. Both
were actual opaque RGB PNGs depicting a checkerboard. They also recomposed
details, so neither is usable even as a geometry-locked source.

The reusable implementation is
`tasks/double-marine-bed-wrapper-batch/alpha_aware_upscale.py`. Its preferred
`split` method requires an explicit acknowledgement that the input is straight
RGBA with decontaminated foreground RGB. It extends foreground color only under
alpha-zero pixels, runs RealESRGAN x4 on RGB, applies a Lanczos x2 finish to RGB,
resamples source alpha independently to x8 with Lanczos, and recombines straight
RGBA. It rejects `finals` paths.

Direct ncnn RGBA is measurable but not the default: its hidden alpha policy is
undocumented. The black/white two-plate method is mathematically valid for an
identical linear upscaler, but RealESRGAN is nonlinear. In the live test,
foreground texture leaked into recovered alpha and edge errors were materially
higher. It is implemented for controlled opaque-only engines and comparison,
not recommended with RealESRGAN.

Evidence is under the product candidate folder
`Images/candidates/openai-transparent-image14/`. The r110 art was used only as a
240x240 controlled crop and remains rejected art; no production final or full
r110 upscale was created.

Preferred command:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv-gen/bin/python -B \
  tasks/double-marine-bed-wrapper-batch/alpha_aware_upscale.py INPUT.png OUTPUT.png \
  --method split --ack-decontaminated-straight-rgb
```

Run the gate:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv-gen/bin/python -B \
  tasks/double-marine-bed-wrapper-batch/tests/test_alpha_aware_upscale.py
```
