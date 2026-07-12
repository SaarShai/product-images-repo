# regen-v12 — regenerate source for trivial BG removal

## Question
Does regenerating the source with a keyable/transparent BG make matting trivial?

## Answer
**Partially yes.** Magenta-chroma regen (attempt1) makes outer BG removal trivial via simple color key.
Native RGBA was **not** produced by OpenAI image tool (both attempts returned opaque RGB).
Pure-white regen (attempt2) recreated the original failure mode (pale paint ≈ paper).

## Source attachment
- Lower-res original found: `14-source-original-941x1672.png` (941×1672) from product `images/ChatGPT Image Jul 7, 2026, 11_22_35 AM.png`
- x4 (3764×6688) kept as composition reference only (too large to attach)

## Attempts (2 max)
| # | Prompt target | Result | Verdict |
|---|---|---|---|
| 1 | transparent > white > magenta | Solid magenta chroma RGB | **BEST** — keyable |
| 2 | transparent or pure #FFF hard edges | Near-white paper (~249) | FAIL — same pale≈paper |

## Best outputs
- `14-regen-v12-best-rgba.png` — attempt1 keyed + rim despill (RGBA)
- `14-regen-v12-attempt1-raw.png` — raw magenta plate
- `14-regen-v12-attempt2-raw.png` — white-paper plate (control fail)

## Review boards
`REVIEW/image14-bg/USER_REVIEW/23-regen-v12-*`

## Remaining issues
- Not native transparent; requires chroma key
- Magenta key can tint purple coral / rim if despill is weak; purple subject paint is near key hue
- Soft watercolor tips/bubbles still need careful soft-alpha (hard key clips them)
- Composition is close but not pixel-identical to original (img2img drift)
- Resolution is original-scale (~941×1671), not x4

## Next step if still imperfect
Prefer regenerating again with **green screen (#00FF00)** (far from purple/pink coral hues) or a tool that truly emits RGBA; or upscale the keyed magenta plate after keying.
