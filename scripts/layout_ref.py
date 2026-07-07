#!/usr/bin/env python3
"""layout_ref.py — render a MODEL-FACING layout reference + a HUMAN diagram from a
feature-callouts YAML (tasks/<task>/style-spec/feature-callouts-*.yaml).

ROUND 2 (v2): the guides now also carry the DOOR-ANCHOR SECTION and the panel
HOLES, sourced from the TRUE template contract at
tasks/marriott-hospital/geometry/v3/door-spec.json and door-holes.png — round-1
verdict was "big oversight: anchor absent, wrong door proportions in all 10
results". door-spec.json's door_anchor_frac == [0.2705, 0.4001, 0.7293, 0.9864]
(x0,y0,x1,y1) is the SAME anchor cited in the door callouts YAML header comment
("Door anchor: x 0.271-0.729, y 0.400-0.986") — both point at the arch region
traced from the template's orange path; door-spec.json is the machine source
of truth used here (see _load_door_anchor). door-holes.png (6 connected white
components) is the machine source for the 6 hole voids (see _load_door_holes).
Both are rendered as a SOLID (no dashes) closed door shape / white+ring holes
in BOTH the model and geometry-only variants — see render_model /
render_geometry_only / _draw_door_anchor / _draw_holes.

Borrows the spec-is-the-contract pattern from scripts/skyline_panel.py
(panel_spec/cmd_guide: one geometry contract feeds both a gen-facing guide and a
human-facing check) and scripts/master_spec.py (grey-body silhouette = paint here;
forbidden stripes parsed as solid bands, not the dashed/annotation source).

MODEL-FACING output (--out-model): grey panel silhouette + each feature zone as a
SOLID mid-grey shape (no text, no dashes — dashes leak as painted dots, per the
solid-strokes-only rule / commit 4d93530). Forbidden stripes are OMITTED
entirely from this output — the body stays continuous grey there. Drawing them
as literal white channels/holes was itself a template mark that generators
painted as literal white slots (proven failure class); the model-facing render
must give the generator nothing to trace, so the void geometry is dropped, not
rendered white (round-2 fix).

Features with count>1 are drawn as COUNT separate disjoint shapes spanning the
zone's horizontal extremes (e.g. count=2 -> two small shapes flanking the zone,
not one shape spanning it) — see _feature_boxes.

HUMAN output (--out-human): the same panel + zones, PLUS text labels (feature_id)
and the forbidden stripes drawn as a distinct (red) tone, for a person to review.
The human diagram is the only place the forbidden-stripe geometry is rendered.

CLI:
  python3 scripts/layout_ref.py --callouts <yaml> --panel-size WxH \
      --out-model <png> --out-human <png>
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import numpy as np
import yaml
from PIL import Image, ImageDraw, ImageFont

BODY_GREY = (200, 200, 200, 255)
CONTOUR = (45, 45, 45, 255)
ZONE_FILL = (140, 140, 140, 255)   # solid mid-grey — architecture/prop/detail zones
ZONE_OUTLINE = (90, 90, 90, 255)
FRAME_RING = (110, 110, 110, 255)  # thin solid frame around a paintable void
FORBIDDEN_HUMAN = (230, 40, 40, 160)
LABEL_COLOR = (20, 20, 20, 255)
DOOR_ANCHOR_OUTLINE = (60, 60, 60, 255)   # solid door-shape contour + split line
DOOR_FILL = (110, 110, 110, 255)   # a step darker than ZONE_FILL — clearly distinct door tone
DOOR_RIM = (75, 75, 75, 255)   # a step darker than DOOR_FILL — the frame-on-the-cut-line band

# geometry-embrace void min size, in fraction of panel width, below which a ring
# would be imperceptible; frame ring width scales off the smaller panel dimension
FRAME_MIN_PX = 2

# door art never reaches panel bottom — the door shape's bottom edge sits this
# fraction of panel HEIGHT above the anchor's own bottom edge (user rule: flaps
# carry only door content, art must not run to the panel floor). round-3
# (round-2b verdict, ledger S147): user wants "as little a gap as possible, or
# no gap" — the illustration must reach the template bottom — so the margin is
# cut from 4% to 1% (kept nonzero only to avoid a razor-thin/1px seam at the
# anchor's exact bottom edge).
DOOR_BOTTOM_MARGIN_FRAC = 0.01

# round-3 (round-2b verdict, ledger S147, item 2): an explicit door-RIM band
# that STRADDLES the portal-mask edge (half outside, half inside), in a tone
# slightly darker than the door fill — teaches the model "the frame sits ON
# the cut line" (user: rim must go OVER the contour/door-area lines), rather
# than the previous render where the door fill's own edge WAS the portal edge
# with no frame overlap. Width is a fraction of panel WIDTH (rim thickness
# should not scale with the panel's tall aspect).
DOOR_RIM_BAND_FRAC = 0.015

# TRUE template contract for the door anchor + door holes (round-1 verdict:
# anchor absence = "big oversight"). Never hand-invent a bbox — these paths are
# the actual traced-from-template geometry.
DOOR_SPEC_JSON = (Path(__file__).resolve().parents[1]
                  / "tasks/marriott-hospital/geometry/v3/door-spec.json")
DOOR_HOLES_PNG = (Path(__file__).resolve().parents[1]
                   / "tasks/marriott-hospital/geometry/v3/door-holes.png")
DOOR_CONTROL_PNG = (Path(__file__).resolve().parents[1]
                     / "tasks/marriott-hospital/geometry/v3/door-control.png")

# round-2 fix (portal-vs-frame inset defect): overlay evidence showed the
# drawn door INSET ~2-3% per side vs the TRUE anchor traced in door-control.png
# — the previous renderer drew "leaves inside a frame" instead of the full
# portal. _load_door_portal_mask() below TRACES door-control.png directly
# (flood-fills the closed arch+sides+bottom path into a boolean mask) instead
# of ever synthesizing a bbox/pieslice by hand — see _draw_door_anchor, which
# now stamps this exact mask instead of drawing a synthetic arch shape.
CACHED_PORTAL_MASK_PNG = (Path(__file__).resolve().parents[1]
                           / "tasks/workflow-rebuild/refs/demo-layout/door-portal-mask.png")

_FORBIDDEN_RE = re.compile(
    r"([0-9]*\.?[0-9]+)\s*-\s*([0-9]*\.?[0-9]+)"
)


def parse_panel_size(spec: str) -> tuple[int, int]:
    w, h = (int(v) for v in spec.lower().split("x"))
    return w, h


def load_callouts(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["_forbidden_bands_frac"] = _forbidden_bands_from_comment(path)
    return data


def _forbidden_bands_from_comment(path: Path) -> list[tuple[float, float]]:
    """The callouts YAML only records forbidden stripes as prose in a header
    comment (e.g. "...Forbidden stripes:\n# x 0.143-0.184 and 0.816-0.857...")
    — there is no machine field, and the ranges can land on the line AFTER the
    word "forbidden" wraps. Join contiguous leading '#' comment lines into one
    blob and pull the x-ranges after the "forbidden" keyword; this is the only
    void geometry the callouts file carries, so it doubles as the cutout-void
    source."""
    comment_lines = [ln.lstrip("#").strip() for ln in path.read_text(encoding="utf-8").splitlines()
                      if ln.lstrip().startswith("#")]
    blob = " ".join(comment_lines)
    idx = blob.lower().find("forbidden")
    if idx == -1:
        return []
    tail = blob[idx:]
    # stop at the sentence-ending period (". " followed by a capital letter,
    # e.g. "...there). Door anchor: ..." — a bare "." also matches inside a
    # decimal number like "0.143", so that alone would truncate too early)
    end_m = re.search(r"\.\s+[A-Z]", tail)
    if end_m:             # later sentences (e.g. "Door anchor: x 0.27-0.73")
        tail = tail[: end_m.start() + 1]   # aren't stripes
    bands: list[tuple[float, float]] = []
    for m in _FORBIDDEN_RE.finditer(tail):
        lo, hi = float(m.group(1)), float(m.group(2))
        if 0.0 <= lo < hi <= 1.0:
            bands.append((lo, hi))
    return bands


def _load_door_anchor(spec_path: Path = DOOR_SPEC_JSON) -> tuple[float, float, float, float]:
    """TRUE door-anchor bbox (x0,y0,x1,y1 frac) from the v3 template contract's
    door-spec.json: door_anchor_frac == [0.2705, 0.4001, 0.7293, 0.9864] — the
    arch region traced from the template's orange path, the same anchor cited
    in the door callouts YAML header comment ("Door anchor: x 0.271-0.729,
    y 0.400-0.986"). Never hand-invented."""
    import json
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    x0, y0, x1, y1 = spec["door_anchor_frac"]
    return (x0, y0, x1, y1)


def _load_door_holes(holes_path: Path = DOOR_HOLES_PNG) -> list[tuple[float, float, float, float]]:
    """TRUE hole geometry from the v3 template contract's door-holes.png: 6
    white (255) connected components on a black field, one bbox per hole,
    returned as (x0,y0,x1,y1) fractions of the holes-image size. Matches
    door-spec.json's holes_n == 6. Never hand-invented."""
    import numpy as np
    from collections import deque
    img = Image.open(holes_path)
    arr = np.array(img.convert("L"))
    mask = arr > 200
    hh, ww = mask.shape
    seen = np.zeros_like(mask, bool)
    boxes = []
    ys, xs = np.where(mask)
    for y0, x0 in zip(ys.tolist(), xs.tolist()):
        if seen[y0, x0]:
            continue
        comp_ys, comp_xs = [], []
        dq = deque([(y0, x0)])
        seen[y0, x0] = True
        while dq:
            y, x = dq.popleft()
            comp_ys.append(y)
            comp_xs.append(x)
            for ny, nx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                if 0 <= ny < hh and 0 <= nx < ww and mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    dq.append((ny, nx))
        bx0, bx1 = min(comp_xs), max(comp_xs)
        by0, by1 = min(comp_ys), max(comp_ys)
        boxes.append((bx0 / ww, by0 / hh, (bx1 + 1) / ww, (by1 + 1) / hh))
    return boxes


def _load_door_portal_mask(control_path: Path = DOOR_CONTROL_PNG) -> "np.ndarray":
    """TRUE door-PORTAL mask, traced from door-control.png (never a hand-
    synthesized bbox/pieslice — binding rule for the round-2 inset-defect fix).
    door-control.png's arch + sides + bottom form a closed white outline; a
    9x9 binary-closing bridges the sub-pixel rasterization gaps at the
    corners (the traced curve's stroke drops to <9px width at the bottom-left
    /bottom-right corners — without closing, a flood-fill leaks past the door
    into the flanking jamb region), then a connected-components flood of the
    resulting black regions isolates the two door-leaf interiors.

    Component selection is purely geometric (no hand-picked labels/spec
    values): the two vertical JAMB STRIPS either side of the door are found
    first (the only enclosed components that are narrow (<60px) and tall
    (>500px) — a jamb-strip-shaped signature), which defines a horizontal
    "door corridor" between them. The door-leaf interiors are then the two
    largest enclosed components that fit ENTIRELY inside that corridor — this
    also naturally excludes (a) the wide components that wrap a leaf AND the
    flanking outer-margin strip into one blob (the jamb sits between them, so
    they straddle the corridor boundary) and (b) the smaller enclosed sliver
    above the arch springline, which belongs to a separate decorative
    pediment/header line. Returns a boolean array in door-control.png's own
    pixel grid (2400x1692) — callers resize with PIL to the target panel
    size."""
    import numpy as np
    from scipy import ndimage
    arr = np.array(Image.open(control_path).convert("L"))
    white = arr > 100
    closed = ndimage.binary_closing(white, structure=np.ones((9, 9)))
    black = ~closed
    lbl, n = ndimage.label(black, structure=np.ones((3, 3)))
    sizes = ndimage.sum(np.ones_like(lbl), lbl, index=np.arange(1, n + 1))
    bg_label = lbl[0, 0]

    jamb_x_ranges = []
    for i in range(1, n + 1):
        if i == bg_label or sizes[i - 1] < 1000:
            continue
        ys, xs = np.where(lbl == i)
        bw, bh = xs.max() - xs.min(), ys.max() - ys.min()
        if bw < 60 and bh > 500:
            jamb_x_ranges.append((xs.min(), xs.max()))
    jamb_x_ranges.sort()
    corridor_x0 = jamb_x_ranges[0][1]
    corridor_x1 = jamb_x_ranges[-1][0]

    candidates = []
    for i in range(1, n + 1):
        if i == bg_label or sizes[i - 1] < 5000:
            continue
        ys, xs = np.where(lbl == i)
        if xs.min() >= corridor_x0 and xs.max() <= corridor_x1:
            candidates.append((i, sizes[i - 1]))
    candidates.sort(key=lambda c: c[1], reverse=True)
    leaf_labels = [i for i, _ in candidates[:2]]
    return np.isin(lbl, leaf_labels)


def _door_portal_mask_bbox_frac(mask: "np.ndarray") -> tuple[float, float, float, float]:
    """Bbox of a boolean portal mask, as (x0,y0,x1,y1) fractions of its own
    canvas size — used to pixel-verify the traced mask against
    door-spec.json's door_anchor_frac (SPEC: within 0.5% per edge)."""
    import numpy as np
    h, w = mask.shape
    ys, xs = np.where(mask)
    return (xs.min() / w, ys.min() / h, (xs.max() + 1) / w, (ys.max() + 1) / h)


def _door_portal_mask_for_panel(w: int, h: int) -> "Image.Image":
    """Portal mask resized (nearest, to keep it a hard silhouette) to the
    target WxH panel canvas, as a PIL 'L' image (255 = door interior)."""
    mask = _load_door_portal_mask()
    img = Image.fromarray((mask * 255).astype("uint8"))
    return img.resize((w, h), Image.NEAREST)


def _door_anchor_box_px(anchor_frac, w: int, h: int) -> tuple[int, int, int, int]:
    """Pixel box for the door-shape anchor, with the bottom edge pulled up
    DOOR_BOTTOM_MARGIN_FRAC * panel-height above the anchor's own bottom edge
    (user rule: door art never reaches panel bottom; flaps carry only door
    content)."""
    x0f, y0f, x1f, y1f = anchor_frac
    x0, y0, x1 = int(round(x0f * w)), int(round(y0f * h)), int(round(x1f * w))
    y1 = int(round(y1f * h - DOOR_BOTTOM_MARGIN_FRAC * h))
    return (x0, y0, x1, y1)


def _door_rim_band_mask(mask_arr: "np.ndarray", w: int, h: int) -> "np.ndarray":
    """Boolean band that STRADDLES the (bottom-cropped) portal-mask edge —
    half outside the mask, half inside — around the FULL portal perimeter
    (arch + sides; at the bottom the mask is already cropped to the
    DOOR_BOTTOM_MARGIN_FRAC zone, so the band naturally stays within it
    there, same treatment as the rest of the perimeter). round-3 (round-2b
    verdict, ledger S147, item 2): teaches the model "the frame sits ON the
    cut line" rather than the fill's own edge coinciding with the portal
    boundary with no overlap. Band total width = DOOR_RIM_BAND_FRAC * panel
    width, split evenly outside/inside via one dilation + one erosion of the
    same half-width, both centered on the mask boundary."""
    from scipy import ndimage
    half = max(1, int(round(DOOR_RIM_BAND_FRAC * w / 2)))
    mask_bool = mask_arr > 0
    struct = np.ones((2 * half + 1, 2 * half + 1))
    dilated = ndimage.binary_dilation(mask_bool, structure=struct)
    eroded = ndimage.binary_erosion(mask_bool, structure=struct)
    return dilated & ~eroded


def _draw_door_anchor(img: Image.Image, d: ImageDraw.ImageDraw, anchor_frac, w: int, h: int):
    """FULL PORTAL fill (round-2 inset-defect fix): the door is now the exact
    TRUE portal mask traced from door-control.png (see
    _load_door_portal_mask), never a synthesized bbox/pieslice — the previous
    pieslice+rect approximation drew "leaves inside a frame" that measured
    ~2-3% inset per side vs the true anchor on overlay review. The mask is
    resized to the panel canvas, then cropped at DOOR_BOTTOM_MARGIN_FRAC above
    the anchor's own bottom edge (same margin rule as before: door art never
    reaches the panel floor) before being stamped as a solid DOOR_FILL region
    — a step darker than ZONE_FILL so the door reads as a distinct fill tone.
    A door-RIM band straddling the portal-mask edge (round-3, ledger S147
    item 2) is stamped next in DOOR_RIM (a step darker than DOOR_FILL), then
    a thin solid center split line (true leaf geometry) is drawn on top."""
    anchor_x0, anchor_y0, anchor_x1, anchor_y1 = _door_anchor_box_px(anchor_frac, w, h)
    mask_img = _door_portal_mask_for_panel(w, h)
    # crop the mask to the bottom-margin rule: blank out rows below the
    # margin-adjusted bottom edge (anchor_y1 already has the margin applied)
    import numpy as np
    mask_arr = np.array(mask_img)
    mask_arr[anchor_y1:, :] = 0
    fill_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    fill_layer.paste(Image.new("RGBA", (w, h), DOOR_FILL), (0, 0), Image.fromarray(mask_arr))
    img.paste(fill_layer, (0, 0), fill_layer)
    rim_mask = _door_rim_band_mask(mask_arr, w, h)
    rim_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    rim_layer.paste(Image.new("RGBA", (w, h), DOOR_RIM), (0, 0),
                     Image.fromarray((rim_mask * 255).astype("uint8")))
    img.paste(rim_layer, (0, 0), rim_layer)
    lw = max(2, min(w, h) // 300)
    cx = (anchor_x0 + anchor_x1) // 2
    # split line spans from the portal's own top-of-straight-run down to the
    # (margin-cropped) bottom — approximate the springline as before (35% of
    # anchor height / half anchor width, whichever is smaller) since the mask
    # doesn't carry an explicit springline marker
    bw = anchor_x1 - anchor_x0
    dome_h = min(bw * 0.5, (anchor_y1 - anchor_y0) * 0.35)
    straight_y0 = anchor_y0 + dome_h
    d.line([(cx, straight_y0), (cx, anchor_y1)], fill=DOOR_ANCHOR_OUTLINE, width=lw)


def _draw_holes(d: ImageDraw.ImageDraw, holes_frac, w: int, h: int):
    """Render each TRUE hole as a WHITE void with a thin solid frame ring — a
    paintable geometry-embrace zone, reusing _draw_void_frame's white-punch +
    ring convention."""
    for box_frac in holes_frac:
        box_px = _zone_px(box_frac, w, h)
        _draw_void_frame(d, box_px, w, h, FRAME_RING)


def _shape_kind(feature: dict) -> str:
    """Pick a simple solid-shape approximation for a feature zone by layer."""
    layer = feature.get("layer", "prop")
    if layer == "architecture":
        return "arch"     # rounded/arch-topped rect — beacons, badges, windows
    if layer == "prop":
        return "ellipse"  # bears, balloons — soft blob
    return "rect"         # detail (topiary etc.) — small block


def _zone_px(bbox_frac, w: int, h: int) -> tuple[int, int, int, int]:
    x0, y0, x1, y1 = bbox_frac
    return (int(round(x0 * w)), int(round(y0 * h)),
            int(round(x1 * w)), int(round(y1 * h)))


# a count>1 sub-shape must not exceed this fraction of the zone width, else two
# shapes at the extremes would touch/overlap for small N (e.g. N=2)
MAX_SUBSHAPE_WIDTH_FRAC = 0.25


def _feature_boxes(feature: dict, w: int, h: int) -> list[tuple[int, int, int, int]]:
    """Pixel boxes to draw for one feature. count==1 (default) -> the zone box
    unchanged. count==N>1 -> N disjoint sub-boxes spanning the zone's
    horizontal extremes (e.g. N=2 -> two small boxes flanking the zone, not one
    shape spanning the whole width) — round-2 fix for the topiary dark-slab
    defect. Each sub-box is centered on one of N evenly spaced x-positions
    from the zone's left extreme to its right extreme and capped at
    MAX_SUBSHAPE_WIDTH_FRAC of the zone width; vertical extent is unchanged."""
    x0, y0, x1, y1 = _zone_px(feature["zone_bbox_frac"], w, h)
    count = max(1, int(feature.get("count", 1) or 1))
    if count == 1:
        return [(x0, y0, x1, y1)]
    zone_w = x1 - x0
    sub_w = max(4, int(round(min(zone_w * MAX_SUBSHAPE_WIDTH_FRAC, zone_w / count))))
    # N evenly spaced centers from the left extreme to the right extreme
    boxes = []
    for i in range(count):
        cx = x0 + (sub_w // 2) if count == 1 else x0 + round(i * (zone_w - sub_w) / (count - 1)) + sub_w // 2
        bx0 = max(x0, cx - sub_w // 2)
        bx1 = min(x1, bx0 + sub_w)
        boxes.append((bx0, y0, bx1, y1))
    return boxes


# feature shapes must clear the door-anchor bbox (and forbidden stripes) by at
# least this fraction of panel width (round-2 fix: topiary count-split boxes
# were overlapping the door-anchor's bottom corners — "props on the flap area"
# violates the flaps-carry-only-door-content rule)
ANCHOR_CLEAR_FRAC = 0.01
STRIPE_CLEAR_FRAC = 0.02


def _boxes_overlap(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> bool:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    return ax0 < bx1 and bx0 < ax1 and ay0 < by1 and by0 < ay1


def _box_overlaps_portal_mask(box: tuple[int, int, int, int], portal_mask: "np.ndarray") -> bool:
    """Pixel-accurate overlap test against the TRUE portal mask (round-2 SPEC:
    "dodge rule now dodges the PORTAL mask not the bbox") — the mask is
    arch-shaped and narrower than its own bbox at the top corners, so a box
    can sit inside the anchor bbox's corner without touching a single portal
    pixel; this checks the actual mask pixels under the box, not just its
    rectangle vs. the anchor rectangle."""
    x0, y0, x1, y1 = box
    h, w = portal_mask.shape
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(w, x1), min(h, y1)
    if x1 <= x0 or y1 <= y0:
        return False
    return bool(portal_mask[y0:y1, x0:x1].any())


def _dodge_anchor_box(box: tuple[int, int, int, int], anchor_px: tuple[int, int, int, int],
                       forbidden_px: list[tuple[int, int]], w: int, h: int,
                       portal_mask: "np.ndarray | None" = None) -> tuple[int, int, int, int]:
    """Shift a feature box horizontally AWAY from the door-anchor bbox when it
    intersects it, clearing by >=ANCHOR_CLEAR_FRAC of panel width; clamp so it
    stays >=STRIPE_CLEAR_FRAC clear of forbidden stripes and inside the
    silhouette (x in [0, w]); if it still can't fit after clamping, shrink its
    width to fit the available gap. Left-of-anchor-center shapes shift left,
    right-of-anchor-center shapes shift right (general left/right rule, not
    special-cased to any one feature). The dodge TRIGGER is pixel-accurate
    against the TRUE portal mask when one is supplied (round-2 SPEC); the
    shift geometry still targets the anchor bbox, which is a safe superset of
    the (narrower, arch-shaped) portal mask, so the result never touches a
    portal pixel."""
    x0, y0, x1, y1 = box
    ax0, ay0, ax1, ay1 = anchor_px
    overlaps = (_box_overlaps_portal_mask(box, portal_mask) if portal_mask is not None
                else _boxes_overlap(box, anchor_px))
    if not overlaps:
        return box

    clear_px = int(round(ANCHOR_CLEAR_FRAC * w))
    box_cx = (x0 + x1) / 2
    anchor_cx = (ax0 + ax1) / 2
    box_w = x1 - x0

    if box_cx <= anchor_cx:
        # shift left: new right edge sits >=clear_px left of the anchor's left edge
        new_x1 = ax0 - clear_px
        new_x0 = new_x1 - box_w
    else:
        # shift right: new left edge sits >=clear_px right of the anchor's right edge
        new_x0 = ax1 + clear_px
        new_x1 = new_x0 + box_w

    # clamp inside the silhouette and clear of forbidden stripes
    lo_bound, hi_bound = 0, w
    stripe_clear_px = int(round(STRIPE_CLEAR_FRAC * w))
    for slo, shi in forbidden_px:
        if new_x1 > slo and new_x0 < shi:
            # box still straddles a stripe after the anchor-dodge shift — push
            # further in the same direction, clear of the stripe too
            if box_cx <= anchor_cx:
                new_x1 = slo - stripe_clear_px
                new_x0 = new_x1 - box_w
            else:
                new_x0 = shi + stripe_clear_px
                new_x1 = new_x0 + box_w

    if new_x0 < lo_bound:
        new_x0 = lo_bound
        new_x1 = new_x0 + box_w
    if new_x1 > hi_bound:
        new_x1 = hi_bound
        new_x0 = new_x1 - box_w

    # still doesn't fit (silhouette too narrow) -> shrink width to the gap
    if new_x0 < lo_bound or new_x1 > hi_bound or _boxes_overlap((new_x0, y0, new_x1, y1), anchor_px):
        if box_cx <= anchor_cx:
            new_x0 = max(lo_bound, new_x0)
            new_x1 = min(new_x1, ax0 - clear_px)
        else:
            new_x1 = min(hi_bound, new_x1)
            new_x0 = max(new_x0, ax1 + clear_px)
        if new_x1 <= new_x0:
            new_x1 = new_x0 + 1  # degenerate gap: keep a minimal valid box

    return (int(round(new_x0)), y0, int(round(new_x1)), y1)


def _dodge_feature_boxes(boxes: list[tuple[int, int, int, int]], anchor_px, forbidden_px, w: int, h: int,
                          portal_mask=None):
    return [_dodge_anchor_box(b, anchor_px, forbidden_px, w, h, portal_mask=portal_mask) for b in boxes]


def _draw_arch(d: ImageDraw.ImageDraw, box, fill, outline, width):
    x0, y0, x1, y1 = box
    bw, bh = x1 - x0, y1 - y0
    dome_h = min(bh, bw) * 0.5
    d.rectangle([x0, y0 + dome_h, x1, y1], fill=fill, outline=outline, width=width)
    d.pieslice([x0, y0, x1, y0 + 2 * dome_h], 180, 360, fill=fill, outline=outline, width=width)


def _draw_zone(d: ImageDraw.ImageDraw, feature: dict, w: int, h: int,
               anchor_px=None, forbidden_px=None, portal_mask=None):
    """Draw one shape per _feature_boxes() box (count==1 -> one shape over the
    whole zone; count==N>1 -> N disjoint shapes at the zone's extremes). When
    anchor_px is given, boxes intersecting the door-anchor bbox are shifted
    (or, failing that, shrunk) clear of it via _dodge_anchor_box — round-2
    fix: feature shapes (incl. count-split sub-boxes) must never land on the
    door-anchor's flap area (props there violate flaps-carry-only-door-content).
    portal_mask, when given, makes the dodge TRIGGER pixel-accurate against
    the TRUE door portal mask rather than its bbox (round-2 SPEC)."""
    kind = _shape_kind(feature)
    lw = max(2, min(w, h) // 300)
    boxes = _feature_boxes(feature, w, h)
    if anchor_px is not None:
        boxes = _dodge_feature_boxes(boxes, anchor_px, forbidden_px or [], w, h, portal_mask=portal_mask)
    for box in boxes:
        if kind == "arch":
            _draw_arch(d, box, ZONE_FILL, ZONE_OUTLINE, lw)
        elif kind == "ellipse":
            d.ellipse(box, fill=ZONE_FILL, outline=ZONE_OUTLINE, width=lw)
        else:
            d.rectangle(box, fill=ZONE_FILL, outline=ZONE_OUTLINE, width=lw)
    return boxes


def _draw_void_frame(d: ImageDraw.ImageDraw, box_px, w: int, h: int, ring_color):
    """Cutout void: punch the interior back to WHITE (the body silhouette is
    already painted grey over this band by _base_canvas — SPEC requires the
    void itself to read as white, not body-grey), then a thin SOLID frame ring
    around it — a paintable geometry-embrace zone, not a hard-edged hole."""
    ring_w = max(FRAME_MIN_PX, min(w, h) // 250)
    d.rectangle(box_px, fill=(255, 255, 255, 255))
    d.rectangle(box_px, outline=ring_color, width=ring_w)


def _base_canvas(w: int, h: int) -> Image.Image:
    """Grey rounded/domed body silhouette on a white background — same
    paint-here convention as skyline_panel.cmd_guide's grey body + bold contour."""
    img = Image.new("RGB", (w, h), (255, 255, 255))
    d = ImageDraw.Draw(img, "RGBA")
    dome_h = w * 0.42
    lw = max(3, w // 110)
    d.rectangle([0, dome_h, w - 1, h - 1], fill=BODY_GREY)
    d.pieslice([0, 0, w - 1, 2 * dome_h], 180, 360, fill=BODY_GREY)
    d.line([(0, dome_h), (0, h - 1)], fill=CONTOUR, width=lw)
    d.line([(w - 1, dome_h), (w - 1, h - 1)], fill=CONTOUR, width=lw)
    d.line([(0, h - 1), (w - 1, h - 1)], fill=CONTOUR, width=lw)
    d.arc([0, 0, w - 1, 2 * dome_h], 180, 360, fill=CONTOUR, width=lw)
    return img


def render_model(callouts: dict, w: int, h: int) -> Image.Image:
    """MODEL-FACING: grey body + solid zone shapes + the TRUE door-anchor
    (solid closed door outline + split line) + the TRUE hole voids. Forbidden
    stripes are OMITTED — the body stays continuous grey where they fall
    (round-2 fix: drawing them as white channels/holes leaked into generated
    art as literal painted white slots). Feature-zone shapes are dodged clear
    of the door-anchor bbox (see _draw_zone/_dodge_anchor_box) — flap area
    carries only door content, never props."""
    img = _base_canvas(w, h)
    d = ImageDraw.Draw(img, "RGBA")
    anchor_px = _door_anchor_box_px(_load_door_anchor(), w, h)
    portal_mask = np.array(_door_portal_mask_for_panel(w, h)) > 0
    forbidden_px = [(int(round(lo * w)), int(round(hi * w)))
                    for lo, hi in callouts.get("_forbidden_bands_frac", [])]
    _draw_door_anchor(img, d, _load_door_anchor(), w, h)
    for feature in callouts.get("features", []):
        _draw_zone(d, feature, w, h, anchor_px=anchor_px, forbidden_px=forbidden_px,
                   portal_mask=portal_mask)
    # holes drawn LAST: they are voids that must always stay clean, even if a
    # dodged feature box (pushed clear of the anchor/stripes) incidentally
    # lands over a hole's position
    _draw_holes(d, _load_door_holes(), w, h)
    return img


def render_geometry_only(w: int, h: int) -> Image.Image:
    """GEOMETRY-ONLY variant: base body + TRUE door-anchor + TRUE hole voids,
    with NO feature zones (round-2 SPEC: "base + anchor + holes, no feature
    zones"). Exposed as its own CLI flag rather than reaching into
    _base_canvas directly (round-1 workaround)."""
    img = _base_canvas(w, h)
    d = ImageDraw.Draw(img, "RGBA")
    _draw_door_anchor(img, d, _load_door_anchor(), w, h)
    _draw_holes(d, _load_door_holes(), w, h)
    return img


def render_human(callouts: dict, w: int, h: int) -> Image.Image:
    """HUMAN: body + zones + door-anchor + holes (same as render_model) PLUS
    the forbidden stripes — rendered here only, as a white geometry-embrace
    void with a thin frame ring, then tinted red — and feature_id text
    labels. Unchanged from the pre-round-2 visual; only render_model dropped
    the forbidden-stripe void geometry. Feature-zone shapes are dodged clear
    of the door-anchor bbox, same rule as render_model."""
    img = _base_canvas(w, h)
    d = ImageDraw.Draw(img, "RGBA")
    anchor_px = _door_anchor_box_px(_load_door_anchor(), w, h)
    portal_mask = np.array(_door_portal_mask_for_panel(w, h)) > 0
    forbidden_px = [(int(round(lo * w)), int(round(hi * w)))
                    for lo, hi in callouts.get("_forbidden_bands_frac", [])]
    _draw_door_anchor(img, d, _load_door_anchor(), w, h)
    for feature in callouts.get("features", []):
        _draw_zone(d, feature, w, h, anchor_px=anchor_px, forbidden_px=forbidden_px,
                   portal_mask=portal_mask)
    # holes drawn LAST — see render_model for rationale
    _draw_holes(d, _load_door_holes(), w, h)
    for lo, hi in callouts.get("_forbidden_bands_frac", []):
        box = (int(round(lo * w)), 0, int(round(hi * w)), h - 1)
        _draw_void_frame(d, box, w, h, FRAME_RING)
        d.rectangle(box, fill=FORBIDDEN_HUMAN)
    font = ImageFont.load_default()
    for feature in callouts.get("features", []):
        x0, y0, x1, y1 = _zone_px(feature["zone_bbox_frac"], w, h)
        label = feature.get("feature_id", "")
        cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
        tb = d.textbbox((0, 0), label, font=font)
        tw, th = tb[2] - tb[0], tb[3] - tb[1]
        d.text((cx - tw / 2, cy - th / 2), label, fill=LABEL_COLOR, font=font)
    return img


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--callouts", required=True, type=Path)
    ap.add_argument("--panel-size", required=True)
    ap.add_argument("--out-model", required=True, type=Path)
    ap.add_argument("--out-human", required=True, type=Path)
    ap.add_argument("--geometry-only", type=Path, default=None,
                     help="also write the geometry-only variant (base + door-anchor "
                          "+ holes, no feature zones) to this path")
    a = ap.parse_args()

    w, h = parse_panel_size(a.panel_size)
    callouts = load_callouts(a.callouts)

    a.out_model.parent.mkdir(parents=True, exist_ok=True)
    a.out_human.parent.mkdir(parents=True, exist_ok=True)
    render_model(callouts, w, h).save(a.out_model)
    render_human(callouts, w, h).save(a.out_human)
    print(f"model -> {a.out_model}  size={w}x{h}")
    print(f"human -> {a.out_human}  size={w}x{h}")

    if a.geometry_only is not None:
        a.geometry_only.parent.mkdir(parents=True, exist_ok=True)
        render_geometry_only(w, h).save(a.geometry_only)
        print(f"geometry-only -> {a.geometry_only}  size={w}x{h}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
