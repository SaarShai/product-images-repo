import json

import numpy as np
from PIL import Image, ImageDraw

from studio.controlmap import _dilate, build_from_guide, cut_layer, panel_silhouette


def test_dilate_does_not_wrap():
    # regression: np.roll-based dilation teleported bottom-row strokes to row 0
    m = np.zeros((10, 10), bool)
    m[-1, :] = True
    d = _dilate(m, 2)
    assert not d[0].any() and not d[1].any()
    assert d[-3].all()


def test_cut_layer_keeps_hairline_strokes():
    # regression: alpha>200 filter lost sub-pixel anti-aliased contours
    rgba = np.zeros((4, 4, 4), np.uint8)
    rgba[1, 1] = (35, 31, 32, 60)       # hairline charcoal, low alpha
    rgba[2, 2] = (255, 219, 85, 255)    # yellow annotation dash
    cut = cut_layer(rgba)
    assert cut[1, 1] and not cut[2, 2]


def test_panel_silhouette_seals_open_bottom():
    # panel with side+top walls but open floor must still yield a solid body
    cut = np.zeros((40, 20), bool)
    cut[5, 3:17] = True    # top
    cut[5:40, 3] = True    # left wall to bottom edge
    cut[5:40, 16] = True   # right wall
    body = panel_silhouette(cut, dilate_iters=0, close_bottom=True)
    assert body[20, 10]          # interior sealed
    assert not body[2, 1]        # outside stays outside


def _synthetic_guide(tmp_path):
    """Gray arched body on white + black contour + pink keep-clear stripe."""
    w, h = 200, 400
    im = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(im)
    d.pieslice([10, 10, w - 10, 200], 180, 360, fill=(200, 200, 200), outline=(20, 20, 20), width=4)
    d.rectangle([10, 105, w - 10, h - 1], fill=(200, 200, 200))
    d.line([10, 105, 10, h - 1], fill=(20, 20, 20), width=4)
    d.line([w - 10, 105, w - 10, h - 1], fill=(20, 20, 20), width=4)
    d.rectangle([90, 150, 110, 380], fill=(245, 160, 160))  # pink annotation stripe
    p = tmp_path / "toy-guide.png"
    im.save(p)
    spec = {"panel": "toy", "aspect": round(w / h, 4), "aspect_tol": 0.02}
    sp = tmp_path / "toy.spec.json"
    sp.write_text(json.dumps(spec))
    return p, sp


def test_build_from_guide(tmp_path):
    guide, spec = _synthetic_guide(tmp_path)
    rep = build_from_guide(str(guide), str(spec), outdir=tmp_path)
    assert rep["aspect_ok"]
    assert rep["body_frac"] > 0.7          # solid silhouette, not hollow
    ctrl = np.array(Image.open(rep["control"]).convert("RGB"))
    # control map is white-on-black edges only: no pink survives
    r, g, b = (ctrl[..., i].astype(int) for i in range(3))
    assert not ((r > 200) & (g < 200)).any()
    assert (ctrl > 128).any()              # contour edges present
    mask = np.array(Image.open(rep["mask"]).convert("L"))
    # pink stripe area is interior => part of the body mask
    assert mask[300, 100] == 255
