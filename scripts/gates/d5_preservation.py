#!/usr/bin/env python3
"""d5_preservation.py — D5 protected-art preservation contract (blocking).

Implements the policy-aware "did the destructive route (chroma-key ->
decontam -> green_purge) delete real protected art" gate described in
`tasks/transparent-bg-endgame/CALIBRATION.md` (D5 section) and the D5
blocking-contract spec landed alongside this module. This is a pure
computation module: masks, component scoring, the pre-purge palette
precheck, and verdict logic. `scripts/gates/gate_battery.py` wires it into
the CLI/battery surface; `scripts/run_c_green_v2.py` wires it into the
two-phase pre-purge-stop / approved-purge runner.

Three reference modes, strongest first:
  - truth:    an exact hand-authored/synthetic RGBA truth mask is supplied.
  - baseline: a human-approved pre-purge raster's alpha is intersected with
              source-color evidence (flood/disagreement-recovery structure
              without ML: color identifies paint, the reviewed baseline
              supplies an independent second view).
  - source_only: source-color component evidence alone (no baseline/truth).

All three are BLOCKING (a real FAIL prevents shipping); a separate, older,
"legacy source-only" heuristic (deleted-area-fraction only, no per-component
recall/skeleton scrutiny) remains available to `gate_battery.py` for
backward-compatible advisory-only callers that do not opt into the new
`--d5-*` flags.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

import numpy as np
from scipy import ndimage as ndi
from skimage.color import deltaE_ciede2000, rgb2lab
from skimage.morphology import skeletonize

CONN8 = np.ones((3, 3), dtype=bool)


# ---------------------------------------------------------------------------
# Config / result types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class D5Thresholds:
    analysis_scale: float
    boundary_budget_px: float
    palette_policy: Literal["preserve-all", "no-green-art"] = "no-green-art"


@dataclass
class D5Component:
    label: int
    area_px: int
    max_inscribed_radius_px: float
    kind: Literal["anchor", "fine", "speck"]


@dataclass
class D5Reference:
    """Protected-core reference mask plus per-component metadata.

    `support` is the FULL (un-eroded) protected-core mask. The boundary
    budget is applied at scoring time (`score_preservation`), not baked in
    here, so the same reference can be (mis)scored with different budgets --
    exactly the scale-metadata sensitivity the spec calls out.
    """

    support: np.ndarray  # bool HxW
    labels: np.ndarray  # int HxW, 0 = not-support
    components: list[D5Component]
    mode: Literal["truth", "baseline", "source_only"]
    excluded_mask: np.ndarray  # bool HxW — policy-excluded (key-hue) pixels, informational
    key_rgb: tuple[int, int, int]
    delta_e: np.ndarray | None = field(default=None, repr=False)


@dataclass
class D5Result:
    verdict: Literal["PASS", "REVIEW", "FAIL"]
    metric: dict[str, Any]
    mask: np.ndarray | None = field(default=None, repr=False)


# ---------------------------------------------------------------------------
# Small shared utilities (self-contained -- this module must not import
# gate_battery.py, which delegates D5 to this module).
# ---------------------------------------------------------------------------


def _delta_e00_to_key(rgb: np.ndarray, key_rgb: tuple[int, int, int]) -> np.ndarray:
    lab = rgb2lab(rgb.astype(np.float32) / 255.0)
    key_lab = rgb2lab(np.array(key_rgb, dtype=np.float32).reshape(1, 1, 3) / 255.0)
    return deltaE_ciede2000(lab, key_lab)


def _border_connected(mask: np.ndarray) -> np.ndarray:
    labels, n = ndi.label(mask, structure=CONN8)
    if n == 0:
        return np.zeros_like(mask, dtype=bool)
    border_labels = np.unique(np.concatenate([labels[0, :], labels[-1, :], labels[:, 0], labels[:, -1]]))
    border_labels = border_labels[border_labels != 0]
    return np.isin(labels, border_labels)


def _max_inscribed_radius(mask: np.ndarray) -> float:
    if not mask.any():
        return 0.0
    return float(ndi.distance_transform_edt(mask).max())


def _padded_slice(sl: tuple[slice, slice], shape: tuple[int, int], pad: int = 2) -> tuple[slice, slice]:
    """Expand a `find_objects` bounding-box slice by `pad` px (clipped to
    array bounds). A tight bbox slice for a component that fills its own
    bounding box (a solid rectangle) has NO zero/background pixels inside
    the crop, so `distance_transform_edt` on that crop alone is meaningless
    -- it needs a visible background margin to measure distance against."""
    h, w = shape
    y0 = max(0, sl[0].start - pad)
    y1 = min(h, sl[0].stop + pad)
    x0 = max(0, sl[1].start - pad)
    x1 = min(w, sl[1].stop + pad)
    return (slice(y0, y1), slice(x0, x1))


def _max_run(mask: np.ndarray) -> int:
    """Longest contiguous horizontal or vertical run of True in `mask`."""
    best = 0
    for axis in (0, 1):
        arr = mask if axis == 0 else mask.T
        for row in arr:
            if not row.any():
                continue
            padded = np.pad(row.astype(np.int8), (1, 1), constant_values=0)
            changes = np.diff(padded)
            starts = np.nonzero(changes == 1)[0]
            ends = np.nonzero(changes == -1)[0]
            if len(starts):
                best = max(best, int((ends - starts).max()))
    return best


def _decide_three_zone(value: float, pass_ok: float, fail_bad: float, higher_is_bad: bool) -> str:
    if higher_is_bad:
        if value <= pass_ok:
            return "PASS"
        if value >= fail_bad:
            return "FAIL"
    else:
        if value >= pass_ok:
            return "PASS"
        if value <= fail_bad:
            return "FAIL"
    return "REVIEW"


def _worst_verdict(verdicts: list[str]) -> str:
    if "FAIL" in verdicts:
        return "FAIL"
    if "REVIEW" in verdicts:
        return "REVIEW"
    return "PASS"


def _rgb_saturation(rgb: np.ndarray) -> np.ndarray:
    """Standard HSV saturation, (max-min)/max, 0 where max==0."""
    r = rgb[..., 0].astype(np.float32)
    g = rgb[..., 1].astype(np.float32)
    b = rgb[..., 2].astype(np.float32)
    cmax = np.maximum(np.maximum(r, g), b)
    cmin = np.minimum(np.minimum(r, g), b)
    sat = np.zeros_like(cmax)
    nonzero = cmax > 0
    sat[nonzero] = (cmax[nonzero] - cmin[nonzero]) / cmax[nonzero]
    return sat


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------


def policy_exclusion_mask(
    rgb: np.ndarray,
    key_rgb: tuple[int, int, int],
    policy: str,
) -> np.ndarray:
    """Pixels the destructive route is ALLOWED to treat as key-hue and purge
    unconditionally -- never counted as deleted protected art.

    `preserve-all`: only literal near-key pixels (ΔE00(key) < 11).
    `no-green-art`: additionally excludes any green-dominant hue, since the
    prompt/route guaranteed the subject contains no essential green content.
    """
    if policy not in {"preserve-all", "no-green-art"}:
        raise ValueError(f"invalid palette_policy {policy!r}")
    de = _delta_e00_to_key(rgb, key_rgb)
    near_key = de < 11.0
    if policy == "preserve-all":
        return near_key
    r = rgb[..., 0].astype(np.int16)
    g = rgb[..., 1].astype(np.int16)
    b = rgb[..., 2].astype(np.int16)
    g_dominant = g - np.maximum(r, b)
    green_hue = (g_dominant > 25) & (np.abs(r - b) < 45) & (g > 45)
    return near_key | green_hue


def _classify_components(
    support: np.ndarray,
    boundary_budget_px: float,
    scale: float,
) -> tuple[np.ndarray, list[D5Component]]:
    labels, n = ndi.label(support, structure=CONN8)
    components: list[D5Component] = []
    radius_thresh = boundary_budget_px + scale
    slices = ndi.find_objects(labels)
    for lbl, sl in enumerate(slices, start=1):
        if sl is None:
            continue
        comp = labels[sl] == lbl
        area = int(comp.sum())
        padded_sl = _padded_slice(sl, support.shape, pad=2)
        radius = _max_inscribed_radius(labels[padded_sl] == lbl)
        kind = "anchor" if radius > radius_thresh else "fine"
        components.append(D5Component(label=lbl, area_px=area, max_inscribed_radius_px=radius, kind=kind))
    return labels, components


def build_d5_reference(
    source_rgb: np.ndarray,
    baseline_rgba: np.ndarray | None,
    *,
    truth_rgba: np.ndarray | None,
    key_rgb: tuple[int, int, int],
    cfg: D5Thresholds,
) -> D5Reference:
    """Build the protected-core reference mask. `truth_rgba` (exact oracle)
    takes precedence over `baseline_rgba` (human-approved second view)."""
    scale = cfg.analysis_scale
    h, w = source_rgb.shape[:2]

    if truth_rgba is not None:
        support = truth_rgba[..., 3] > 127
        min_area = 16.0 * scale * scale
        labels0, n0 = ndi.label(support, structure=CONN8)
        keep = np.zeros_like(support)
        sizes = ndi.sum(support, labels0, index=range(1, n0 + 1)) if n0 else []
        for i, size in enumerate(sizes, start=1):
            if size >= min_area:
                keep |= labels0 == i
        labels, components = _classify_components(keep, cfg.boundary_budget_px, scale)
        return D5Reference(
            support=keep,
            labels=labels,
            components=components,
            mode="truth",
            excluded_mask=np.zeros((h, w), dtype=bool),
            key_rgb=key_rgb,
        )

    de = _delta_e00_to_key(source_rgb, key_rgb)
    paper = _border_connected(de <= 11.0)
    excluded = policy_exclusion_mask(source_rgb, key_rgb, cfg.palette_policy)
    candidate = (~paper) & (~excluded)

    src_labels, n = ndi.label(candidate, structure=CONN8)
    min_area = 16.0 * scale * scale
    qualified = np.zeros((h, w), dtype=bool)
    slices = ndi.find_objects(src_labels)
    for lbl, sl in enumerate(slices, start=1):
        if sl is None:
            continue
        comp = src_labels[sl] == lbl
        area = int(comp.sum())
        if area < min_area:
            continue
        comp_de = de[sl][comp]
        median_de = float(np.median(comp_de))
        p10_de = float(np.percentile(comp_de, 10))
        if median_de < 18.0 or p10_de < 14.0:
            continue
        qualified[sl] |= comp

    if baseline_rgba is not None:
        baseline_support = baseline_rgba[..., 3] > 127
        final_support = qualified & baseline_support
        mode: Literal["truth", "baseline", "source_only"] = "baseline"
    else:
        final_support = qualified
        mode = "source_only"

    labels, components = _classify_components(final_support, cfg.boundary_budget_px, scale)
    return D5Reference(
        support=final_support,
        labels=labels,
        components=components,
        mode=mode,
        excluded_mask=excluded,
        key_rgb=key_rgb,
        delta_e=de,
    )


def score_no_green_art(
    baseline_rgba: np.ndarray,
    *,
    cfg: D5Thresholds,
) -> D5Result:
    """Pre-purge palette stop: verify `NO_GREEN_ART` on the decontaminated
    pre-purge raster instead of trusting the prompt. Ignores a
    `6 * scale` px band around the alpha boundary (edge spill there is
    expected and is exactly what green_purge exists to remove), then flags
    any INTERIOR prohibited-green component."""
    scale = cfg.analysis_scale
    rgb = baseline_rgba[..., :3]
    alpha = baseline_rgba[..., 3]
    support = alpha > 127
    band_px = 6.0 * scale

    if support.any():
        dist_in = ndi.distance_transform_edt(support)
        interior = support & (dist_in > band_px)
    else:
        interior = np.zeros_like(support)

    r = rgb[..., 0].astype(np.int16)
    g = rgb[..., 1].astype(np.int16)
    b = rgb[..., 2].astype(np.int16)
    g_dominant = g - np.maximum(r, b)
    sat = _rgb_saturation(rgb)
    prohibited = (g >= 100) & (g_dominant >= 30) & (sat >= 0.45) & (np.abs(r.astype(np.int32) - b.astype(np.int32)) <= 60)
    green = interior & prohibited

    labels, n = ndi.label(green, structure=CONN8)
    max_area = 0
    max_radius = 0.0
    components_metric = []
    slices = ndi.find_objects(labels)
    for lbl, sl in enumerate(slices, start=1):
        if sl is None:
            continue
        comp = labels[sl] == lbl
        area = int(comp.sum())
        padded_sl = _padded_slice(sl, green.shape, pad=2)
        radius = _max_inscribed_radius(labels[padded_sl] == lbl)
        components_metric.append({"label": lbl, "area_px": area, "radius_px": round(radius, 3)})
        max_area = max(max_area, area)
        max_radius = max(max_radius, radius)

    pass_area = 16.0 * scale * scale
    pass_radius = 1.0 * scale
    fail_area = 64.0 * scale * scale
    fail_radius = 3.0 * scale

    if max_area <= pass_area and max_radius <= pass_radius:
        verdict = "PASS"
    elif max_area >= fail_area or max_radius >= fail_radius:
        verdict = "FAIL"
    else:
        verdict = "REVIEW"

    metric = {
        "scale": scale,
        "edge_band_px": band_px,
        "interior_px": int(interior.sum()),
        "prohibited_green_px": int(green.sum()),
        "max_component_area_px": max_area,
        "max_component_radius_px": round(max_radius, 3),
        "thresholds": {
            "pass_area_max_px": pass_area,
            "pass_radius_max_px": pass_radius,
            "fail_area_min_px": fail_area,
            "fail_radius_min_px": fail_radius,
        },
        "components": sorted(components_metric, key=lambda c: -c["area_px"])[:8],
    }
    return D5Result(verdict=verdict, metric=metric, mask=green if green.any() else None)


def score_preservation(
    final_rgba: np.ndarray,
    reference: D5Reference,
    *,
    cfg: D5Thresholds,
) -> D5Result:
    """Score `final_rgba` (post-purge delivered art) against a D5Reference.
    The permitted boundary band (`cfg.boundary_budget_px`) is removed from
    the reference before recall is measured -- that band is the erosion
    `green_purge --erode` is explicitly allowed to spend."""
    scale = cfg.analysis_scale
    budget = cfg.boundary_budget_px
    final_support = final_rgba[..., 3] > 127

    if not reference.support.any():
        metric = {"mode": reference.mode, "note": "empty reference -- nothing to preserve", "n_components": 0}
        return D5Result(verdict="PASS", metric=metric)

    dist_in = ndi.distance_transform_edt(reference.support)
    core = reference.support & (dist_in > budget)

    deleted_core = core & ~final_support

    if core.any():
        aggregate_recall = float((core & final_support).sum() / core.sum())
    else:
        aggregate_recall = 1.0

    anchor_recalls: list[dict[str, Any]] = []
    fine_losses: list[dict[str, Any]] = []
    any_anchor_lost = False
    for comp in reference.components:
        comp_mask_full = reference.labels == comp.label
        comp_core = comp_mask_full & core
        extent = comp_core if comp_core.any() else comp_mask_full
        overlap = int((extent & final_support).sum())
        denom = int(extent.sum())
        recall_i = float(overlap / denom) if denom else 1.0
        if comp.kind == "anchor":
            anchor_recalls.append(
                {"label": comp.label, "area_px": comp.area_px, "radius_px": round(comp.max_inscribed_radius_px, 3), "recall": round(recall_i, 6)}
            )
            if recall_i <= 0.0:
                any_anchor_lost = True
        else:
            full_overlap = int((comp_mask_full & final_support).sum())
            full_recall = float(full_overlap / comp.area_px) if comp.area_px else 1.0
            if full_recall < 0.999:
                fine_losses.append(
                    {"label": comp.label, "area_px": comp.area_px, "recall": round(full_recall, 6)}
                )

    min_anchor_recall = min((c["recall"] for c in anchor_recalls), default=1.0)

    island_labels, n_islands = ndi.label(deleted_core, structure=CONN8)
    max_island_area = 0
    max_island_radius = 0.0
    if n_islands:
        sizes = ndi.sum(deleted_core, island_labels, index=range(1, n_islands + 1))
        max_island_area = int(max(sizes)) if len(sizes) else 0
        max_island_radius = _max_inscribed_radius(deleted_core)

    # Skeletonize the boundary-budget-eroded core, not the raw reference
    # support: the outermost boundary band is the erosion the purge route is
    # explicitly allowed to spend, so skeleton branches that only exist in
    # that permitted band must not register as a severed bridge.
    skeleton = skeletonize(core) if core.any() else core
    missing_skel = skeleton & (~final_support)
    max_missing_run = _max_run(missing_skel) if missing_skel.any() else 0

    agg_verdict = _decide_three_zone(aggregate_recall, 0.9995, 0.995, higher_is_bad=False)
    anchor_verdict = _decide_three_zone(min_anchor_recall, 0.995, 0.98, higher_is_bad=False) if anchor_recalls else "PASS"
    island_verdict = _decide_three_zone(float(max_island_area), 0.0, 16.0 * scale * scale, higher_is_bad=True)
    radius_verdict = _decide_three_zone(max_island_radius, 0.0, 2.0 * scale, higher_is_bad=True)
    skeleton_verdict = _decide_three_zone(float(max_missing_run), 0.0, 3.0 * scale, higher_is_bad=True)
    lost_verdict = "FAIL" if any_anchor_lost else "PASS"
    fine_verdict = "REVIEW" if fine_losses else "PASS"

    verdict = _worst_verdict(
        [agg_verdict, anchor_verdict, island_verdict, radius_verdict, skeleton_verdict, lost_verdict, fine_verdict]
    )

    metric = {
        "mode": reference.mode,
        "scale": scale,
        "boundary_budget_px": budget,
        "reference_support_px": int(reference.support.sum()),
        "core_px": int(core.sum()),
        "aggregate_core_recall": round(aggregate_recall, 6),
        "aggregate_verdict": agg_verdict,
        "min_anchor_component_recall": round(min_anchor_recall, 6),
        "anchor_verdict": anchor_verdict,
        "anchor_components": sorted(anchor_recalls, key=lambda c: c["recall"])[:8],
        "any_anchor_component_entirely_lost": any_anchor_lost,
        "fine_components_lossy": fine_losses[:8],
        "deleted_core_max_island_area_px": max_island_area,
        "deleted_core_max_island_radius_px": round(max_island_radius, 3),
        "missing_skeleton_run_px": max_missing_run,
        "n_anchor_components": len(anchor_recalls),
        "n_fine_components": sum(1 for c in reference.components if c.kind == "fine"),
    }
    mask = deleted_core if deleted_core.any() else None
    return D5Result(verdict=verdict, metric=metric, mask=mask)
