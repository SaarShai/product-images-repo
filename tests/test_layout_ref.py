"""layout_ref.py — model-facing layout ref (no text, no dashes, zones in-bounds)
+ human diagram (labels + forbidden stripes) from a feature-callouts YAML."""
import subprocess
import sys
from collections import deque
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import layout_ref as L  # noqa: E402

DOOR_CALLOUTS = REPO / "tasks/marriott-hospital/style-spec/feature-callouts-v1.yaml"
DEMO_DIR = REPO / "tasks/workflow-rebuild/refs/demo-layout"


def _components(mask: np.ndarray) -> list[np.ndarray]:
    """4-neighbour connected components (BFS) — matches the local idiom used by
    scripts/master_spec.py's components() for dash/dot-size scans."""
    h, w = mask.shape
    seen = np.zeros_like(mask, bool)
    comps = []
    ys, xs = np.where(mask)
    for y0, x0 in zip(ys.tolist(), xs.tolist()):
        if seen[y0, x0]:
            continue
        comp = np.zeros_like(mask, bool)
        dq = deque([(y0, x0)])
        seen[y0, x0] = True
        while dq:
            y, x = dq.popleft()
            comp[y, x] = True
            for ny, nx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    dq.append((ny, nx))
        comps.append(comp)
    return comps


@pytest.fixture(scope="module")
def callouts():
    return L.load_callouts(DOOR_CALLOUTS)


def test_forbidden_bands_parsed_from_comment(callouts):
    bands = callouts["_forbidden_bands_frac"]
    assert len(bands) == 2
    (a0, a1), (b0, b1) = bands
    assert a0 == pytest.approx(0.143, abs=0.001)
    assert a1 == pytest.approx(0.184, abs=0.001)
    assert b0 == pytest.approx(0.816, abs=0.001)
    assert b1 == pytest.approx(0.857, abs=0.001)


def test_zones_in_bounds(callouts):
    w, h = 832, 1184
    for feature in callouts["features"]:
        x0, y0, x1, y1 = L._zone_px(feature["zone_bbox_frac"], w, h)
        assert 0 <= x0 < x1 <= w, feature["feature_id"]
        assert 0 <= y0 < y1 <= h, feature["feature_id"]


def test_void_interior_is_white_not_body_grey(callouts):
    """SPEC (human diagram only): 'cutout voids white with a thin solid frame
    ring around each' — the void band's interior (inside the ring, away from
    the contour lines) must be white, not BODY_GREY, in the HUMAN output.
    Regression test for the ring-only-outline bug where _draw_void_frame drew
    the ring but never punched the interior back to white, so it read as
    plain grey body under a thin darker rule. Round-2: the MODEL-facing
    output no longer renders this void geometry at all (see
    test_model_output_has_no_forbidden_white_stripe below) — only render_human
    still draws the white+ring+red void."""
    w, h = 832, 1184
    img = L.render_human(callouts, w, h)
    arr = np.array(img.convert("RGB"))
    lo, hi = callouts["_forbidden_bands_frac"][0]
    x0, x1 = int(round(lo * w)), int(round(hi * w))
    ring_w = max(L.FRAME_MIN_PX, min(w, h) // 250)
    # sample inside the ring, well below the dome so we're clear of the
    # curved contour line at the top of the silhouette
    y = int(h * 0.6)
    interior = arr[y, x0 + ring_w + 2 : x1 - ring_w - 2]
    assert interior.size > 0
    # the red overlay tints the interior in render_human, so assert it is not
    # BODY_GREY-toned (the pre-fix bug) rather than pure white here.
    assert not np.allclose(interior, L.BODY_GREY[:3], atol=5), (
        f"void interior reads as plain body-grey, not a void: sample={interior[:1]}"
    )


def test_model_output_has_no_forbidden_white_stripe(callouts):
    """DEFECT 1 (critical, round 2): the MODEL-facing render must OMIT the
    forbidden stripes entirely — no full-height white column cutting through
    the grey body. Scan every x-column inside each forbidden band; none may
    be (near-)white for the full body height (dome-base to floor), which is
    what a literal keep-clear channel would look like and what generators
    mis-paint as a literal white slot."""
    w, h = 832, 1184
    img = L.render_model(callouts, w, h)
    arr = np.array(img.convert("RGB"))
    dome_h = w * 0.42
    y0, y1 = int(dome_h) + 5, h - 5  # clear of the dome arc and the floor rule
    for lo, hi in callouts["_forbidden_bands_frac"]:
        x0, x1 = int(round(lo * w)), int(round(hi * w))
        for x in range(x0, x1):
            column = arr[y0:y1, x]
            is_white = (column > 250).all(axis=1)
            assert not is_white.all(), (
                f"model-facing render has a full-height white column at x={x} "
                f"inside forbidden band ({lo}-{hi}) — stripes must be omitted"
            )


def test_panel_size_aspect_matches_output(callouts, tmp_path):
    w, h = 832, 1184
    img = L.render_model(callouts, w, h)
    assert img.size == (w, h)
    assert round(w / h, 4) == round(img.size[0] / img.size[1], 4)


def test_model_output_has_no_text(callouts):
    """No-text guaranteed BY CONSTRUCTION: render_model never touches a font —
    only render_human does. Assert the model path carries no ImageFont usage
    by checking output equality when features/forbidden are unchanged (a text
    draw would perturb pixels the human-only label region doesn't touch here,
    but the authoritative guarantee is structural: model draw calls never
    reference text)."""
    import inspect
    src = inspect.getsource(L.render_model)
    assert "text" not in src.lower()
    assert "font" not in src.lower()


def _min_component_dim(nonwhite: np.ndarray) -> int:
    """Smallest bbox-dimension across all connected components in a nonwhite
    mask (used both to assert a real render is clean and, as a negative
    control, that an injected isolated dot would actually be caught)."""
    dims = []
    for comp in _components(nonwhite):
        n = int(comp.sum())
        if n == 0:
            continue
        ys, xs = np.where(comp)
        comp_w, comp_h = xs.max() - xs.min() + 1, ys.max() - ys.min() + 1
        dims.append(max(comp_w, comp_h))
    return min(dims) if dims else 0


def test_model_output_no_small_components_anti_dash(callouts):
    """Model-facing PNG must contain no connected component smaller than 12px
    (anti-dash/dot check) — dashes leak into generated art as painted dots."""
    w, h = 832, 1184
    img = L.render_model(callouts, w, h)
    arr = np.array(img.convert("RGB"))
    nonwhite = ~(arr > 250).all(axis=2)
    assert _min_component_dim(nonwhite) >= 12


def test_anti_dash_check_actually_catches_an_isolated_dot():
    """Negative control for the anti-dash check above: on an all-white canvas
    with everything touching (so the whole-panel-is-one-component trap from
    the real render can't hide a regression), injecting one isolated 4px dot,
    physically disconnected from anything else, must drop the measured
    min-component-dim below 12 — proving the checker has teeth rather than
    passing vacuously because body/zones/rings are always one big blob."""
    w, h = 200, 200
    arr = np.full((h, w, 3), 255, dtype=np.uint8)
    # a large connected shape (>=12px in both dims) that alone would pass
    arr[50:150, 50:150] = 0
    nonwhite = ~(arr > 250).all(axis=2)
    assert _min_component_dim(nonwhite) >= 12

    # inject an isolated dash/dot, disconnected (>=1px gap) from the shape above
    arr[10:14, 10:14] = 0
    nonwhite = ~(arr > 250).all(axis=2)
    assert _min_component_dim(nonwhite) < 12


def test_human_output_has_labels_and_forbidden_stripes(callouts):
    w, h = 832, 1184
    model_img = L.render_model(callouts, w, h)
    human_img = L.render_human(callouts, w, h)
    assert np.array(model_img.convert("RGB")).tobytes() != np.array(human_img.convert("RGB")).tobytes()
    harr = np.array(human_img.convert("RGB"))
    lo, hi = callouts["_forbidden_bands_frac"][0]
    x0, x1 = int(lo * w), int(hi * w)
    strip = harr[h // 2, x0:x1]
    # forbidden stripe tinted red: red channel clearly dominant over blue/green
    assert strip[:, 0].mean() > strip[:, 2].mean() + 20


def test_count_two_feature_yields_two_disjoint_components(callouts):
    """DEFECT 2 (round 2): a feature with count=2 (topiary in the door
    callouts) must render as 2 DISJOINT shapes flanking its zone, not one
    slab spanning the whole zone width. Crop the model render to the
    feature's zone ROW (full panel width, since round-2 door-anchor dodging
    can shift topiary sub-boxes outside their original x-extent — see
    test_topiary_shapes_never_overlap_door_anchor below) and assert exactly 2
    connected components of the ZONE_FILL shape tone (the surrounding
    BODY_GREY is a different, lighter tone, so it does not bridge the two
    shapes into one component), each no wider than 25% of the (pre-dodge)
    zone width."""
    w, h = 832, 1184
    feature = next(f for f in callouts["features"] if f.get("count", 1) == 2)
    assert feature["feature_id"] == "topiary"
    img = L.render_model(callouts, w, h)
    arr = np.array(img.convert("RGB"))
    x0, y0, x1, y1 = L._zone_px(feature["zone_bbox_frac"], w, h)
    crop = arr[y0:y1, 0:w]
    shape_tone = np.array(L.ZONE_FILL[:3])
    is_shape = (np.abs(crop.astype(int) - shape_tone).max(axis=2) <= 4)
    comps = [c for c in _components(is_shape) if c.sum() > 0]
    assert len(comps) == 2, f"expected 2 disjoint topiary shapes, got {len(comps)}"
    zone_w = x1 - x0
    for comp in comps:
        ys, xs = np.where(comp)
        comp_w = xs.max() - xs.min() + 1
        assert comp_w <= zone_w * 0.25 + 1, f"topiary sub-shape too wide: {comp_w}px of zone {zone_w}px"


def test_topiary_shapes_never_overlap_door_anchor(callouts):
    """ROUND-2 FIX: feature-zone shapes (including count-split sub-boxes)
    must never intersect the door PORTAL — the topiary count=2 boxes
    previously overlapped the door-anchor's bottom corners ("props on the
    flap area" violates the flaps-carry-only-door-content rule). Assert no
    EXACT ZONE_FILL-toned pixel falls inside the TRUE portal mask (SPEC
    round-2 (5): "dodge rule now dodges the PORTAL mask not the bbox" — the
    portal is arch-shaped and narrower than its own bbox at the top corners,
    so a shape may legitimately sit in the anchor bbox's corner, outside the
    arch, without ever touching a door pixel), in both the model and human
    renders, for the real door callouts. Exact-match (not a loose tolerance)
    so incidental anti-aliased text-label pixels in render_human that happen
    to be near the tone (e.g. the 'topiary' label itself, drawn at the zone's
    un-shifted center) don't false-positive — a real shape fill is a flat,
    exact-tone block."""
    w, h = 832, 1184
    anchor_px = L._door_anchor_box_px(L._load_door_anchor(), w, h)
    ax0, ay0, ax1, ay1 = anchor_px
    portal_mask = np.array(L._door_portal_mask_for_panel(w, h)) > 0
    portal_mask[ay1:, :] = False  # same bottom-crop the renderer applies
    shape_tone = np.array(L.ZONE_FILL[:3])
    for img in (L.render_model(callouts, w, h), L.render_human(callouts, w, h)):
        arr = np.array(img.convert("RGB"))
        is_shape = (arr == shape_tone).all(axis=2)
        assert not (is_shape & portal_mask).any(), (
            "a feature-zone shape pixel falls inside the door portal mask"
        )


def test_feature_boxes_general_count(callouts):
    """_feature_boxes generalizes beyond N=2: count=1 -> 1 box unchanged;
    count=N>1 -> N disjoint boxes, each <=25% of zone width, spanning the
    zone's horizontal extremes."""
    w, h = 832, 1184
    feature = {"zone_bbox_frac": [0.1, 0.1, 0.9, 0.2], "layer": "detail", "count": 4}
    boxes = L._feature_boxes(feature, w, h)
    assert len(boxes) == 4
    zone_w = int(round(0.9 * w)) - int(round(0.1 * w))
    xs_sorted = sorted(boxes, key=lambda b: b[0])
    for i, box in enumerate(xs_sorted):
        bx0, by0, bx1, by1 = box
        assert bx1 - bx0 <= zone_w * 0.25 + 1
        if i > 0:
            assert bx0 >= xs_sorted[i - 1][2], "sub-boxes must be disjoint (non-overlapping)"
    # spans the zone's horizontal extremes: first box touches the left edge,
    # last box touches the right edge
    assert xs_sorted[0][0] == int(round(0.1 * w))
    assert xs_sorted[-1][2] == int(round(0.9 * w))

    single = L._feature_boxes({"zone_bbox_frac": [0.1, 0.1, 0.9, 0.2]}, w, h)
    assert len(single) == 1
    assert single[0] == L._zone_px([0.1, 0.1, 0.9, 0.2], w, h)


def test_shape_kind_by_layer():
    assert L._shape_kind({"layer": "architecture"}) == "arch"
    assert L._shape_kind({"layer": "prop"}) == "ellipse"
    assert L._shape_kind({"layer": "detail"}) == "rect"


def test_cli_writes_distinct_files_and_demo_dir(tmp_path):
    out_model = tmp_path / "model.png"
    out_human = tmp_path / "human.png"
    r = subprocess.run(
        [sys.executable, str(REPO / "scripts/layout_ref.py"),
         "--callouts", str(DOOR_CALLOUTS), "--panel-size", "832x1184",
         "--out-model", str(out_model), "--out-human", str(out_human)],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    assert out_model.exists() and out_human.exists()
    m = Image.open(out_model)
    assert m.size == (832, 1184)


def test_door_anchor_present_in_model_and_geometry_only(callouts):
    """SPEC (1): the door-anchor solid shape must appear in BOTH the model
    variant and the geometry-only variant, at the TRUE anchor position
    (door-spec.json's door_anchor_frac). Check the arch outline's darker tone
    (DOOR_ANCHOR_OUTLINE) is present within the anchor's pixel bbox."""
    w, h = 832, 1184
    anchor = L._load_door_anchor()
    x0, y0, x1, y1 = L._door_anchor_box_px(anchor, w, h)
    outline = np.array(L.DOOR_ANCHOR_OUTLINE[:3])
    for img in (L.render_model(callouts, w, h), L.render_geometry_only(w, h)):
        arr = np.array(img.convert("RGB"))
        crop = arr[y0:y1, x0:x1]
        is_outline = (np.abs(crop.astype(int) - outline).max(axis=2) <= 4)
        assert is_outline.any(), "door-anchor outline not found in anchor bbox"


def test_door_shape_bottom_above_anchor_bottom(callouts):
    """SPEC (1): the door shape's bottom must end ~1% of panel height ABOVE
    the anchor's own bottom edge (round-3, ledger S147: user wants "as little
    a gap as possible, or no gap" — cut from 4% to 1% — door art must reach
    close to the panel bottom while still avoiding a razor-thin seam)."""
    w, h = 832, 1184
    anchor = L._load_door_anchor()
    _, _, _, y1 = L._door_anchor_box_px(anchor, w, h)
    anchor_bottom_px = int(round(anchor[3] * h))
    expected = int(round(anchor[3] * h - L.DOOR_BOTTOM_MARGIN_FRAC * h))
    assert y1 == expected
    assert anchor_bottom_px - y1 == pytest.approx(L.DOOR_BOTTOM_MARGIN_FRAC * h, abs=1)


def test_holes_are_white_voids_with_darker_ring(callouts):
    """SPEC (2): each hole void is WHITE with a surrounding darker ring, in
    both the model and geometry-only variants."""
    w, h = 832, 1184
    holes = L._load_door_holes()
    assert len(holes) == 6
    for img in (L.render_model(callouts, w, h), L.render_geometry_only(w, h)):
        arr = np.array(img.convert("RGB"))
        for box_frac in holes:
            x0, y0, x1, y1 = L._zone_px(box_frac, w, h)
            cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
            center = arr[cy, cx]
            assert (center > 250).all(), f"hole interior not white: {center}"
            ring_w = max(L.FRAME_MIN_PX, min(w, h) // 250)
            # sample just outside the box edge for the darker ring tone
            ring_px = arr[cy, max(0, x0 - ring_w // 2 - 1)] if x0 - ring_w // 2 - 1 >= 0 else arr[cy, x0]
            assert not (ring_px > 250).all(), "expected a darker ring around the hole void"


def test_geometry_only_has_no_feature_zones(callouts):
    """SPEC (3): geometry-only variant = base + anchor + holes, NO feature
    zones — the ZONE_FILL tone must not appear anywhere in it, even though it
    does appear in render_model."""
    w, h = 832, 1184
    geo_arr = np.array(L.render_geometry_only(w, h).convert("RGB"))
    model_arr = np.array(L.render_model(callouts, w, h).convert("RGB"))
    zone_tone = np.array(L.ZONE_FILL[:3])
    geo_has_zone = (np.abs(geo_arr.astype(int) - zone_tone).max(axis=2) <= 4).any()
    model_has_zone = (np.abs(model_arr.astype(int) - zone_tone).max(axis=2) <= 4).any()
    assert not geo_has_zone
    assert model_has_zone


def test_geometry_only_cli_flag(tmp_path):
    """SPEC (3): geometry-only variant exposed as a proper CLI flag
    (--geometry-only), not by reaching into _base_canvas()."""
    out_model = tmp_path / "model.png"
    out_human = tmp_path / "human.png"
    out_geo = tmp_path / "geo.png"
    r = subprocess.run(
        [sys.executable, str(REPO / "scripts/layout_ref.py"),
         "--callouts", str(DOOR_CALLOUTS), "--panel-size", "832x1184",
         "--out-model", str(out_model), "--out-human", str(out_human),
         "--geometry-only", str(out_geo)],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    assert out_geo.exists()
    assert Image.open(out_geo).size == (832, 1184)


def test_demo_renders_written_for_door_callouts():
    """DONE MEANS (2): demo renders for the door callouts at 832x1184 written to
    tasks/workflow-rebuild/refs/demo-layout/."""
    out_model = DEMO_DIR / "door-layout-model.png"
    out_human = DEMO_DIR / "door-layout-human.png"
    r = subprocess.run(
        [sys.executable, str(REPO / "scripts/layout_ref.py"),
         "--callouts", str(DOOR_CALLOUTS), "--panel-size", "832x1184",
         "--out-model", str(out_model), "--out-human", str(out_human)],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    assert out_model.exists()
    assert out_human.exists()
    assert Image.open(out_model).size == (832, 1184)


def test_portal_mask_matches_door_spec_anchor():
    """SPEC (1): the portal mask TRACED from door-control.png (never a
    hand-synthesized bbox) must match door-spec.json's door_anchor_frac
    within 0.5% per edge — pixel-verifies the traced geometry against the
    machine contract instead of trusting the trace blindly."""
    mask = L._load_door_portal_mask()
    x0, y0, x1, y1 = L._door_portal_mask_bbox_frac(mask)
    ax0, ay0, ax1, ay1 = L._load_door_anchor()
    for got, want, edge in ((x0, ax0, "x0"), (y0, ay0, "y0"),
                             (x1, ax1, "x1"), (y1, ay1, "y1")):
        assert abs(got - want) <= 0.006, (
            f"portal mask {edge}={got:.4f} vs door-spec anchor {edge}={want:.4f} "
            f"(diff {abs(got - want) * 100:.2f}%)"
        )


def test_door_render_iou_vs_portal_mask():
    """SPEC (3): IoU between the rendered door region (DOOR_FILL- or
    DOOR_RIM-toned pixels) and the (bottom-cropped) TRUE portal mask must be
    >= 0.90 — the door in the guide must BE the true portal, not an inset
    approximation of it. round-3 (ledger S147, item 2): the door-RIM band now
    STRADDLES the portal edge by design (half outside, half inside), so a
    thin perimeter-wide strip is intentionally rendered OUTSIDE the raw
    portal mask (rendered is a strict superset there, never an inset) —
    this structurally caps IoU below the pre-rim 0.97 (measured ~0.906 at
    DOOR_RIM_BAND_FRAC=0.015); threshold lowered to 0.90 to accommodate the
    band's outside-half by design while still catching a real inset
    regression (an inset door would drop IoU much further, since it loses
    mask-side area rather than gaining a bounded outside strip)."""
    w, h = 832, 1184
    anchor = L._load_door_anchor()
    _, _, _, anchor_y1 = L._door_anchor_box_px(anchor, w, h)
    mask = np.array(L._door_portal_mask_for_panel(w, h)) > 0
    mask[anchor_y1:, :] = False  # same bottom-crop the renderer applies

    img = L.render_geometry_only(w, h)
    arr = np.array(img.convert("RGB"))
    fill_tone = np.array(L.DOOR_FILL[:3])
    rim_tone = np.array(L.DOOR_RIM[:3])
    is_fill = (np.abs(arr.astype(int) - fill_tone).max(axis=2) <= 4)
    is_rim = (np.abs(arr.astype(int) - rim_tone).max(axis=2) <= 4)
    rendered = is_fill | is_rim

    intersection = (rendered & mask).sum()
    union = (rendered | mask).sum()
    iou = intersection / union if union else 0.0
    assert iou >= 0.90, f"door-render IoU vs portal mask = {iou:.4f} (need >= 0.90)"


def test_rim_band_straddles_portal_edge_on_arch_and_both_sides(callouts):
    """NEW (round-3, ledger S147, item 2): the door-RIM band must exist on
    BOTH sides of the portal-mask edge — sampled on the arch (top) and on
    each of the left/right straight sides — so the rendered guide teaches
    "the frame sits ON the cut line" rather than butting up against it.
    For each sampled boundary point, walk outward along the local normal
    (horizontal for the sides, vertical for the arch) and assert a
    DOOR_RIM-toned pixel is found within the band's half-width on the
    OUTSIDE (still-false in the mask) and within the half-width on the
    INSIDE (still-true in the mask)."""
    w, h = 832, 1184
    anchor = L._load_door_anchor()
    _, _, _, anchor_y1 = L._door_anchor_box_px(anchor, w, h)
    mask = np.array(L._door_portal_mask_for_panel(w, h)) > 0
    mask[anchor_y1:, :] = False  # same bottom-crop the renderer applies

    img = L.render_geometry_only(w, h)
    arr = np.array(img.convert("RGB"))
    rim_tone = np.array(L.DOOR_RIM[:3])
    is_rim = (np.abs(arr.astype(int) - rim_tone).max(axis=2) <= 4)

    half = max(1, int(round(L.DOOR_RIM_BAND_FRAC * w / 2))) + 2  # small slack for rounding

    def rim_found(ys, xs) -> bool:
        for y, x in zip(ys, xs):
            if 0 <= y < h and 0 <= x < w and is_rim[y, x]:
                return True
        return False

    # -- left side: scan a mid-height row, find the mask's left edge, check
    #    rim pixels just outside (smaller x) and just inside (larger x)
    xs_side, = np.where(mask[int(h * 0.75), :])
    assert xs_side.size, "no portal pixels on the sampled side row"
    left_edge_x = xs_side.min()
    y_row = int(h * 0.75)
    assert rim_found([y_row] * half, range(left_edge_x - half, left_edge_x)), (
        "no rim pixel found OUTSIDE the portal edge on the left side"
    )
    assert rim_found([y_row] * half, range(left_edge_x, left_edge_x + half)), (
        "no rim pixel found INSIDE the portal edge on the left side"
    )

    # -- right side: mirror of the left-side check
    right_edge_x = xs_side.max()
    assert rim_found([y_row] * half, range(right_edge_x + 1, right_edge_x + 1 + half)), (
        "no rim pixel found OUTSIDE the portal edge on the right side"
    )
    assert rim_found([y_row] * half, range(right_edge_x - half + 1, right_edge_x + 1)), (
        "no rim pixel found INSIDE the portal edge on the right side"
    )

    # -- arch (top): scan a column through the LEFT leaf's dome (not the
    #    anchor's dead-center, which falls in the gap between the two door
    #    leaves / the center split), find the mask's top edge, check rim
    #    pixels just above (outside) and below (inside)
    x_col = int(round(anchor[0] * w + (anchor[2] * w - anchor[0] * w) * 0.3))
    ys_col, = np.where(mask[:, x_col])
    assert ys_col.size, "no portal pixels on the sampled arch column"
    top_edge_y = ys_col.min()
    assert rim_found(range(top_edge_y - half, top_edge_y), [x_col] * half), (
        "no rim pixel found OUTSIDE the portal edge on the arch"
    )
    assert rim_found(range(top_edge_y, top_edge_y + half), [x_col] * half), (
        "no rim pixel found INSIDE the portal edge on the arch"
    )


def test_portal_mask_saved_reference_matches_live_trace():
    """The cached reference PNG in tasks/workflow-rebuild/refs/demo-layout/
    (door-portal-mask.png, the pixel-verified trace artifact for this SPEC)
    must match a fresh trace of door-control.png byte-for-byte — regression
    guard against the trace silently drifting from the saved evidence."""
    live = L._load_door_portal_mask()
    cached = np.array(Image.open(L.CACHED_PORTAL_MASK_PNG).convert("L")) > 127
    assert live.shape == cached.shape
    assert np.array_equal(live, cached)
