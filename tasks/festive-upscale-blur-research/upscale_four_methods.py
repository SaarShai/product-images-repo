from __future__ import annotations

import json
import subprocess
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage as ndi


PROD = Path(
    "/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/festive/images"
)
SRC_OBJECT = PROD / "best option 2-05.png"
SRC_PANEL = PROD / "best option 2-06.png"
OUT_DIR = PROD / "Images" / "candidates"
TASK_DIR = Path("tasks/festive-upscale-blur-research")
ANALYSIS_DIR = TASK_DIR / "analysis"

REALESRGAN = Path("tasks/marine-pod-upscale/tools/realesrgan-full/realesrgan-ncnn-vulkan")
REALESRGAN_MODELS = Path("tasks/marine-pod-upscale/tools/realesrgan-full/models")
SCALE = 4


def ensure_dirs() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)


def load_rgb(path: Path) -> np.ndarray:
    return np.array(Image.open(path).convert("RGB"))


def write_rgba(arr: np.ndarray, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA").save(path)


def write_rgb(arr: np.ndarray, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB").save(path)


def border_connected_black_mask(rgb: np.ndarray, threshold: int = 10) -> np.ndarray:
    near_black = np.all(rgb <= threshold, axis=2)
    labels, n = ndi.label(near_black)
    if n == 0:
        return np.zeros(near_black.shape, dtype=bool)
    border_labels = set(np.unique(labels[0, :]))
    border_labels.update(np.unique(labels[-1, :]))
    border_labels.update(np.unique(labels[:, 0]))
    border_labels.update(np.unique(labels[:, -1]))
    border_labels.discard(0)
    return np.isin(labels, list(border_labels))


def object_rgba_from_black_bg(rgb: np.ndarray) -> np.ndarray:
    bg = border_connected_black_mask(rgb)
    fg = ~bg
    # Fill tiny background pinholes inside the object while keeping the outer silhouette.
    fg = ndi.binary_fill_holes(fg)
    fg = ndi.binary_opening(fg, iterations=1)
    fg = ndi.binary_closing(fg, iterations=1)
    alpha = ndi.gaussian_filter(fg.astype(np.float32), sigma=0.55)
    rgba = np.dstack([rgb, np.clip(alpha * 255, 0, 255).astype(np.uint8)])
    rgba[rgba[..., 3] == 0, :3] = 0
    return rgba


def composite_on(arr: np.ndarray, bg: tuple[int, int, int]) -> Image.Image:
    im = Image.fromarray(arr.astype(np.uint8), "RGBA")
    canvas = Image.new("RGBA", im.size, (*bg, 255))
    canvas.alpha_composite(im)
    return canvas.convert("RGB")


def unsharp_cv(rgb: np.ndarray, amount: float = 0.65, sigma: float = 1.15) -> np.ndarray:
    blur = cv2.GaussianBlur(rgb, (0, 0), sigmaX=sigma)
    return cv2.addWeighted(rgb, 1 + amount, blur, -amount, 0)


def method_cv2_direct(rgb: np.ndarray) -> np.ndarray:
    h, w = rgb.shape[:2]
    up = cv2.resize(rgb, (w * SCALE, h * SCALE), interpolation=cv2.INTER_LANCZOS4)
    up = unsharp_cv(up, amount=0.72, sigma=1.2)
    a = np.full(up.shape[:2], 255, dtype=np.uint8)
    return np.dstack([up, a])


def resize_rgba_premult(rgba: np.ndarray, size: tuple[int, int], resample=Image.Resampling.LANCZOS) -> np.ndarray:
    rgb = rgba[..., :3].astype(np.float32)
    a = rgba[..., 3:4].astype(np.float32) / 255.0
    premul = (rgb * a).astype(np.uint8)
    premul_img = Image.fromarray(premul, "RGB").resize(size, resample)
    alpha_img = Image.fromarray(rgba[..., 3], "L").resize(size, resample)
    premul_up = np.array(premul_img).astype(np.float32)
    alpha_up = np.array(alpha_img).astype(np.float32)
    denom = np.maximum(alpha_up[..., None] / 255.0, 1e-4)
    rgb_up = np.clip(premul_up / denom, 0, 255).astype(np.uint8)
    out = np.dstack([rgb_up, alpha_up.astype(np.uint8)])
    out[out[..., 3] == 0, :3] = 0
    return out


def method_pillow_alpha_adaptive(rgba: np.ndarray) -> np.ndarray:
    h, w = rgba.shape[:2]
    up = resize_rgba_premult(rgba, (w * SCALE, h * SCALE))
    pil = Image.fromarray(up, "RGBA")
    rgb = pil.convert("RGB").filter(ImageFilter.UnsharpMask(radius=1.6, percent=135, threshold=4))
    out = np.dstack([np.array(rgb), up[..., 3]])
    # A second local adaptive pass only where the original had structure, avoiding flat alpha edge noise.
    bgr = cv2.cvtColor(out[..., :3], cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    grad = cv2.magnitude(
        cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3),
        cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3),
    )
    presence = cv2.GaussianBlur((grad > np.percentile(grad[up[..., 3] > 0], 55)).astype(np.float32), (0, 0), 4.0)
    sharp = unsharp_cv(out[..., :3], amount=0.45, sigma=0.9)
    mix = np.clip(presence[..., None] * (up[..., 3:4] > 0), 0, 1)
    out[..., :3] = np.clip(out[..., :3] * (1 - mix) + sharp * mix, 0, 255).astype(np.uint8)
    out[out[..., 3] == 0, :3] = 0
    return out


def run_realesrgan(inp: Path, out: Path, model: str = "realesrgan-x4plus") -> None:
    cmd = [
        str(REALESRGAN),
        "-i",
        str(inp),
        "-o",
        str(out),
        "-s",
        str(SCALE),
        "-m",
        str(REALESRGAN_MODELS),
        "-n",
        model,
        "-f",
        "png",
    ]
    subprocess.run(cmd, check=True)


def method_realesrgan_direct(src: Path, out_path: Path) -> np.ndarray:
    run_realesrgan(src, out_path, "realesrgan-x4plus")
    arr = load_rgb(out_path)
    return np.dstack([arr, np.full(arr.shape[:2], 255, dtype=np.uint8)])


def method_realesrgan_alpha_padded(rgb: np.ndarray, rgba: np.ndarray, out_path: Path) -> np.ndarray:
    h, w = rgb.shape[:2]
    padded_w = max(512, w)
    left = (padded_w - w) // 2
    cream = np.array([248, 240, 218], dtype=np.uint8)
    alpha = rgba[..., 3:4].astype(np.float32) / 255.0
    rgb_on_cream = (rgb.astype(np.float32) * alpha + cream * (1 - alpha)).astype(np.uint8)
    pad = np.tile(cream, (h, padded_w, 1))
    pad[:, left : left + w, :] = rgb_on_cream
    inp = ANALYSIS_DIR / "object-cream-padded-input.png"
    write_rgb(pad, inp)
    run_realesrgan(inp, out_path, "realesrgan-x4plus")
    up = load_rgb(out_path)
    crop = up[:, left * SCALE : (left + w) * SCALE, :]
    alpha_up = np.array(Image.fromarray(rgba[..., 3], "L").resize((w * SCALE, h * SCALE), Image.Resampling.LANCZOS))
    out = np.dstack([crop, alpha_up])
    out[out[..., 3] == 0, :3] = 0
    return out


def sharpness_metrics(rgba: np.ndarray) -> dict:
    rgb = rgba[..., :3]
    a = rgba[..., 3] > 8
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    lap = cv2.Laplacian(gray, cv2.CV_64F)
    grad = cv2.magnitude(
        cv2.Sobel(gray.astype(np.float32), cv2.CV_32F, 1, 0, ksize=3),
        cv2.Sobel(gray.astype(np.float32), cv2.CV_32F, 0, 1, ksize=3),
    )
    vals = lap[a]
    gvals = grad[a]
    return {
        "size": list(rgba.shape[:2][::-1]),
        "alpha_nonzero": int(np.count_nonzero(a)),
        "lap_var_fg": float(vals.var()) if vals.size else 0.0,
        "grad_p95_fg": float(np.percentile(gvals, 95)) if gvals.size else 0.0,
    }


def make_blur_diagnostic(src_rgba: np.ndarray) -> Path:
    rgb = src_rgba[..., :3]
    alpha = src_rgba[..., 3] > 8
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
    lap_abs = np.abs(cv2.Laplacian(gray, cv2.CV_32F))
    local = cv2.boxFilter(lap_abs, ddepth=-1, ksize=(33, 33), normalize=True)
    local[~alpha] = 0
    ref = np.percentile(local[alpha], 95) if np.any(alpha) else 1
    heat = np.clip(local / max(ref, 1e-6), 0, 1)
    heat_img = cv2.applyColorMap((heat * 255).astype(np.uint8), cv2.COLORMAP_INFERNO)
    heat_img = cv2.cvtColor(heat_img, cv2.COLOR_BGR2RGB)
    overlay = (rgb.astype(np.float32) * 0.55 + heat_img.astype(np.float32) * 0.45).astype(np.uint8)
    diag = np.dstack([overlay, src_rgba[..., 3]])
    path = ANALYSIS_DIR / "object-local-sharpness-heatmap.png"
    write_rgba(diag, path)
    return path


def make_contact(outputs: list[tuple[str, Path]], out_path: Path, bg=(255, 255, 255), zoom: tuple[int, int, int, int] | None = None) -> None:
    images = []
    for label, path in outputs:
        arr = np.array(Image.open(path).convert("RGBA"))
        im = composite_on(arr, bg)
        if zoom is not None:
            im = im.crop(zoom)
        im.thumbnail((560, 1400), Image.Resampling.LANCZOS)
        images.append((label, im.copy()))
    cols = 3
    label_h = 44
    pad = 24
    w = max(im.width for _, im in images)
    h = max(im.height for _, im in images)
    rows = int(np.ceil(len(images) / cols))
    sheet = Image.new("RGB", (cols * w + (cols + 1) * pad, rows * (h + label_h) + (rows + 1) * pad), bg)
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 24)
    except OSError:
        font = ImageFont.load_default()
    text_fill = (255, 255, 255) if sum(bg) < 120 else (30, 30, 30)
    for idx, (label, im) in enumerate(images):
        r, c = divmod(idx, cols)
        x = pad + c * (w + pad)
        y = pad + r * (h + label_h + pad)
        draw.text((x, y), label, fill=text_fill, font=font)
        sheet.paste(im, (x, y + label_h))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path, quality=95)


def main() -> None:
    ensure_dirs()
    src_rgb = load_rgb(SRC_OBJECT)
    src_rgba = object_rgba_from_black_bg(src_rgb)
    source_clean = ANALYSIS_DIR / "best-option-2-05-object-clean-rgba.png"
    write_rgba(src_rgba, source_clean)
    heatmap = make_blur_diagnostic(src_rgba)

    outputs: list[tuple[str, Path]] = []

    m1 = method_cv2_direct(src_rgb)
    m1_path = OUT_DIR / "best-option-2-05-upscale-m1-opencv-lanczos-unsharp-x4.png"
    write_rgba(m1, m1_path)
    outputs.append(("m1 OpenCV Lanczos", m1_path))

    m2 = method_pillow_alpha_adaptive(src_rgba)
    m2_path = OUT_DIR / "best-option-2-05-upscale-m2-alpha-premult-pillow-adaptive-x4.png"
    write_rgba(m2, m2_path)
    outputs.append(("m2 alpha+adaptive", m2_path))

    m3_path = OUT_DIR / "best-option-2-05-upscale-m3-realesrgan-direct-x4.png"
    m3 = method_realesrgan_direct(SRC_OBJECT, m3_path)
    write_rgba(m3, m3_path)
    outputs.append(("m3 ESRGAN direct", m3_path))

    m4_tmp = ANALYSIS_DIR / "best-option-2-05-upscale-m4-realesrgan-cream-padded-raw.png"
    m4 = method_realesrgan_alpha_padded(src_rgb, src_rgba, m4_tmp)
    m4_path = OUT_DIR / "best-option-2-05-upscale-m4-realesrgan-alpha-padded-fixed-x4.png"
    write_rgba(m4, m4_path)
    outputs.append(("m4 ESRGAN padded fix", m4_path))

    source_up = resize_rgba_premult(src_rgba, (src_rgba.shape[1] * SCALE, src_rgba.shape[0] * SCALE), Image.Resampling.NEAREST)
    source_up_path = ANALYSIS_DIR / "source-nearest-x4-reference.png"
    write_rgba(source_up, source_up_path)
    all_for_contact = [("source nearest x4", source_up_path), *outputs]

    make_contact(all_for_contact, OUT_DIR / "best-option-2-05-upscale-four-methods-contact-white.jpg", bg=(255, 255, 255))
    make_contact(all_for_contact, OUT_DIR / "best-option-2-05-upscale-four-methods-contact-magenta.jpg", bg=(206, 0, 180))
    make_contact(all_for_contact, OUT_DIR / "best-option-2-05-upscale-four-methods-contact-black.jpg", bg=(0, 0, 0))
    # Zoom around the candy cane and mixed sharp/soft gingerbread texture.
    zoom = (70 * SCALE, 90 * SCALE, 176 * SCALE, 430 * SCALE)
    make_contact(all_for_contact, OUT_DIR / "best-option-2-05-upscale-four-methods-zoom-candy-texture-magenta.jpg", bg=(206, 0, 180), zoom=zoom)

    metrics = {
        "source_object": str(SRC_OBJECT),
        "source_panel": str(SRC_PANEL),
        "source_size": list(src_rgb.shape[:2][::-1]),
        "source_black_background_pct": float(border_connected_black_mask(src_rgb).mean() * 100),
        "clean_rgba_path": str(source_clean),
        "heatmap_path": str(heatmap),
        "methods": {},
    }
    for label, path in outputs:
        arr = np.array(Image.open(path).convert("RGBA"))
        metrics["methods"][label] = {"path": str(path), **sharpness_metrics(arr)}
    metrics_path = ANALYSIS_DIR / "upscale-method-metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2))
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
