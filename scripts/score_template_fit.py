#!/usr/bin/env python3
"""Score generated artwork against the castle-panel template constraints."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from make_overlay_preview import fit_contain, fit_cover, scale_artwork


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEMPLATE = ROOT / "assets/templates/previews/two-panel-template-cropped.png"
DEFAULT_GENERATED = ROOT / "tasks/castle-panels/outputs/generated"
DEFAULT_REVIEW_DIR = ROOT / "tasks/castle-panels/outputs/reviews"
GUIDE_CACHE: dict[tuple[str, int, int, str], dict[str, np.ndarray]] = {}


@dataclass(frozen=True)
class Recipe:
    name: str
    fit: str = "cover"
    art_scale: float = 1.0
    art_scale_x: float | None = None
    art_scale_y: float | None = None
    art_offset_x: int = 0
    art_offset_y: int = 0


@dataclass
class Score:
    image: str
    recipe: str
    mode: str
    score: float
    verdict: str
    left_safe_gap_px: int | None
    right_safe_gap_px: int | None
    bottom_safe_gap_px: int | None
    painted_bbox: list[int] | None
    feature_bbox: list[int] | None
    safe_bbox: list[int] | None
    side_gutter_painted_pct: float
    side_gutter_feature_pct: float
    bottom_gutter_painted_pct: float
    bottom_gutter_feature_pct: float
    center_lane_painted_pct: float
    center_lane_feature_pct: float
    red_zone_feature_pct: float
    cutline_feature_pct: float
    penalties: dict[str, float]
    notes: list[str]


def resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def mask_bbox(mask: np.ndarray) -> tuple[int, int, int, int] | None:
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def pct(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(100.0 * numerator / denominator, 4)


def dilate(mask: np.ndarray, size: int) -> np.ndarray:
    image = Image.fromarray(mask.astype("uint8") * 255)
    return np.asarray(image.filter(ImageFilter.MaxFilter(size=size))) > 0


def guide_masks(template_path: Path, width: int, height: int, fit: str) -> dict[str, np.ndarray]:
    cache_key = (str(template_path.resolve()), width, height, fit)
    cached = GUIDE_CACHE.get(cache_key)
    if cached is not None:
        return cached

    template = Image.open(template_path)
    fitted = fit_cover(template.convert("RGBA"), width, height) if fit == "cover" else fit_contain(template.convert("RGBA"), width, height)
    rgb = np.asarray(fitted.convert("RGB")).astype(np.int16)
    red, green, blue = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    masks = {
        "red": (red > 175) & (green < 120) & (blue < 120),
        "yellow": (red > 185) & (green > 150) & (blue < 130),
        "green": (green > 130) & (red < 140) & (blue < 170),
        "black": (red < 95) & (green < 95) & (blue < 95),
    }
    masks["red_dilated"] = dilate(masks["red"], 9)
    masks["black_dilated"] = dilate(masks["black"], 11)
    GUIDE_CACHE[cache_key] = masks
    return masks


def artwork_masks(image: Image.Image) -> dict[str, np.ndarray]:
    rgb = np.asarray(image.convert("RGB")).astype(np.int16)
    red, green, blue = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    white_distance = (255 - red) + (255 - green) + (255 - blue)
    spread = np.maximum.reduce([red, green, blue]) - np.minimum.reduce([red, green, blue])
    painted = ((white_distance > 34) & ((spread > 5) | (np.minimum.reduce([red, green, blue]) < 246))) | (
        np.minimum.reduce([red, green, blue]) < 238
    )
    saturation = spread
    darkness = 255 - ((red + green + blue) / 3.0)
    warm_detail = (red > green + 18) & (red > blue + 25) & (darkness > 24)
    cool_detail = (blue > red + 18) & (blue > green + 10) & (darkness > 24)
    green_detail = (green > red + 14) & (green > blue + 8) & (darkness > 28)
    dark_detail = darkness > 96
    feature = painted & ((saturation > 62) | warm_detail | cool_detail | green_detail | dark_detail)
    return {"painted": painted, "feature": feature}


def default_recipes() -> list[Recipe]:
    recipes = [
        Recipe("raw"),
        Recipe("uniform090-y50", art_scale=0.90, art_offset_y=50),
        Recipe("sx090-sy100-y50", art_scale=1.0, art_scale_x=0.90, art_scale_y=1.00, art_offset_y=50),
    ]
    for sx in (0.84, 0.86, 0.88, 0.90, 0.92):
        for sy in (0.96, 1.00, 1.04):
            for oy in (20, 40, 60, 80):
                recipes.append(Recipe(f"sx{sx:.2f}-sy{sy:.2f}-y{oy:+d}", art_scale=1.0, art_scale_x=sx, art_scale_y=sy, art_offset_y=oy))
    return recipes


def parse_float_list(value: str | None, fallback: list[float]) -> list[float]:
    if not value:
        return fallback
    return [float(item.strip()) for item in value.split(",") if item.strip()]


def parse_int_list(value: str | None, fallback: list[int]) -> list[int]:
    if not value:
        return fallback
    return [int(item.strip()) for item in value.split(",") if item.strip()]


def grid_recipes(x_scales: list[float], y_scales: list[float], y_offsets: list[int]) -> list[Recipe]:
    recipes: list[Recipe] = []
    for sx in x_scales:
        for sy in y_scales:
            for oy in y_offsets:
                recipes.append(Recipe(f"sx{sx:.2f}-sy{sy:.2f}-y{oy:+d}", art_scale=1.0, art_scale_x=sx, art_scale_y=sy, art_offset_y=oy))
    return recipes


def recipe_from_args(args: argparse.Namespace) -> Recipe:
    return Recipe(
        name=args.recipe_name,
        fit=args.fit,
        art_scale=args.art_scale,
        art_scale_x=args.art_scale_x,
        art_scale_y=args.art_scale_y,
        art_offset_x=args.art_offset_x,
        art_offset_y=args.art_offset_y,
    )


def region(mask_shape: tuple[int, int], bbox: tuple[int, int, int, int] | None, pad: int = 0) -> np.ndarray:
    out = np.zeros(mask_shape, dtype=bool)
    if bbox is None:
        return out
    height, width = mask_shape
    x0, y0, x1, y1 = bbox
    x0 = max(0, x0 - pad)
    y0 = max(0, y0 - pad)
    x1 = min(width - 1, x1 + pad)
    y1 = min(height - 1, y1 + pad)
    out[y0 : y1 + 1, x0 : x1 + 1] = True
    return out


def center_lane_bbox(red_bbox: tuple[int, int, int, int] | None, black_bbox: tuple[int, int, int, int] | None) -> tuple[int, int, int, int] | None:
    if red_bbox is None:
        return None
    rx0, ry0, rx1, ry1 = red_bbox
    if black_bbox is None:
        return rx0, ry0, rx1, ry1
    _, by0, _, by1 = black_bbox
    return rx0, min(ry0, by0), rx1, max(ry1, by1)


def score_image(image_path: Path, template_path: Path, recipe: Recipe, mode: str, make_debug: bool = False) -> tuple[Score, Image.Image | None]:
    source = Image.open(image_path).convert("RGBA")
    placed = scale_artwork(
        source,
        recipe.art_scale,
        recipe.art_offset_x,
        recipe.art_offset_y,
        scale_x=recipe.art_scale_x,
        scale_y=recipe.art_scale_y,
    )
    guides = guide_masks(template_path, placed.width, placed.height, recipe.fit)
    art = artwork_masks(placed)

    painted = art["painted"]
    feature = art["feature"]
    safe_bbox = mask_bbox(guides["yellow"])
    red_bbox = mask_bbox(guides["red"])
    black_bbox = mask_bbox(guides["black"])
    painted_bbox = mask_bbox(painted)
    feature_bbox = mask_bbox(feature)

    height, width = painted.shape
    side_region = np.zeros_like(painted)
    bottom_region = np.zeros_like(painted)
    left_gap = right_gap = bottom_gap = None
    if safe_bbox is not None:
        sx0, sy0, sx1, sy1 = safe_bbox
        side_region[:, :sx0] = True
        side_region[:, sx1 + 1 :] = True
        bottom_region[sy1 + 1 :, :] = True
        gap_bbox = feature_bbox or painted_bbox
        if gap_bbox is not None:
            px0, _, px1, py1 = gap_bbox
            left_gap = int(px0 - sx0)
            right_gap = int(sx1 - px1)
            bottom_gap = int(sy1 - py1)

    red_region = guides["red_dilated"]
    cutline_region = guides["black_dilated"]
    lane = region(painted.shape, center_lane_bbox(red_bbox, black_bbox), pad=6)

    side_area = int(side_region.sum())
    bottom_area = int(bottom_region.sum())
    lane_area = int(lane.sum())
    red_area = int(red_region.sum())
    cutline_area = int(cutline_region.sum())

    side_painted = pct(int((painted & side_region).sum()), side_area)
    side_feature = pct(int((feature & side_region).sum()), side_area)
    bottom_painted = pct(int((painted & bottom_region).sum()), bottom_area)
    bottom_feature = pct(int((feature & bottom_region).sum()), bottom_area)
    lane_painted = pct(int((painted & lane).sum()), lane_area)
    lane_feature = pct(int((feature & lane).sum()), lane_area)
    red_feature = pct(int((feature & red_region).sum()), red_area)
    cutline_feature = pct(int((feature & cutline_region).sum()), cutline_area)

    penalties: dict[str, float] = {}
    notes: list[str] = []

    def add(name: str, value: float, note: str | None = None) -> None:
        penalties[name] = round(value, 3)
        if note and value > 0:
            notes.append(note)

    if safe_bbox is None:
        add("missing_safe_bbox", 100.0, "yellow safe-area guide was not detected")
    if painted_bbox is None:
        add("missing_artwork", 100.0, "no painted artwork pixels were detected")

    if left_gap is not None:
        add("left_safe_violation", max(0.0, -left_gap) * 1.2, "paint crosses left safe guide")
    if right_gap is not None:
        add("right_safe_violation", max(0.0, -right_gap) * 1.2, "paint crosses right safe guide")
    if bottom_gap is not None:
        add("bottom_safe_violation", max(0.0, -bottom_gap) * 1.0, "paint crosses bottom safe guide")
        add("large_bottom_gap", max(0.0, bottom_gap - 80) * 0.2, "artwork sits too far above bottom safe guide")

    add("side_gutter_painted", side_painted * 0.6, "painted pixels in side gutter")
    add("side_gutter_feature", side_feature * 6.0, "high-detail/color pixels in side gutter")
    add("bottom_gutter_painted", bottom_painted * 0.35, "painted pixels in bottom gutter")
    add("bottom_gutter_feature", bottom_feature * 4.0, "high-detail/color pixels in bottom gutter")
    add("red_zone_feature", red_feature * 4.0, "feature detail in red keep-clear zones")
    add("cutline_feature", cutline_feature * 1.4, "feature detail close to black cut lines")

    if mode == "empty":
        add("center_lane_painted", max(0.0, lane_painted - 10.0) * 1.8, "empty-center lane is too painted")
        add("center_lane_feature", lane_feature * 4.0, "empty-center lane has feature detail")
    else:
        add("center_lane_underfilled", max(0.0, 55.0 - lane_painted) * 1.2, "wall-center lane is too blank")
        add("center_lane_feature", max(0.0, lane_feature - 5.0) * 3.5, "wall-center lane has too much feature detail")

    total_penalty = sum(penalties.values())
    score = max(0.0, round(100.0 - (total_penalty * 0.30), 2))
    has_safe_violation = any("violation" in key and value > 0 for key, value in penalties.items())
    if score >= 82 and not has_safe_violation:
        verdict = "PASS"
    elif score >= 55:
        verdict = "WARN"
    else:
        verdict = "FAIL"

    debug = None
    if make_debug:
        debug = build_debug_image(placed, guides, painted, feature, side_region, bottom_region, lane, red_region, cutline_region)
    score_obj = Score(
        image=str(image_path.relative_to(ROOT) if image_path.is_relative_to(ROOT) else image_path),
        recipe=recipe.name,
        mode=mode,
        score=score,
        verdict=verdict,
        left_safe_gap_px=left_gap,
        right_safe_gap_px=right_gap,
        bottom_safe_gap_px=bottom_gap,
        painted_bbox=list(painted_bbox) if painted_bbox else None,
        feature_bbox=list(feature_bbox) if feature_bbox else None,
        safe_bbox=list(safe_bbox) if safe_bbox else None,
        side_gutter_painted_pct=side_painted,
        side_gutter_feature_pct=side_feature,
        bottom_gutter_painted_pct=bottom_painted,
        bottom_gutter_feature_pct=bottom_feature,
        center_lane_painted_pct=lane_painted,
        center_lane_feature_pct=lane_feature,
        red_zone_feature_pct=red_feature,
        cutline_feature_pct=cutline_feature,
        penalties=penalties,
        notes=notes,
    )
    return score_obj, debug


def build_debug_image(
    placed: Image.Image,
    guides: dict[str, np.ndarray],
    painted: np.ndarray,
    feature: np.ndarray,
    side_region: np.ndarray,
    bottom_region: np.ndarray,
    lane: np.ndarray,
    red_region: np.ndarray,
    cutline_region: np.ndarray,
) -> Image.Image:
    debug = placed.convert("RGBA")
    overlay = Image.new("RGBA", debug.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)

    def tint(mask: np.ndarray, color: tuple[int, int, int, int]) -> None:
        layer = np.zeros((mask.shape[0], mask.shape[1], 4), dtype=np.uint8)
        layer[mask] = color
        debug.alpha_composite(Image.fromarray(layer))

    tint((painted & side_region) | (painted & bottom_region), (255, 0, 0, 72))
    tint(feature & lane, (0, 80, 255, 96))
    tint(feature & red_region, (255, 0, 255, 120))
    tint(feature & cutline_region, (255, 160, 0, 72))

    for mask, color in (
        (guides["yellow"], (255, 220, 0, 255)),
        (guides["red"], (255, 0, 0, 255)),
        (guides["black"], (0, 0, 0, 255)),
        (guides["green"], (0, 180, 40, 255)),
    ):
        ys, xs = np.where(mask)
        for x, y in zip(xs[::3], ys[::3]):
            draw.point((int(x), int(y)), fill=color)

    debug.alpha_composite(overlay)
    return debug.convert("RGB")


def write_json(path: Path, scores: list[Score]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [asdict(score) for score in scores]
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_markdown(path: Path, scores: list[Score], limit: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = sorted(scores, key=lambda item: item.score, reverse=True)[:limit]
    lines = [
        "# Template Fit Score Report",
        "",
        "| Rank | Verdict | Score | Image | Recipe | L gap | R gap | B gap | Side feature % | Center feature % | Red feature % | Notes |",
        "|---:|---|---:|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for index, item in enumerate(rows, start=1):
        notes = "; ".join(item.notes[:3])
        lines.append(
            "| {rank} | `{verdict}` | `{score:.2f}` | `{image}` | `{recipe}` | `{lg}` | `{rg}` | `{bg}` | `{side:.3f}` | `{center:.3f}` | `{red:.3f}` | {notes} |".format(
                rank=index,
                verdict=item.verdict,
                score=item.score,
                image=item.image,
                recipe=item.recipe,
                lg="" if item.left_safe_gap_px is None else item.left_safe_gap_px,
                rg="" if item.right_safe_gap_px is None else item.right_safe_gap_px,
                bg="" if item.bottom_safe_gap_px is None else item.bottom_safe_gap_px,
                side=item.side_gutter_feature_pct,
                center=item.center_lane_feature_pct,
                red=item.red_zone_feature_pct,
                notes=notes.replace("|", "/"),
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def iter_batch_images(path: Path) -> Iterable[Path]:
    if path.is_file():
        yield path
        return
    for item in sorted(path.glob("*.png")):
        if item.is_file():
            yield item


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("image", nargs="?", type=Path, help="Generated artwork PNG, or omit with --batch-generated")
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    parser.add_argument("--mode", choices=("wall", "empty"), default="wall")
    parser.add_argument("--fit", choices=("cover", "contain"), default="cover")
    parser.add_argument("--recipe-name", default="custom")
    parser.add_argument("--art-scale", type=float, default=1.0)
    parser.add_argument("--art-scale-x", type=float)
    parser.add_argument("--art-scale-y", type=float)
    parser.add_argument("--art-offset-x", type=int, default=0)
    parser.add_argument("--art-offset-y", type=int, default=0)
    parser.add_argument("--sweep", action="store_true", help="score the default placement recipe sweep")
    parser.add_argument("--x-scales", help="comma-separated horizontal scales for --sweep")
    parser.add_argument("--y-scales", help="comma-separated vertical scales for --sweep")
    parser.add_argument("--y-offsets", help="comma-separated y offsets for --sweep")
    parser.add_argument("--batch-generated", action="store_true", help="score every generated PNG in the castle task")
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--md-out", type=Path)
    parser.add_argument("--top", type=int, default=30)
    parser.add_argument("--debug-out", type=Path, help="debug image path for single-image scoring")
    parser.add_argument("--require-pass", action="store_true", help="exit nonzero unless the best scored recipe is PASS")
    parser.add_argument("--min-score", type=float, help="exit nonzero unless the best scored recipe meets this score")
    args = parser.parse_args()

    template = resolve(args.template)
    if args.batch_generated:
        images = list(iter_batch_images(DEFAULT_GENERATED))
    elif args.image:
        images = [resolve(args.image)]
    else:
        raise SystemExit("Provide an image or use --batch-generated.")

    if args.sweep and (args.x_scales or args.y_scales or args.y_offsets):
        recipes = grid_recipes(
            parse_float_list(args.x_scales, [0.84, 0.86, 0.88, 0.90, 0.92]),
            parse_float_list(args.y_scales, [0.96, 1.00, 1.04]),
            parse_int_list(args.y_offsets, [20, 40, 60, 80]),
        )
    else:
        recipes = default_recipes() if args.sweep else [recipe_from_args(args)]
    scores: list[Score] = []
    best_debug_score: Score | None = None
    best_debug_image: Path | None = None
    best_debug_recipe: Recipe | None = None
    for image in images:
        for recipe in recipes:
            score, _ = score_image(image, template, recipe, args.mode, make_debug=False)
            scores.append(score)
            if best_debug_score is None or score.score > best_debug_score.score:
                best_debug_score = score
                best_debug_image = image
                best_debug_recipe = recipe

    scores.sort(key=lambda item: item.score, reverse=True)

    if args.json_out:
        write_json(resolve(args.json_out), scores)
    if args.md_out:
        write_markdown(resolve(args.md_out), scores, args.top)
    if args.debug_out:
        if len(images) != 1:
            raise SystemExit("--debug-out is only supported for single-image scoring")
        assert best_debug_image is not None and best_debug_recipe is not None
        _, debug = score_image(best_debug_image, template, best_debug_recipe, args.mode, make_debug=True)
        assert debug is not None
        debug_path = resolve(args.debug_out)
        debug_path.parent.mkdir(parents=True, exist_ok=True)
        debug.save(debug_path)

    if len(scores) == 1 and not args.json_out:
        print(json.dumps(asdict(scores[0]), indent=2))
    else:
        for index, item in enumerate(scores[: args.top], start=1):
            print(
                f"{index:02d} {item.verdict:4s} {item.score:6.2f} {item.recipe:22s} "
                f"L={item.left_safe_gap_px} R={item.right_safe_gap_px} B={item.bottom_safe_gap_px} "
                f"{item.image}"
            )
    best = scores[0]
    if args.require_pass and best.verdict != "PASS":
        print(f"Best recipe did not pass: {best.verdict} {best.score:.2f} {best.recipe}")
        return 2
    if args.min_score is not None and best.score < args.min_score:
        print(f"Best score below minimum {args.min_score:.2f}: {best.score:.2f} {best.recipe}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
