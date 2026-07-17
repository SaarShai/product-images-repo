#!/usr/bin/env python3
"""Amendment 1+2 (pre-run corrections, 2 independent advisors): frozen
arch-shaped RGBA matte of the embedded door raster (assets/door_socket.png).

Border-connected near-white flood ONLY (white_key.py conventions:
thresh=246, sat=18, erode=0, feather~0.8px, NO interior reopening),
reimplemented standalone here (not shelled out) so the flood result is
directly auditable in-process before it is frozen. RGB bytes are NEVER
touched -- only the alpha channel is derived.

Audit (Amendment 2 #1): a conservative, non-flood, GLOBAL foreground test at
a looser threshold (~235, no border-connectivity, no sat gate) marks any
pixel that is unambiguously colored/non-white. Any such pixel the flood
matte removed (background) must sit within AUDIT_ERODE_PX of the matte's
background boundary (i.e. AA/feather fringe only, never a deep interior
chunk) and the total count must stay under a small budget. Asserted in code.

Feeds build_assets.py's arch-shaped socket_mask (replacing the earlier
full-rect socket exclusion). See PARAMS.md Amendment 1 / Amendment 2.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[4]
EXP = ROOT / "tasks/geometry-adherence-solutions/experiment-1"
ASSETS = EXP / "assets"
CHECKS = ASSETS / "checks"
SRC = ASSETS / "door_socket.png"
OUT = ASSETS / "door_socket_rgba.png"

THRESH = 246       # min RGB channel to count as background-white (white_key.py default preset)
SAT = 18           # max (max-min) channel spread to count as background-white
FEATHER = 0.8      # px, alpha-only Gaussian feather (white_key.py default)
AUDIT_THRESH = 235       # looser GLOBAL (non-flood) threshold for the over-removal audit
AUDIT_ERODE_PX = 2       # over-removed px must be within this many px of the bg boundary
AUDIT_MAX_DIFF_PX = 500  # total over-removal budget (px)


def border_connected_bg(whiteish: np.ndarray) -> np.ndarray:
    """4-connected components of `whiteish`; keep only components touching
    the image border (erode=0: no shrink of the resulting bg / growth of fg;
    no interior reopening: trapped interior near-white islands stay fg)."""
    struct = ndimage.generate_binary_structure(2, 1)
    lbl, _ = ndimage.label(whiteish, structure=struct)
    border_labels = (set(np.unique(lbl[0, :]).tolist()) | set(np.unique(lbl[-1, :]).tolist()) |
                      set(np.unique(lbl[:, 0]).tolist()) | set(np.unique(lbl[:, -1]).tolist()))
    border_labels.discard(0)
    if not border_labels:
        return np.zeros_like(whiteish, dtype=bool)
    return np.isin(lbl, list(border_labels))


def main() -> int:
    im = Image.open(SRC).convert("RGBA")
    rgb_u8 = np.asarray(im.convert("RGB"))
    rgb = rgb_u8.astype(np.int16)
    mn = rgb.min(axis=2)
    mx = rgb.max(axis=2)

    whiteish = (mn >= THRESH) & ((mx - mn) <= SAT)
    bg = border_connected_bg(whiteish)
    fg_hard = ~bg

    alpha_img = Image.fromarray((fg_hard * 255).astype(np.uint8), "L")
    if FEATHER > 0:
        alpha_img = alpha_img.filter(ImageFilter.GaussianBlur(FEATHER))
    alpha = np.asarray(alpha_img)

    out = Image.fromarray(np.dstack([rgb_u8, alpha]), "RGBA")
    CHECKS.mkdir(parents=True, exist_ok=True)
    out.save(OUT)

    n_removed = int(bg.sum())

    # ---- audit (Amendment 2 #1) ----------------------------------------
    conservative_fg = ~(mn >= AUDIT_THRESH)          # simple GLOBAL test, no connectivity/sat gate
    over_removed = conservative_fg & bg              # "definitely art" pixels the matte removed
    bg_interior = ndimage.binary_erosion(bg, iterations=AUDIT_ERODE_PX)
    deep_violations = over_removed & bg_interior
    n_over_removed = int(over_removed.sum())
    n_deep = int(deep_violations.sum())

    assert n_deep == 0, (
        f"matte over-removal audit FAILED: {n_deep} px of definitely-art content "
        f"(min-channel<{AUDIT_THRESH}) removed more than {AUDIT_ERODE_PX}px inside "
        f"the background region (not border-adjacent) -- see {OUT}")
    assert n_over_removed <= AUDIT_MAX_DIFF_PX, (
        f"matte over-removal audit FAILED: {n_over_removed} px exceeds budget "
        f"{AUDIT_MAX_DIFF_PX} -- see {OUT}")

    # ---- matte edge overlay check (native res) --------------------------
    edge = ndimage.binary_dilation(bg, iterations=1) & ~ndimage.binary_erosion(bg, iterations=1)
    ov = rgb_u8.copy()
    ov[edge] = [255, 0, 0]
    Image.fromarray(ov).save(CHECKS / "matte_edge_overlay.png")

    print(f"[build_socket_matte] native_size={im.size} thresh={THRESH} sat={SAT} erode=0 feather={FEATHER}")
    print(f"[build_socket_matte] removed_px={n_removed} ({100*n_removed/(im.width*im.height):.2f}% of raster)")
    print(f"[build_socket_matte] audit: over_removed_px={n_over_removed} (budget {AUDIT_MAX_DIFF_PX}) "
          f"deep_violations={n_deep} (must be 0) -- PASSED")
    print(f"[build_socket_matte] wrote {OUT}")
    print(f"[build_socket_matte] wrote {CHECKS / 'matte_edge_overlay.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
