#!/usr/bin/env python3
"""Build diagnostic scout-test inputs for the Berlin skyline method decision.

The output boards are intentionally cheap and non-final. They help decide which
kind of image-generation input is worth using before spending effort on a full
three-panel skyline render.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parent
ELEMENTS_PATH = ROOT / "outputs/generated/20260616-berlin-elements-v2.png"
TEMPLATE_PATH = ROOT / "outputs/reviews/checkpoint-1-template-preview/template.svg.png"
STYLE_REF_PATH = ROOT / "refs/WhatsApp Image 2026-06-16 at 01.31.54.jpeg"
HOTEL_REF_PATH = ROOT / "refs/Beisheim-Center_und_Potsdamer_Platz_in_Berlin_(2013)_(cropped).jpg"
STYLE_PACKET_PATH = ROOT / "style-packet/style-exemplar-sheet.png"
OUT_DIR = ROOT / "outputs/reviews/scout-tests"
PROMPT_DIR = ROOT / "prompts/scout-tests"
CHECKPOINT_PATH = ROOT / "checkpoints/scout-test-protocol.md"


def font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    choices = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for choice in choices:
        try:
            return ImageFont.truetype(choice, size)
        except OSError:
            pass
    return ImageFont.load_default()


F_TITLE = font(40, True)
F_HEAD = font(28, True)
F_BODY = font(22)
F_SMALL = font(17)


def transparent_crop(sheet: Image.Image, box: tuple[int, int, int, int], strength: float = 1.0) -> Image.Image:
    # Strengthen faint watercolor elements for map readability while keeping the
    # paper-white sheet background transparent.
    crop = sheet.crop(box).convert("RGB")
    crop = ImageEnhance.Contrast(crop).enhance(1.45)
    crop = ImageEnhance.Color(crop).enhance(1.08).convert("RGBA")
    pixels = crop.load()
    for y in range(crop.height):
        for x in range(crop.width):
            r, g, b, a = pixels[x, y]
            whiteness = min(r, g, b)
            if whiteness > 253:
                pixels[x, y] = (r, g, b, 0)
            elif whiteness > 248:
                pixels[x, y] = (r, g, b, int(a * strength * (253 - whiteness) / 5))
            else:
                pixels[x, y] = (r, g, b, min(255, int(a * strength)))
    alpha = crop.getchannel("A").filter(ImageFilter.GaussianBlur(0.35))
    crop.putalpha(alpha)
    return crop


def fit(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    copy = img.copy()
    copy.thumbnail(size, Image.Resampling.LANCZOS)
    return copy


def paste_fit(canvas: Image.Image, img: Image.Image, box: tuple[int, int, int, int]) -> None:
    x1, y1, x2, y2 = box
    fitted = fit(img, (x2 - x1, y2 - y1))
    canvas.alpha_composite(fitted, (x1 + (x2 - x1 - fitted.width) // 2, y1 + (y2 - y1 - fitted.height) // 2))


def template_overlay(width: int = 1660, alpha_scale: float = 1.15) -> Image.Image:
    template = Image.open(TEMPLATE_PATH).convert("RGBA")
    pix = template.load()
    xs: list[int] = []
    ys: list[int] = []
    for y in range(template.height):
        for x in range(template.width):
            r, g, b, a = pix[x, y]
            if a > 10 and min(r, g, b) < 245:
                xs.append(x)
                ys.append(y)
    x1 = max(0, min(xs) - 30)
    y1 = max(0, min(ys) - 30)
    x2 = min(template.width, max(xs) + 30)
    y2 = min(template.height, max(ys) + 30)
    crop = template.crop((x1, y1, x2, y2))
    crop = crop.resize((width, int(width * crop.height / crop.width)), Image.Resampling.LANCZOS)
    r, g, b, a = crop.split()
    a = a.point(lambda v: min(220, int(v * alpha_scale)))
    crop.putalpha(a)
    return crop


def production_outline_overlay(width: int = 1660, alpha: int = 150) -> Image.Image:
    """Return only the dark production outlines from the template preview.

    This avoids giving image-generation scouts a strong red/yellow/green dashed
    construction pattern to accidentally reproduce.
    """
    template = Image.open(TEMPLATE_PATH).convert("RGBA")
    pix = template.load()
    xs: list[int] = []
    ys: list[int] = []
    for y in range(template.height):
        for x in range(template.width):
            r, g, b, a = pix[x, y]
            if a > 10 and min(r, g, b) < 245:
                xs.append(x)
                ys.append(y)
    x1 = max(0, min(xs) - 30)
    y1 = max(0, min(ys) - 30)
    x2 = min(template.width, max(xs) + 30)
    y2 = min(template.height, max(ys) + 30)
    crop = template.crop((x1, y1, x2, y2))
    crop = crop.resize((width, int(width * crop.height / crop.width)), Image.Resampling.LANCZOS)
    out = Image.new("RGBA", crop.size, (0, 0, 0, 0))
    src = crop.load()
    dst = out.load()
    for y in range(crop.height):
        for x in range(crop.width):
            r, g, b, a = src[x, y]
            is_dark_neutral = a > 8 and max(r, g, b) < 155 and abs(r - g) < 35 and abs(g - b) < 35
            if is_dark_neutral:
                dst[x, y] = (35, 35, 33, min(alpha, int(a * 1.8)))
    return out


def draw_top_contour(draw: ImageDraw.ImageDraw, pts: list[tuple[int, int]], color: tuple[int, int, int, int]) -> None:
    draw.line(pts, fill=color, width=7, joint="curve")


def write_header(draw: ImageDraw.ImageDraw, title: str, subtitle: str) -> None:
    draw.text((42, 26), title, font=F_TITLE, fill=(28, 30, 28))
    draw.text((44, 80), subtitle, font=F_BODY, fill=(70, 72, 68))


def build_wireframe_map() -> Path:
    canvas = Image.new("RGBA", (1800, 1220), (255, 255, 255, 255))
    draw = ImageDraw.Draw(canvas, "RGBA")
    write_header(
        draw,
        "Scout A: Wireframe / Layout Map",
        "Tests whether a schematic map alone can control landmark placement and template constraints.",
    )

    ox, oy = 82, 175
    overlay = template_overlay(alpha_scale=1.55)
    canvas.alpha_composite(overlay, (ox, oy))

    # Strong simple blocks: useful if a model follows graphic planning, useless
    # if it needs pictorial reference.
    shapes = [
        ("TV", (140, 355, 240, 820), (80, 140, 205, 96)),
        ("Gate", (245, 585, 505, 820), (212, 175, 80, 104)),
        ("Dom", (595, 350, 860, 790), (92, 170, 145, 104)),
        ("Church", (875, 330, 1068, 790), (170, 125, 80, 104)),
        ("Hotel", (1290, 320, 1620, 835), (150, 150, 150, 112)),
        ("Bridge arch", (620, 685, 1235, 865), (190, 112, 70, 112)),
        ("U-Bahn run-through", (100, 805, 1580, 910), (235, 188, 42, 120)),
    ]
    for label, box, fill in shapes:
        x1, y1, x2, y2 = box
        draw.rounded_rectangle((x1, y1, x2, y2), radius=18, fill=fill, outline=(50, 55, 55, 180), width=3)
        draw.text((x1 + 14, y1 + 14), label, font=F_HEAD, fill=(25, 28, 26, 230))
    draw.arc((600, 655, 1260, 1045), start=190, end=350, fill=(104, 70, 40, 220), width=10)
    draw_top_contour(
        draw,
        [(120, 300), (205, 245), (330, 380), (610, 315), (780, 245), (1010, 340), (1300, 312), (1640, 285)],
        (52, 145, 68, 210),
    )
    draw.text((54, 1136), "Generation input: schematic only. Labels are intentional review aids; prompt says not to reproduce text.", font=F_SMALL, fill=(80, 80, 76))
    out = OUT_DIR / "scout-a-wireframe-layout-map.png"
    canvas.convert("RGB").save(out, quality=95)
    return out


def build_rough_whole_set_map() -> Path:
    sheet = Image.open(ELEMENTS_PATH).convert("RGBA")
    parts = {
        "tv": transparent_crop(sheet, (40, 25, 165, 610), 1.35),
        "gate": transparent_crop(sheet, (185, 165, 625, 595), 1.35),
        "dom": transparent_crop(sheet, (610, 110, 960, 615), 1.28),
        "church": transparent_crop(sheet, (945, 105, 1155, 625), 1.28),
        "hotel": transparent_crop(sheet, (1160, 80, 1515, 625), 1.35),
        "train": transparent_crop(sheet, (55, 630, 825, 725), 1.38),
        "rail": transparent_crop(sheet, (55, 730, 835, 790), 1.25),
        "stone": transparent_crop(sheet, (55, 800, 835, 875), 1.15),
        "water": transparent_crop(sheet, (55, 890, 850, 990), 1.12),
        "bridge": transparent_crop(sheet, (875, 610, 1485, 885), 1.28),
    }

    canvas = Image.new("RGBA", (1800, 1220), (255, 255, 255, 255))
    draw = ImageDraw.Draw(canvas, "RGBA")
    write_header(
        draw,
        "Scout B: Rough Whole-Set Composition Map",
        "Tests whether a pictorial map can be repainted into one cohesive watercolor scene.",
    )

    # A stronger B+C hybrid than the earlier faint options.
    placements = {
        "tv": (105, 250, 245, 805),
        "gate": (215, 505, 555, 810),
        "dom": (555, 235, 950, 740),
        "church": (895, 250, 1118, 745),
        "hotel": (1265, 250, 1685, 845),
        "train": (92, 800, 1515, 910),
        "rail": (88, 882, 1545, 940),
        "stone": (86, 936, 1550, 998),
        "water": (510, 954, 1550, 1058),
        "bridge": (575, 638, 1290, 880),
    }
    for key in ["water", "stone", "rail", "train", "bridge", "tv", "gate", "dom", "church", "hotel"]:
        paste_fit(canvas, parts[key], placements[key])

    draw = ImageDraw.Draw(canvas, "RGBA")
    draw_top_contour(
        draw,
        [(120, 300), (205, 245), (330, 380), (610, 292), (780, 236), (1012, 335), (1305, 315), (1645, 278)],
        (52, 145, 68, 190),
    )
    overlay = production_outline_overlay(alpha=175)
    canvas.alpha_composite(overlay, (82, 175))
    draw.text((54, 1136), "Generation input: repaint this as one illustration. Do not paste, trace, or preserve sprite edges.", font=F_SMALL, fill=(80, 80, 76))
    out = OUT_DIR / "scout-b-rough-whole-set-map.png"
    canvas.convert("RGB").save(out, quality=95)
    return out


def build_seam_safe_whole_set_map() -> Path:
    sheet = Image.open(ELEMENTS_PATH).convert("RGBA")
    parts = {
        "tv": transparent_crop(sheet, (40, 25, 165, 610), 1.35),
        "gate": transparent_crop(sheet, (185, 165, 625, 595), 1.35),
        "dom": transparent_crop(sheet, (610, 110, 960, 615), 1.25),
        "church": transparent_crop(sheet, (945, 105, 1155, 625), 1.25),
        "hotel": transparent_crop(sheet, (1160, 80, 1515, 625), 1.35),
        "train": transparent_crop(sheet, (55, 630, 825, 725), 1.3),
        "rail": transparent_crop(sheet, (55, 730, 835, 790), 1.2),
        "stone": transparent_crop(sheet, (55, 800, 835, 875), 1.1),
        "water": transparent_crop(sheet, (55, 890, 850, 990), 1.1),
        "bridge": transparent_crop(sheet, (875, 610, 1485, 885), 1.25),
    }

    canvas = Image.new("RGBA", (1800, 1220), (255, 255, 255, 255))
    draw = ImageDraw.Draw(canvas, "RGBA")
    write_header(
        draw,
        "Scout B2: Seam-Safe Rough Composition Map",
        "Targets the repeated failure: Brandenburg Gate must not be cropped by the left seam.",
    )

    placements = {
        "tv": (100, 250, 232, 805),
        "gate": (215, 520, 485, 800),
        "dom": (610, 235, 970, 740),
        "church": (910, 250, 1120, 745),
        "hotel": (1275, 250, 1688, 845),
        "train": (92, 805, 1515, 910),
        "rail": (88, 888, 1545, 940),
        "stone": (86, 940, 1550, 1000),
        "water": (510, 956, 1550, 1058),
        "bridge": (600, 640, 1305, 880),
    }
    for key in ["water", "stone", "rail", "train", "bridge", "tv", "gate", "dom", "church", "hotel"]:
        paste_fit(canvas, parts[key], placements[key])

    draw = ImageDraw.Draw(canvas, "RGBA")
    # Pale seam-clearance bands, intentionally quiet enough not to become final
    # art but visible enough to mark "do not place focal features here."
    for x1, x2 in [(500, 585), (1325, 1390)]:
        draw.rectangle((x1, 230, x2, 1030), fill=(255, 255, 255, 100))
        draw.line((x1, 230, x1, 1030), fill=(120, 120, 116, 105), width=2)
        draw.line((x2, 230, x2, 1030), fill=(120, 120, 116, 105), width=2)
    draw_top_contour(
        draw,
        [(120, 300), (205, 245), (330, 382), (620, 292), (790, 236), (1015, 335), (1310, 315), (1645, 278)],
        (52, 145, 68, 190),
    )
    overlay = production_outline_overlay(alpha=175)
    canvas.alpha_composite(overlay, (82, 175))
    draw.text((54, 1136), "Generation input: seam-safe map. Keep gate fully left of the left-center seam.", font=F_SMALL, fill=(80, 80, 76))
    out = OUT_DIR / "scout-b2-seam-safe-map.png"
    canvas.convert("RGB").save(out, quality=95)
    return out


def build_direct_reference_board() -> Path:
    canvas = Image.new("RGBA", (1800, 1220), (255, 255, 255, 255))
    draw = ImageDraw.Draw(canvas, "RGBA")
    write_header(
        draw,
        "Scout C: Direct Whole-Scene From References",
        "Tests whether references + template instructions are enough without a composition map.",
    )

    template = template_overlay(width=1220, alpha_scale=1.45)
    canvas.alpha_composite(template, (505, 230))

    style_ref = Image.open(STYLE_REF_PATH).convert("RGBA")
    hotel_ref = Image.open(HOTEL_REF_PATH).convert("RGBA")
    style_packet = Image.open(STYLE_PACKET_PATH).convert("RGBA")
    style_ref.thumbnail((430, 280), Image.Resampling.LANCZOS)
    hotel_ref.thumbnail((205, 280), Image.Resampling.LANCZOS)
    style_packet.thumbnail((430, 500), Image.Resampling.LANCZOS)

    draw.rounded_rectangle((55, 162, 470, 470), radius=12, fill=(255, 255, 255, 245), outline=(198, 198, 190), width=2)
    draw.rounded_rectangle((55, 498, 470, 862), radius=12, fill=(255, 255, 255, 245), outline=(198, 198, 190), width=2)
    draw.rounded_rectangle((55, 890, 470, 1120), radius=12, fill=(255, 255, 255, 245), outline=(198, 198, 190), width=2)

    canvas.alpha_composite(style_ref, (70, 185))
    canvas.alpha_composite(hotel_ref, (175, 520))
    canvas.alpha_composite(style_packet.crop((0, 0, style_packet.width, min(style_packet.height, 220))), (70, 910))
    draw.text((70, 430), "Style / palette / existing Berlin render", font=F_SMALL, fill=(60, 62, 58))
    draw.text((70, 830), "Hotel mass reference: include lower podium/wing", font=F_SMALL, fill=(60, 62, 58))
    draw.text((70, 1100), "Style packet excerpts", font=F_SMALL, fill=(60, 62, 58))
    draw.text((540, 1082), "Generation input: template + references only. No landmark placement map.", font=F_SMALL, fill=(80, 80, 76))

    out = OUT_DIR / "scout-c-direct-reference-board.png"
    canvas.convert("RGB").save(out, quality=95)
    return out


def build_contact_sheet(paths: list[Path]) -> Path:
    sheet = Image.new("RGB", (1240, 3260), (248, 248, 246))
    draw = ImageDraw.Draw(sheet)
    y = 34
    for path in paths:
        img = Image.open(path).convert("RGB")
        img.thumbnail((1160, 705), Image.Resampling.LANCZOS)
        draw.text((42, y), path.stem, font=F_HEAD, fill=(32, 34, 31))
        sheet.paste(img, (40, y + 44))
        y += 800
    out = OUT_DIR / "scout-inputs-contact-sheet.png"
    sheet.save(out, quality=95)
    return out


def write_prompts(paths: dict[str, Path]) -> None:
    PROMPT_DIR.mkdir(parents=True, exist_ok=True)
    (PROMPT_DIR / "scout-a-wireframe-obedience.md").write_text(
        f"""# Scout A - Wireframe Obedience

Attachment/input board:
- `{paths['a']}`

Goal:
Create a rough, low-detail watercolor/pencil Berlin skyline thumbnail for the
three-panel Screenery skyline template using the attached schematic map as the
placement authority. This is not final art.

Prompt emphasis:
- Follow the schematic placement exactly enough to prove obedience.
- Left narrow panel: Fernsehturm plus Brandenburg Gate, whole and unsplit.
- Center door panel: Berliner Dom plus Kaiser Wilhelm Memorial Church tower,
  with the bridge/viaduct arch echoing the saloon-door flap arch.
- Right narrow panel: Ritz-Carlton / Beisheim / Potsdamer Platz high-rise with
  its lower podium/wing visible.
- Low yellow U-Bahn, rail, stone, and water/ground band may run through panels
  as quiet infrastructure.
- Keep sky and removable background white or pale paper-white.
- Do not reproduce labels, colored blocks, dashed guides, or construction text.

Pass if:
- The panel allocation is obeyed.
- Major landmarks are whole within their panels.
- The bridge/arch and low U-Bahn premise survive.

Fail if:
- The result becomes a generic skyline, reproduces labels/guides, or ignores
  red/seam safety.
""",
        encoding="utf-8",
    )
    (PROMPT_DIR / "scout-b-rough-map-redraw.md").write_text(
        f"""# Scout B - Rough Whole-Set Redraw

Attachment/input board:
- `{paths['b']}`

Goal:
Use the attached rough map only as composition evidence, then repaint the whole
Berlin skyline as one cohesive watercolor/pencil illustration in the style of
the source render. This is a scout thumbnail, not production art.

Prompt emphasis:
- Do not paste, crop, trace, or preserve the element sheet pixels.
- Preserve the B+C hybrid composition: continuous low U-Bahn, central
  bridge/viaduct arch, Dom/church mass in the center, and full hotel with lower
  podium on the right.
- Make the landmarks feel drawn in the same hand, with shared light, line
  weight, paper texture, muted pastel palette, and white/paper-white sky.
- Keep recognizable features away from panel seams, red separators, red
  rectangles, and door split areas.
- Treat bridge, rail, water, stone, and train body as run-through
  infrastructure; do not split focal landmarks.

Pass if:
- The output reads as one coherent watercolor scene, not assembled sprites.
- It keeps all approved landmark identities and the hotel lower section.
- The bridge/arch and U-Bahn run-through remain useful for the template.

Fail if:
- It looks collaged, drops landmark identity, or cannot keep focal details away
  from production cuts.
""",
        encoding="utf-8",
    )
    (PROMPT_DIR / "scout-c-direct-whole-scene.md").write_text(
        f"""# Scout C - Direct Whole-Scene

Attachment/input board:
- `{paths['c']}`

Goal:
Generate a rough whole-set Berlin skyline directly from the template and
references, without using a placement map. This tests whether direct prompting
has enough control.

Prompt emphasis:
- Use the three-panel Screenery skyline template structure shown in the board.
- Match the watercolor/pencil style and muted Berlin palette of the existing
  render reference.
- Include: Fernsehturm, Brandenburg Gate, Berliner Dom, Kaiser Wilhelm Memorial
  Church tower, Ritz-Carlton / Beisheim / Potsdamer Platz high-rise with lower
  podium/wing, Oberbaum-inspired bridge/viaduct arch, and yellow Berlin U-Bahn.
- Keep buildings/landmarks whole within their physical panels.
- Use white/paper-white sky; no blue sky fill.
- Avoid copying the old four-panel render layout literally; adapt it to the
  three-panel saloon-door template.

Pass if:
- It produces a coherent composition without needing a map.
- It includes the required landmark roster with acceptable placement.
- It respects the saloon arch and run-through U-Bahn premise.

Fail if:
- It drifts into a generic Berlin postcard, omits landmarks, crops focal
  features, or ignores the template structure.
""",
        encoding="utf-8",
    )
    (PROMPT_DIR / "scout-b2-seam-safe-redraw.md").write_text(
        f"""# Scout B2 - Seam-Safe Rough Whole-Set Redraw

Attachment/input board:
- `{paths['b2']}`

Goal:
Repeat the rough-map redraw test, but with the primary failure corrected in the
input map: the Brandenburg Gate is smaller and clearly left of the left-center
panel seam.

Prompt emphasis:
- Treat this as a seam-safety test, not final art.
- Repaint as one cohesive watercolor/pencil scene.
- Keep the entire Brandenburg Gate and Quadriga inside the left narrow panel,
  with visible white/quiet clearance before the left-center seam.
- Keep train doors/windows away from seams; plain yellow train body may cross.
- Preserve the central bridge/viaduct arch, Berliner Dom, Kaiser Wilhelm tower,
  full hotel lower podium/wing, white sky, rail/stone/water run-through band.
- Do not reproduce seam-clearance marks, labels, construction lines, or guide
  artifacts.

Pass if:
- Gate is no longer cropped by the left seam.
- Whole-scene watercolor cohesion remains close to Scout B/C.
- The saloon arch and U-Bahn run-through premise survive.

Fail if:
- Gate or Quadriga still touch/cross the seam, or the prompt over-corrects into
  a weak/disconnected composition.
""",
        encoding="utf-8",
    )
    (PROMPT_DIR / "scout-judge-rubric.md").write_text(
        """# Berlin Skyline Scout Judge Rubric

Score each scout from 0 to 2 in each category.

1. Template obedience:
- 2: three physical panels and saloon-door arch are clear.
- 1: rough panel awareness but drift/ambiguity.
- 0: generic rectangle or wrong structure.

2. Landmark roster:
- 2: all required Berlin landmarks present and recognizable.
- 1: most are present but one important identity is weak.
- 0: major omissions or generic skyline.

3. No-crop premise:
- 2: focal buildings/features are whole and away from seam/red-risk zones.
- 1: only minor risk or ambiguous details.
- 0: split/cropped focal landmarks or features.

4. Cohesion/style:
- 2: one watercolor/pencil scene in the source render family.
- 1: acceptable rough style but assembled or uneven.
- 0: collage/procedural/vector/photo style.

5. Useful next-step signal:
- 2: clearly unlocks or rejects a method.
- 1: some signal, still needs another scout.
- 0: too ambiguous to guide the method choice.

Decision rule:
- Prefer B when B scores highest or ties C while being more controllable.
- Prefer C only if it matches B on template obedience and beats it on cohesion.
- Prefer A only if it beats B/C on obedience without reproducing schematic
  artifacts; otherwise A remains a diagnostic negative control.
""",
        encoding="utf-8",
    )


def write_protocol(paths: dict[str, Path]) -> None:
    CHECKPOINT_PATH.write_text(
        f"""# Berlin Skyline Scout-Test Protocol

Date: 2026-06-16

Purpose: decide whether the next Berlin skyline generation should proceed from
(A) a wireframe/layout map, (B) a rough whole-set composition map, or (C) direct
whole-scene generation from the references and template.

## Inputs

- Approved element sheet: `outputs/generated/20260616-berlin-elements-v2.png`
- Source template: `source/template.svg`
- Style render reference: `refs/WhatsApp Image 2026-06-16 at 01.31.54.jpeg`
- Hotel reference: `refs/Beisheim-Center_und_Potsdamer_Platz_in_Berlin_(2013)_(cropped).jpg`
- Style packet: `style-packet/`

## Scout Inputs

- A wireframe/layout map: `{paths['a']}`
- B rough whole-set composition map: `{paths['b']}`
- C direct reference/template board: `{paths['c']}`
- B2 seam-safe rough map: `{paths['b2']}`
- Review contact sheet: `{paths['contact']}`

## Test A: Wireframe/Layout Map

Question: can a schematic map alone control landmark placement and template
rules well enough for generation?

Pass: panel allocation, saloon arch, low U-Bahn, white sky, and whole landmarks
survive without copying labels/guides.

Fail: model invents generic skyline, reproduces construction marks, or ignores
red/seam safety.

Decision unlocked: use wireframe maps only if obedience is excellent; otherwise
use them only as internal planning artifacts.

## Test B: Rough Whole-Set Composition Map

Question: can a pictorial B+C hybrid map be repainted into one cohesive
watercolor scene rather than a pasted element collage?

Pass: one coherent watercolor/pencil Berlin illustration, all landmarks
recognizable, full hotel lower podium/wing, central bridge/arch and U-Bahn
run-through retained.

Fail: pasted/assembled feel, landmark omissions, or focal details still collide
with production cuts.

Decision unlocked: if B passes, proceed with rough composition map -> whole-set
redraw -> SVG export/verification.

## Test C: Direct Whole-Scene

Question: can direct prompting from references/template control both composition
and style without a map?

Pass: cohesive and complete composition that respects the template as well as B.

Fail: generic Berlin postcard, omissions, cropping, or weak saloon-door/use of
the three-panel template.

Decision unlocked: choose direct generation only if it matches B on template
obedience and beats B on visual cohesion.

## Test B2: Seam-Safe Rough Map

Question: after the first smoke tests, can the repeated Brandenburg Gate seam
crop be prevented by changing the composition map before a full render?

Pass: the entire Brandenburg Gate and Quadriga stay inside the left narrow
panel with quiet clearance before the seam, while the whole-set watercolor
cohesion remains strong.

Fail: the model still crops the gate or the seam-safe layout becomes too weak
or disconnected.

Decision unlocked: proceed only if the next full-generation map is seam-safe;
otherwise redesign the left panel allocation before rendering.

## Judge Rubric

Use `prompts/scout-tests/scout-judge-rubric.md`. Do not promote any scout to a
final candidate. A scout only decides the next method.

## Preliminary Method Expectation

The earlier placement options were too similar and too faint to decide a method.
Scout B is the current expected winner because it gives the model pictorial
composition evidence while still asking for a whole-scene repaint. Scout C is
the control for whether the map is unnecessary. Scout A is mostly a negative
control for whether pure schematics are useful.
""",
        encoding="utf-8",
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    paths = {
        "a": build_wireframe_map(),
        "b": build_rough_whole_set_map(),
        "b2": build_seam_safe_whole_set_map(),
        "c": build_direct_reference_board(),
    }
    paths["contact"] = build_contact_sheet([paths["a"], paths["b"], paths["b2"], paths["c"]])
    write_prompts(paths)
    write_protocol(paths)
    for key in ["a", "b", "c", "contact"]:
        print(f"{key}: {paths[key]}")
    print(f"protocol: {CHECKPOINT_PATH}")
    print(f"prompts: {PROMPT_DIR}")


if __name__ == "__main__":
    main()
