from __future__ import annotations

import base64
import hashlib
import io
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import requests
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage as ndi

sys.path.insert(0, "scripts")
from falgen import load_key  # noqa: E402


PROD = Path(
    "/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/festive/images"
)
OUT_DIR = PROD / "Images" / "candidates"
TASK_DIR = Path("tasks/festive-magenta-m5-upscale")
ANALYSIS_DIR = TASK_DIR / "analysis"
SCALE = 2
FAL_ENDPOINT = "fal-ai/recraft/upscale/crisp"

PILOTS = [
    PROD / "best magenta background-07.png",
    PROD / "best magenta background-03.png",
]


def slug(path: Path) -> str:
    return path.stem.replace(" ", "-").lower()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def connected_background_mask(rgb: np.ndarray) -> np.ndarray:
    h, w = rgb.shape[:2]
    border = np.concatenate([rgb[0, :, :], rgb[-1, :, :], rgb[:, 0, :], rgb[:, -1, :]], axis=0)
    bg = np.median(border, axis=0)

    dist = np.linalg.norm(rgb.astype(np.float32) - bg.astype(np.float32), axis=2)
    magenta_family = (rgb[..., 0] > 185) & (rgb[..., 1] < 95) & (rgb[..., 2] > 165)
    near_bg = (dist < 82) | magenta_family

    labels, n = ndi.label(near_bg)
    if n == 0:
        return np.zeros((h, w), dtype=bool)
    border_labels = set(np.unique(labels[0, :]))
    border_labels.update(np.unique(labels[-1, :]))
    border_labels.update(np.unique(labels[:, 0]))
    border_labels.update(np.unique(labels[:, -1]))
    border_labels.discard(0)
    bg_mask = np.isin(labels, list(border_labels))
    bg_mask = ndi.binary_closing(bg_mask, iterations=1)
    return bg_mask


def rgba_from_magenta_source(src: Path) -> np.ndarray:
    rgb = np.array(Image.open(src).convert("RGB"))
    bg_mask = connected_background_mask(rgb)
    fg = ~bg_mask
    fg = ndi.binary_fill_holes(fg)
    fg = ndi.binary_opening(fg, iterations=1)
    fg = ndi.binary_closing(fg, iterations=1)
    alpha = ndi.gaussian_filter(fg.astype(np.float32), sigma=0.75)
    alpha = np.clip(alpha * 255, 0, 255).astype(np.uint8)
    rgba = np.dstack([rgb, alpha])
    rgba[rgba[..., 3] == 0, :3] = 0
    return rgba


def write_rgba(rgba: np.ndarray, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.clip(rgba, 0, 255).astype(np.uint8), "RGBA").save(path)


def composite_over(rgba: np.ndarray, bg: tuple[int, int, int]) -> Image.Image:
    im = Image.fromarray(rgba.astype(np.uint8), "RGBA")
    canvas = Image.new("RGBA", im.size, (*bg, 255))
    canvas.alpha_composite(im)
    return canvas.convert("RGB")


def make_padded_input(rgba: np.ndarray, path: Path) -> tuple[int, int, int]:
    h, w = rgba.shape[:2]
    padded_w = max(512, w)
    padded_h = h
    left = (padded_w - w) // 2
    cream = np.array([249, 240, 220], dtype=np.float32)
    rgb = rgba[..., :3].astype(np.float32)
    a = rgba[..., 3:4].astype(np.float32) / 255.0
    object_on_cream = rgb * a + cream * (1.0 - a)
    pad = np.tile(cream.astype(np.uint8), (padded_h, padded_w, 1))
    pad[:, left : left + w, :] = np.clip(object_on_cream, 0, 255).astype(np.uint8)
    Image.fromarray(pad, "RGB").save(path)
    return left, padded_w, padded_h


def fal_crisp(input_path: Path, output_path: Path) -> None:
    im = Image.open(input_path).convert("RGB")
    b = io.BytesIO()
    im.save(b, "PNG")
    uri = "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()
    response = requests.post(
        f"https://fal.run/{FAL_ENDPOINT}",
        headers={"Authorization": f"Key {load_key()}", "Content-Type": "application/json"},
        json={"image_url": uri},
        timeout=420,
    )
    if response.status_code != 200:
        raise RuntimeError(f"FAL error {response.status_code}: {response.text[:800]}")
    payload = response.json()
    image = payload.get("image") or (payload.get("images") or [None])[0]
    url = image["url"] if isinstance(image, dict) else image
    data = requests.get(url, timeout=240).content
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(data)


def resize_alpha(alpha: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    return np.array(Image.fromarray(alpha, "L").resize(size, Image.Resampling.LANCZOS))


def add_subtle_texture_and_sharpness(rgba: np.ndarray, seed: int) -> np.ndarray:
    rgb = rgba[..., :3].astype(np.float32)
    alpha = rgba[..., 3].astype(np.float32) / 255.0
    fg = alpha > 0.05
    if not np.any(fg):
        return rgba

    pil_rgb = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), "RGB")
    sharpened = pil_rgb.filter(ImageFilter.UnsharpMask(radius=1.15, percent=92, threshold=4))
    rgb = np.array(sharpened).astype(np.float32)

    rng = np.random.default_rng(seed)
    noise = rng.normal(0, 1, rgb.shape[:2]).astype(np.float32)
    grain = cv2.GaussianBlur(noise, (0, 0), sigmaX=0.45)
    wash = cv2.GaussianBlur(noise, (0, 0), sigmaX=5.0)
    tooth = np.clip(grain * 2.3 + wash * 3.5, -8, 8)
    texture_strength = np.clip(alpha * 0.95, 0, 0.95)
    rgb += tooth[..., None] * texture_strength[..., None]

    # Restore the transparent side of the edge and avoid crunchy low-alpha dust.
    out = np.dstack([np.clip(rgb, 0, 255).astype(np.uint8), rgba[..., 3]])
    out[out[..., 3] < 3, :3] = 0
    return out


def edge_clean(rgba: np.ndarray) -> np.ndarray:
    out = rgba.copy()
    alpha = out[..., 3]
    rgb = out[..., :3]
    magenta_like = (rgb[..., 0] > 185) & (rgb[..., 1] < 105) & (rgb[..., 2] > 155)
    weak_edge = (alpha > 0) & (alpha < 180)
    out[..., 3][magenta_like & weak_edge] = np.minimum(out[..., 3][magenta_like & weak_edge], 40)
    out[out[..., 3] < 3, :3] = 0
    return out


def process_one(src: Path) -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    name = slug(src)
    source_sha_before = sha256(src)
    source = Image.open(src).convert("RGB")
    source_w, source_h = source.size
    target_size = (source_w * SCALE, source_h * SCALE)

    clean_rgba = rgba_from_magenta_source(src)
    clean_path = ANALYSIS_DIR / f"{name}-clean-rgba.png"
    write_rgba(clean_rgba, clean_path)

    padded_path = ANALYSIS_DIR / f"{name}-cream-padded-input.png"
    left, padded_w, padded_h = make_padded_input(clean_rgba, padded_path)

    raw_path = ANALYSIS_DIR / f"{name}-m5-fal-crisp-raw.png"
    fal_crisp(padded_path, raw_path)
    raw = Image.open(raw_path).convert("RGB")
    raw_w, raw_h = raw.size
    raw_scale_x = raw_w / padded_w
    raw_scale_y = raw_h / padded_h

    crop = raw.crop((round(left * raw_scale_x), 0, round((left + source_w) * raw_scale_x), raw_h))
    crop = crop.resize(target_size, Image.Resampling.LANCZOS)
    alpha = resize_alpha(clean_rgba[..., 3], target_size)
    rgba = np.dstack([np.array(crop), alpha])
    rgba = edge_clean(add_subtle_texture_and_sharpness(rgba, seed=int(hashlib.sha1(name.encode()).hexdigest()[:8], 16)))

    final_path = OUT_DIR / f"{name}-m5-fal-crisp-clean-x2.png"
    write_rgba(rgba, final_path)

    source_sha_after = sha256(src)
    return {
        "source": str(src),
        "source_sha_before": source_sha_before,
        "source_sha_after": source_sha_after,
        "source_size": [source_w, source_h],
        "target_size": list(target_size),
        "clean_rgba": str(clean_path),
        "padded_input": str(padded_path),
        "raw_fal": str(raw_path),
        "raw_fal_size": [raw_w, raw_h],
        "raw_scale": [raw_scale_x, raw_scale_y],
        "output": str(final_path),
        "output_size": list(Image.open(final_path).size),
    }


def make_contact(entries: list[dict], suffix: str, bg: tuple[int, int, int], zoom: bool = False) -> str:
    tiles: list[tuple[str, Image.Image]] = []
    for item in entries:
        src_rgba = rgba_from_magenta_source(Path(item["source"]))
        src_ref = Image.fromarray(src_rgba, "RGBA").resize(item["target_size"], Image.Resampling.NEAREST)
        out_rgba = np.array(Image.open(item["output"]).convert("RGBA"))
        for label, rgba_im in [
            (Path(item["source"]).name + " source nearest x2", src_ref),
            (Path(item["output"]).name, Image.fromarray(out_rgba, "RGBA")),
        ]:
            im = composite_over(np.array(rgba_im.convert("RGBA")), bg)
            if zoom:
                w, h = im.size
                im = im.crop((int(w * 0.26), int(h * 0.12), int(w * 0.74), int(h * 0.54)))
            im.thumbnail((520, 900), Image.Resampling.LANCZOS)
            tiles.append((label, im.copy()))

    pad = 24
    label_h = 52
    cols = 2
    tile_w = max(t.width for _, t in tiles)
    tile_h = max(t.height for _, t in tiles)
    rows = int(np.ceil(len(tiles) / cols))
    sheet = Image.new("RGB", (cols * tile_w + (cols + 1) * pad, rows * (tile_h + label_h) + (rows + 1) * pad), bg)
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 21)
    except OSError:
        font = ImageFont.load_default()
    fill = (255, 255, 255) if sum(bg) < 120 else (32, 32, 32)
    for i, (label, tile) in enumerate(tiles):
        row, col = divmod(i, cols)
        x = pad + col * (tile_w + pad)
        y = pad + row * (tile_h + label_h + pad)
        draw.text((x, y), label[:58], fill=fill, font=font)
        sheet.paste(tile, (x, y + label_h))

    out = OUT_DIR / f"best-magenta-background-m5-fal-crisp-clean-x2-pilots-{suffix}.jpg"
    sheet.save(out, quality=95)
    return str(out)


def main() -> None:
    manifest = {
        "method": "m5 FAL/Recraft crisp clean, cream padded, clean alpha transfer, edge clean, x2 final from FAL crisp detail",
        "scale": SCALE,
        "pilots": [process_one(path) for path in PILOTS],
        "boards": {},
    }
    manifest["boards"]["contact_magenta"] = make_contact(manifest["pilots"], "contact-magenta", (206, 0, 180), zoom=False)
    manifest["boards"]["contact_white"] = make_contact(manifest["pilots"], "contact-white", (255, 255, 255), zoom=False)
    manifest["boards"]["zoom_magenta"] = make_contact(manifest["pilots"], "zoom-magenta", (206, 0, 180), zoom=True)
    manifest["boards"]["zoom_black"] = make_contact(manifest["pilots"], "zoom-black", (0, 0, 0), zoom=True)
    manifest_path = TASK_DIR / "pilot-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
