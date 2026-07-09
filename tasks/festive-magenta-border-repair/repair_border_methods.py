from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi
from skimage.morphology import binary_closing, binary_opening, disk


SRC = Path(
    "/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/festive/images/best magenta background-09.png"
)
OUT_DIR = SRC.parent / "Images" / "candidates"
ANALYSIS_DIR = Path("tasks/festive-magenta-border-repair/analysis")


METHODS = {
    "method1-alpha-trim": "trim the outer 4px alpha ring and re-feather",
    "method2-cream-halo-neutralize": "recolor the outer artifact band to warm icing tones",
    "method3-detached-line-remove": "remove thin detached outline components, then softly re-feather the main silhouette",
}


def rgba_array(path: Path) -> np.ndarray:
    return np.array(Image.open(path).convert("RGBA"))


def write_png(arr: np.ndarray, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA").save(path)


def premult_on_white(arr: np.ndarray) -> Image.Image:
    rgb = arr[..., :3].astype(np.float32)
    a = arr[..., 3:4].astype(np.float32) / 255.0
    comp = rgb * a + 255 * (1 - a)
    return Image.fromarray(np.clip(comp, 0, 255).astype(np.uint8), "RGB")


def edge_distance(mask: np.ndarray) -> np.ndarray:
    return ndi.distance_transform_edt(mask)


def method1_alpha_trim(src: np.ndarray) -> np.ndarray:
    out = src.copy()
    a = src[..., 3]
    mask = a > 4
    eroded = ndi.binary_erosion(mask, iterations=4)
    feather = ndi.gaussian_filter(eroded.astype(np.float32), sigma=1.4)
    new_a = np.minimum(a.astype(np.float32), feather * 255.0)
    out[..., 3] = np.clip(new_a, 0, 255).astype(np.uint8)
    out[out[..., 3] == 0, :3] = 0
    return out


def method2_cream_halo_neutralize(src: np.ndarray) -> np.ndarray:
    out = src.copy()
    rgb = out[..., :3].astype(np.float32)
    a = out[..., 3].astype(np.float32)
    mask = a > 4
    dist = edge_distance(mask)
    edge = mask & (dist <= 12)
    lum = rgb.mean(axis=2)
    sat = rgb.max(axis=2) - rgb.min(axis=2)
    # The unwanted border is mostly low-chroma gray/tan edge ink. Avoid red/green/blue candies.
    artifact = edge & ((lum < 228) | ((sat < 32) & (lum < 246))) & (a > 12)
    cream = np.array([250, 241, 219], dtype=np.float32)
    falloff = np.clip((13.0 - dist) / 12.0, 0.0, 1.0)[..., None]
    amt = np.where(artifact[..., None], 0.78 * falloff, 0.0)
    rgb = rgb * (1 - amt) + cream * amt
    # Slightly soften only the very outside of artifact pixels so the jagged line cannot read as a stroke.
    alpha_factor = np.ones_like(a)
    alpha_factor[artifact & (dist <= 3)] = 0.58
    alpha_factor[artifact & (dist > 3) & (dist <= 6)] = 0.78
    out[..., :3] = np.clip(rgb, 0, 255).astype(np.uint8)
    out[..., 3] = np.clip(a * alpha_factor, 0, 255).astype(np.uint8)
    return out


def method3_detached_line_remove(src: np.ndarray) -> np.ndarray:
    out = src.copy()
    a = src[..., 3]
    mask = a > 8
    # The bad border is an opaque but very thin detached contour. Opening drops
    # those strokes while broad cookies, icing rims, and candy silhouettes stay.
    opened = binary_opening(mask, disk(5))
    opened = binary_closing(opened, disk(2))
    keep = ndi.binary_dilation(opened, iterations=2) & mask
    feather = ndi.gaussian_filter(keep.astype(np.float32), sigma=0.9)
    new_alpha = np.minimum(a.astype(np.float32), feather * 255.0)
    out[..., 3] = np.clip(new_alpha, 0, 255).astype(np.uint8)
    out[out[..., 3] == 0, :3] = 0
    return out


def make_contact(paths: list[Path], labels: list[str], out_path: Path) -> None:
    thumbs = []
    for p in paths:
        im = premult_on_white(rgba_array(p))
        im.thumbnail((900, 1180), Image.Resampling.LANCZOS)
        thumbs.append(im.copy())
    w = max(im.width for im in thumbs)
    h = max(im.height for im in thumbs)
    pad = 36
    label_h = 58
    sheet = Image.new("RGB", (2 * w + 3 * pad, 2 * (h + label_h) + 3 * pad), "white")
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 30)
    except OSError:
        font = ImageFont.load_default()
    for idx, (im, label) in enumerate(zip(thumbs, labels)):
        row, col = divmod(idx, 2)
        x = pad + col * (w + pad)
        y = pad + row * (h + label_h + pad)
        draw.text((x, y), label, fill=(35, 35, 35), font=font)
        sheet.paste(im, (x, y + label_h))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path, quality=95)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    src = rgba_array(SRC)
    outputs = []
    for name, func in [
        ("method1-alpha-trim", method1_alpha_trim),
        ("method2-cream-halo-neutralize", method2_cream_halo_neutralize),
        ("method3-detached-line-remove", method3_detached_line_remove),
    ]:
        arr = func(src)
        out_path = OUT_DIR / f"best-magenta-background-09-border-repair-{name}.png"
        write_png(arr, out_path)
        outputs.append(out_path)

        preview = premult_on_white(arr)
        preview.thumbnail((1400, 1850), Image.Resampling.LANCZOS)
        preview.save(ANALYSIS_DIR / f"{name}-on-white-preview.jpg", quality=95)

    src_preview = ANALYSIS_DIR / "source-on-white-fullscaled.jpg"
    src_img = premult_on_white(src)
    src_img.thumbnail((1400, 1850), Image.Resampling.LANCZOS)
    src_img.save(src_preview, quality=95)

    make_contact(
        [SRC, *outputs],
        ["source", "method 1 alpha trim", "method 2 cream neutralize", "method 3 detached-line remove"],
        OUT_DIR / "best-magenta-background-09-border-repair-contact-sheet.jpg",
    )

    metrics = []
    src_alpha = src[..., 3]
    src_mask = src_alpha > 0
    for p in outputs:
        arr = rgba_array(p)
        alpha = arr[..., 3]
        changed = np.any(np.abs(arr.astype(np.int16) - src.astype(np.int16)) > 2, axis=2)
        metrics.append(
            {
                "file": str(p),
                "size": list(arr.shape[:2][::-1]),
                "outside_original_alpha_pixels": int(np.count_nonzero((alpha > 0) & ~src_mask)),
                "alpha_pixels_removed": int(np.count_nonzero((src_alpha > 0) & (alpha == 0))),
                "changed_pixels": int(np.count_nonzero(changed)),
                "alpha_bbox": Image.fromarray(alpha).getbbox(),
            }
        )
    import json

    (ANALYSIS_DIR / "repair-metrics.json").write_text(json.dumps(metrics, indent=2))
    print(json.dumps(metrics, indent=2))
    print("contact_sheet", OUT_DIR / "best-magenta-background-09-border-repair-contact-sheet.jpg")


if __name__ == "__main__":
    main()
