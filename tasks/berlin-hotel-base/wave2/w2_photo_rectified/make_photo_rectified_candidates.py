#!/usr/bin/env python3
"""Build photo-rectified Berlin hotel-base candidates for wave 2.

Reads the shared source/reference files, but writes only next to this script.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent

SRC = ROOT / "work" / "src.png"
CAHILL2 = ROOT / "refs" / "ritz_cahill2.jpg"
STREET = ROOT / "refs" / "ritz_streetlevel.png"

BOX = (3162, 2582, 4082, 2845)
ZOOM_BOX = (3050, 2480, 4120, 2900)
W, H = BOX[2] - BOX[0], BOX[3] - BOX[1]


def pil_rgb(path: Path) -> Image.Image:
    return Image.open(path).convert("RGB")


def to_np(im: Image.Image) -> np.ndarray:
    return np.asarray(im.convert("RGB"), dtype=np.uint8)


def from_np(arr: np.ndarray) -> Image.Image:
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")


def rectify(path: Path, quad: list[tuple[float, float]], size: tuple[int, int]) -> np.ndarray:
    src = cv2.cvtColor(cv2.imread(str(path), cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)
    src_pts = np.asarray(quad, dtype=np.float32)
    w, h = size
    dst_pts = np.asarray([(0, 0), (w - 1, 0), (w - 1, h - 1), (0, h - 1)], dtype=np.float32)
    matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)
    return cv2.warpPerspective(src, matrix, size, flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


def draw_quad_grid(path: Path, quad: list[tuple[float, float]], out: Path) -> None:
    im = pil_rgb(path)
    draw = ImageDraw.Draw(im)
    draw.line(quad + [quad[0]], fill=(255, 30, 30), width=4)
    for i, pt in enumerate(quad, 1):
        x, y = pt
        draw.ellipse((x - 7, y - 7, x + 7, y + 7), outline=(255, 255, 0), width=3)
        draw.text((x + 9, y + 2), str(i), fill=(255, 255, 0))
    im.save(out)


def match_mean_std(arr: np.ndarray, target: np.ndarray, strength: float = 0.70) -> np.ndarray:
    a = arr.astype(np.float32)
    t = target.astype(np.float32)
    a_mean, a_std = a.reshape(-1, 3).mean(axis=0), a.reshape(-1, 3).std(axis=0) + 1e-5
    t_mean, t_std = t.reshape(-1, 3).mean(axis=0), t.reshape(-1, 3).std(axis=0) + 1e-5
    transferred = (a - a_mean) / a_std * (t_std * 0.88) + t_mean
    return np.clip(a * (1 - strength) + transferred * strength, 0, 255)


def watercolorize(rect: np.ndarray, style_target: np.ndarray, seed: int, warm_windows: bool) -> np.ndarray:
    rng = np.random.default_rng(seed)
    rect = cv2.resize(rect, (W, H), interpolation=cv2.INTER_CUBIC)

    # Smooth the photograph toward wash-like color masses before deriving linework.
    smooth = cv2.bilateralFilter(rect, d=7, sigmaColor=55, sigmaSpace=13)
    lab = cv2.cvtColor(smooth, cv2.COLOR_RGB2LAB).astype(np.float32)
    L, A, B = lab[..., 0], lab[..., 1], lab[..., 2]

    gray = cv2.cvtColor(rect, cv2.COLOR_RGB2GRAY).astype(np.float32)
    gray_blur = cv2.GaussianBlur(gray, (0, 0), 1.8)
    gnorm = np.clip((gray_blur - 30) / 210, 0, 1)

    # Muted architectural palette sampled toward the existing artwork.
    shadow = np.array([82, 91, 86], dtype=np.float32)
    mid = np.array([184, 173, 148], dtype=np.float32)
    highlight = np.array([232, 221, 188], dtype=np.float32)
    base = np.where(gnorm[..., None] < 0.55,
                    shadow + (mid - shadow) * (gnorm[..., None] / 0.55),
                    mid + (highlight - mid) * ((gnorm[..., None] - 0.55) / 0.45))

    # Keep the photo-derived dark window rhythm, but make it watercolor, not blue glass.
    hsv = cv2.cvtColor(rect, cv2.COLOR_RGB2HSV)
    dark = gray_blur < np.percentile(gray_blur, 42)
    blueish = (hsv[..., 0] > 80) & (hsv[..., 0] < 135) & (hsv[..., 1] > 25)
    window_mask = cv2.GaussianBlur((dark | blueish).astype(np.float32), (0, 0), 1.1)[..., None]
    if warm_windows:
        win = np.array([91, 95, 84], dtype=np.float32) * 0.60 + np.array([207, 158, 67], dtype=np.float32) * 0.40
    else:
        win = np.array([72, 87, 91], dtype=np.float32)
    base = base * (1 - 0.70 * window_mask) + win * (0.70 * window_mask)

    # Pull the overall statistics back into the target crop's muted watercolor range.
    base = match_mean_std(base, style_target, strength=0.62)

    # Ink/architectural linework from the rectified photo, softened.
    edges = cv2.Canny(rect, threshold1=55, threshold2=135)
    edges = cv2.dilate(edges, np.ones((2, 2), np.uint8), iterations=1)
    edges = cv2.GaussianBlur(edges.astype(np.float32) / 255.0, (0, 0), 0.75)[..., None]
    ink = np.array([48, 58, 58], dtype=np.float32)
    base = base * (1 - 0.38 * edges) + ink * (0.38 * edges)

    # Subtle paper/wash unevenness, deterministic per candidate.
    noise = rng.normal(0, 4.0, size=base.shape).astype(np.float32)
    wash = cv2.GaussianBlur(noise, (0, 0), 6.0)
    base = base + wash

    # Final small blur keeps the plate in the source artwork's soft focus.
    base = cv2.GaussianBlur(base, (0, 0), 0.55)
    return np.clip(base, 0, 255).astype(np.uint8)


def composite(src: np.ndarray, plate: np.ndarray, name: str, min_alpha: float = 0.38, foliage_keep: float = 0.72) -> np.ndarray:
    x0, y0, x1, y1 = BOX
    patch = src[y0:y1, x0:x1].astype(np.float32)
    plate_f = plate.astype(np.float32)

    yy = np.linspace(0, 1, H, dtype=np.float32)[:, None]
    xx = np.linspace(0, 1, W, dtype=np.float32)[None, :]
    vertical = np.minimum(np.clip(yy / 0.13, 0, 1), np.clip((1 - yy) / 0.13, 0, 1))
    horizontal = np.minimum(np.clip(xx / 0.045, 0, 1), np.clip((1 - xx) / 0.045, 0, 1))
    alpha = (min_alpha + (1 - min_alpha) * vertical) * (0.72 + 0.28 * horizontal)

    # Protect the tree/foliage that overlaps the left edge of the allowed box.
    hsv = cv2.cvtColor(src[y0:y1, x0:x1], cv2.COLOR_RGB2HSV)
    foliage = ((hsv[..., 0] > 15) & (hsv[..., 0] < 55) & (hsv[..., 1] > 28) & (xx < 0.25))
    foliage = cv2.GaussianBlur(foliage.astype(np.float32), (0, 0), 4.0)
    alpha = alpha * (1 - foliage_keep * foliage)
    alpha = alpha[..., None]

    mixed = patch * (1 - alpha) + plate_f * alpha
    out = src.copy()
    out[y0:y1, x0:x1] = np.clip(mixed, 0, 255).astype(np.uint8)
    from_np(out).save(OUT / f"{name}_composited.png")
    from_np(out[ZOOM_BOX[1]:ZOOM_BOX[3], ZOOM_BOX[0]:ZOOM_BOX[2]]).save(OUT / f"{name}_zoom.png")
    from_np(out[y0:y1, x0:x1]).save(OUT / f"{name}_box_zoom.png")
    return out


def draw_simplified_photo_plate(photo_plate: np.ndarray, style_target: np.ndarray) -> np.ndarray:
    """Use rectified-photo texture, but simplify into the source elevation rhythm."""
    # Start with a pale stone wash from the photo texture and source palette.
    texture = cv2.GaussianBlur(photo_plate.astype(np.float32), (0, 0), 3.2)
    texture = match_mean_std(texture, style_target, strength=0.78)
    stone = np.full((H, W, 3), np.array([211, 201, 173], dtype=np.float32), dtype=np.float32)
    plate = stone * 0.58 + texture * 0.42

    rng = np.random.default_rng(404)
    wash = cv2.GaussianBlur(rng.normal(0, 3.5, size=plate.shape).astype(np.float32), (0, 0), 9)
    plate += wash

    im = from_np(plate)
    draw = ImageDraw.Draw(im, "RGBA")

    # Bay rhythm follows the existing source elevation, not the distorted photo.
    edges = [0, 84, 174, 264, 354, 443, 533, 623, 690, 738, 786, 835, 884, 920]
    front_until = 690

    # Horizontal belt courses and low plinth. Keep them slightly wavering via translucent lines.
    draw.rectangle((0, 0, W, 13), fill=(190, 182, 158, 95))
    draw.line((0, 18, W, 17), fill=(78, 88, 84, 85), width=1)
    draw.rectangle((0, 206, W, 246), fill=(185, 176, 150, 88))
    draw.line((0, 207, W, 207), fill=(76, 83, 78, 105), width=2)
    draw.line((0, 246, W, 246), fill=(88, 84, 72, 80), width=1)

    # Vertical piers: pale faces plus one darker ink side, like the existing tower.
    for x in edges:
        pier_w = 20 if x < front_until else 12
        draw.rectangle((x - pier_w // 2, 8, x + pier_w // 2, 238), fill=(222, 213, 184, 116))
        draw.line((x - pier_w // 2, 14, x - pier_w // 2, 232), fill=(84, 91, 84, 92), width=1)
        draw.line((x + pier_w // 2, 14, x + pier_w // 2, 232), fill=(244, 234, 204, 76), width=1)

    # Window groups: one smaller upper row plus a quiet ground-floor row, no canopy/text.
    window_fill = (55, 73, 76, 128)
    window_glaze = (126, 146, 141, 78)
    warm_reflect = (215, 159, 62, 34)
    ink = (38, 49, 50, 112)
    for a, b in zip(edges[:-1], edges[1:]):
        bay_w = b - a
        if bay_w < 28:
            continue
        inset = 27 if b <= front_until else 10
        group_x0 = a + inset
        group_x1 = b - inset
        if group_x1 - group_x0 < 12:
            continue
        slots = 2 if (group_x1 - group_x0) < 34 else 3
        gap = 5 if slots == 2 else 6
        slot_w = max(4, int((group_x1 - group_x0 - gap * (slots - 1)) / slots))
        for row_y0, row_y1, extra_alpha in [(48, 98, 0), (126, 198, 20)]:
            x = group_x0
            for _ in range(slots):
                x2 = min(group_x1, x + slot_w)
                draw.rounded_rectangle((x, row_y0, x2, row_y1), radius=3,
                                       fill=tuple(min(255, c + extra_alpha) for c in window_fill),
                                       outline=ink, width=1)
                draw.rectangle((x + 2, row_y0 + 2, x2 - 2, row_y1 - 2), fill=window_glaze)
                if row_y0 > 100:
                    draw.rectangle((x + 2, row_y1 - 15, x2 - 2, row_y1 - 3), fill=warm_reflect)
                x += slot_w + gap
        # faint stone panel divisions from the photo-derived architecture
        draw.line((a + 6, 107, b - 6, 107), fill=(91, 88, 76, 46), width=1)

    plate = to_np(im).astype(np.float32)

    # Add restrained linework extracted from the photo plate so the candidate remains photo-driven.
    gray = cv2.cvtColor(photo_plate, cv2.COLOR_RGB2GRAY)
    edges_img = cv2.Canny(gray, 65, 155)
    edges_img = cv2.GaussianBlur(edges_img.astype(np.float32) / 255.0, (0, 0), 0.65)[..., None]
    plate = plate * (1 - 0.11 * edges_img) + np.array([42, 51, 51], dtype=np.float32) * (0.11 * edges_img)

    plate = cv2.GaussianBlur(plate, (0, 0), 0.42)
    return np.clip(plate, 0, 255).astype(np.uint8)


def contact_sheet(items: list[tuple[str, Image.Image]], out: Path) -> None:
    thumb_w, thumb_h = 420, 220
    margin, label_h = 14, 24
    sheet = Image.new("RGB", (thumb_w * 2 + margin * 3, (thumb_h + label_h + margin) * ((len(items) + 1) // 2) + margin), (238, 234, 222))
    draw = ImageDraw.Draw(sheet)
    for idx, (label, im) in enumerate(items):
        r, c = divmod(idx, 2)
        x = margin + c * (thumb_w + margin)
        y = margin + r * (thumb_h + label_h + margin)
        t = im.copy()
        t.thumbnail((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        sheet.paste(t, (x, y + label_h))
        draw.text((x, y), label, fill=(35, 35, 35))
    sheet.save(out)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    src = to_np(pil_rgb(SRC))
    x0, y0, x1, y1 = BOX
    style_target = src[2480:2580, 3162:4082]
    from_np(src[y0:y1, x0:x1]).save(OUT / "_source_allowed_box.png")

    quads = {
        # Lower podium/front-facade rectangle before the Cahill entrance canopy.
        "cahill2": [(92, 423), (508, 423), (512, 646), (86, 650)],
        # Frontal lower facade in the street-level image, cropped just above sign/canopy.
        "streetlevel": [(77, 244), (548, 252), (585, 536), (49, 528)],
    }
    draw_quad_grid(CAHILL2, quads["cahill2"], OUT / "_quad_cahill2.png")
    draw_quad_grid(STREET, quads["streetlevel"], OUT / "_quad_streetlevel.png")

    raw_cahill = rectify(CAHILL2, quads["cahill2"], (W, H))
    raw_street = rectify(STREET, quads["streetlevel"], (W, H))
    from_np(raw_cahill).save(OUT / "raw_rectified_cahill2.png")
    from_np(raw_street).save(OUT / "raw_rectified_streetlevel.png")

    plate_cahill = watercolorize(raw_cahill, style_target, seed=122, warm_windows=True)
    plate_street = watercolorize(raw_street, style_target, seed=223, warm_windows=False)
    from_np(plate_cahill).save(OUT / "plate_cahill2_watercolor.png")
    from_np(plate_street).save(OUT / "plate_streetlevel_watercolor.png")

    # A hybrid keeps street-level photo line rhythm but uses Cahill's warmer lower-base massing.
    hybrid = np.clip(plate_street.astype(np.float32) * 0.62 + plate_cahill.astype(np.float32) * 0.38, 0, 255).astype(np.uint8)
    hybrid = cv2.GaussianBlur(hybrid, (0, 0), 0.35)
    from_np(hybrid).save(OUT / "plate_hybrid_watercolor.png")

    simplified = draw_simplified_photo_plate(hybrid, style_target)
    from_np(simplified).save(OUT / "plate_simplified_aligned_watercolor.png")

    cand_cahill = composite(src, plate_cahill, "w2_photo_rectified_cahill2")
    cand_street = composite(src, plate_street, "w2_photo_rectified_streetlevel")
    cand_hybrid = composite(src, hybrid, "w2_photo_rectified_hybrid")
    cand_simplified = composite(src, simplified, "w2_photo_rectified_simplified")
    cand_simplified_strong = composite(src, simplified, "w2_photo_rectified_simplified_strong", min_alpha=0.60, foliage_keep=0.58)

    source_zoom = from_np(src[ZOOM_BOX[1]:ZOOM_BOX[3], ZOOM_BOX[0]:ZOOM_BOX[2]])
    contact_sheet(
        [
            ("source crop", source_zoom),
            ("raw Cahill2 rectified", from_np(raw_cahill)),
            ("Cahill2 watercolor plate", from_np(plate_cahill)),
            ("Cahill2 composite zoom", from_np(cand_cahill[ZOOM_BOX[1]:ZOOM_BOX[3], ZOOM_BOX[0]:ZOOM_BOX[2]])),
            ("raw streetlevel rectified", from_np(raw_street)),
            ("streetlevel watercolor plate", from_np(plate_street)),
            ("streetlevel composite zoom", from_np(cand_street[ZOOM_BOX[1]:ZOOM_BOX[3], ZOOM_BOX[0]:ZOOM_BOX[2]])),
            ("hybrid composite zoom", from_np(cand_hybrid[ZOOM_BOX[1]:ZOOM_BOX[3], ZOOM_BOX[0]:ZOOM_BOX[2]])),
            ("simplified aligned plate", from_np(simplified)),
            ("simplified composite zoom", from_np(cand_simplified[ZOOM_BOX[1]:ZOOM_BOX[3], ZOOM_BOX[0]:ZOOM_BOX[2]])),
            ("simplified strong zoom", from_np(cand_simplified_strong[ZOOM_BOX[1]:ZOOM_BOX[3], ZOOM_BOX[0]:ZOOM_BOX[2]])),
        ],
        OUT / "contact_sheet.png",
    )

    print("wrote candidates to", OUT)


if __name__ == "__main__":
    main()
