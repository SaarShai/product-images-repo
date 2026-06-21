#!/usr/bin/env python3
"""leak_metric.py — PERCEPTUAL outside-mask leakage metric.

Companion to compose_fairy.py's --diffmask gate. That gate reports the max
RAW pixel delta OUTSIDE the edit mask (=0 ideal). But a whole-crop repaint
engine (Flux.2 / Kontext) can subtly REPAINT the background — same colors,
shifted texture/structure — which a byte-pixel gate near a feathered seam can
miss. This metric checks whether the region OUTSIDE the mask is PERCEPTUALLY
unchanged, using three complementary signals computed on outside-mask pixels:

  (a) SSIM        structural similarity (1.0 = identical)
  (b) LPIPS       learned perceptual distance (0.0 = identical)
  (c) DINOv2      patch-cosine similarity map of self-supervised features
                  (1.0 = identical); the most sensitive LOCAL-edit detector.
                  Falls back to LPIPS+SSIM only if the hub download is too slow
                  or torch.hub is unavailable (pass --no-dino to force).

LEAKAGE SCORE (0=clean .. 1=heavy leak), a max over the available signals:
  leak = max( 1-SSIM_out , clamp(LPIPS_out / LPIPS_REF) , 1-DINO_cos_out )
PASS = leak < --thresh  (outside-mask perceptually unchanged).

Mask semantics match compose_fairy.py: WHITE (>127) = the EDITED region (taxi /
fairy); the metric scores the COMPLEMENT (everything outside white). Mask is
resized to the image size if needed (nearest, to keep it binary).

Usage:
  python3 leak_metric.py --orig A.png --edited B.png --mask M.png \
      [--thresh 0.06] [--lpips-ref 0.15] [--no-dino] [--json out.json]
"""
import argparse
import json
import sys

import numpy as np
from PIL import Image


# ------------------------------------------------------------------ helpers
def load_rgb(path, size=None):
    im = Image.open(path).convert("RGB")
    if size is not None and im.size != size:
        im = im.resize(size, Image.LANCZOS)
    return im


def load_mask(path, size):
    m = Image.open(path).convert("L")
    if m.size != size:
        m = m.resize(size, Image.NEAREST)
    a = np.asarray(m, np.uint8)
    # Returns the OUTSIDE boolean (the region we SCORE): True where NOT edited.
    # White (>127) = EDITED region (taxi/fairy); we score its complement.
    return a <= 127


# ------------------------------------------------------------------ SSIM (outside-mask)
def ssim_outside(orig, edited, outside):
    """Windowed SSIM averaged over OUTSIDE pixels only.

    The edit region is neutralized to a constant grey in BOTH images first, so
    SSIM windows straddling the mask boundary see NO difference there and can't
    drag the outside score down (byte-identical outside -> SSIM 1.0). Then the
    map is averaged over outside pixels only."""
    from skimage.metrics import structural_similarity as ssim
    o = np.asarray(orig, np.float64).copy()
    e = np.asarray(edited, np.float64).copy()
    inside = ~outside
    o[inside] = 127.0
    e[inside] = 127.0  # identical inside -> zero structural diff at the seam
    _, smap = ssim(o, e, channel_axis=2, full=True, data_range=255.0,
                   gaussian_weights=True, sigma=1.5, use_sample_covariance=False)
    smap = smap.mean(axis=2)  # per-pixel, averaged over channels
    if outside.sum() == 0:
        return float("nan")
    return float(smap[outside].mean())


# ------------------------------------------------------------------ LPIPS (outside-mask)
def lpips_outside(orig, edited, outside, device):
    """LPIPS computed on the image with the EDIT region neutralized in BOTH
    images (set to a constant grey in both -> contributes ~0 perceptual diff),
    so the returned distance is driven by OUTSIDE-mask differences only."""
    import torch
    import lpips as lpips_mod

    net = lpips_mod.LPIPS(net="alex", verbose=False).to(device).eval()

    def prep(img):
        a = np.asarray(img, np.float32) / 255.0
        # neutralize inside-mask in both images identically
        inside = ~outside
        a[inside] = 0.5
        t = torch.from_numpy(a).permute(2, 0, 1).unsqueeze(0)  # 1,3,H,W
        t = t * 2.0 - 1.0  # LPIPS expects [-1,1]
        return t.to(device)

    with torch.no_grad():
        d = net(prep(orig), prep(edited))
    return float(d.flatten()[0].item())


# ------------------------------------------------------------------ DINOv2 patch-cosine (outside-mask)
def dino_outside(orig, edited, outside, device):
    """DINOv2 ViT-S/14 patch tokens; cosine similarity per patch between orig &
    edited, averaged over patches whose receptive area is mostly OUTSIDE the
    edit mask. Returns (mean_cos_outside, n_patches) or (None, reason)."""
    import torch

    try:
        model = torch.hub.load("facebookresearch/dinov2", "dinov2_vits14",
                               verbose=False, trust_repo=True)
    except Exception as ex:  # noqa: BLE001
        return None, f"dino-load-failed: {type(ex).__name__}: {ex}"

    model = model.to(device).eval()
    patch = 14
    # resize to a multiple of 14 (keep it small/fast: target ~518 on long side)
    W, H = orig.size
    long = 518
    scale = long / max(W, H)
    nw = max(patch, int(round(W * scale / patch)) * patch)
    nh = max(patch, int(round(H * scale / patch)) * patch)
    gw, gh = nw // patch, nh // patch

    def prep(img, dev):
        im = img.resize((nw, nh), Image.LANCZOS)
        a = np.asarray(im, np.float32) / 255.0
        mean = np.array([0.485, 0.456, 0.406], np.float32)
        std = np.array([0.229, 0.224, 0.225], np.float32)
        a = (a - mean) / std
        return torch.from_numpy(a).permute(2, 0, 1).unsqueeze(0).to(dev)

    def feats(dev):
        m = model.to(dev)
        with torch.no_grad():
            fo = m.forward_features(prep(orig, dev))["x_norm_patchtokens"][0]  # (gh*gw, C)
            fe = m.forward_features(prep(edited, dev))["x_norm_patchtokens"][0]
        return fo, fe

    try:
        fo, fe = feats(device)
    except Exception:  # noqa: BLE001 — MPS can miss an op; fall back to CPU
        fo, fe = feats("cpu")

    fo = torch.nn.functional.normalize(fo, dim=-1)
    fe = torch.nn.functional.normalize(fe, dim=-1)
    cos = (fo * fe).sum(-1).reshape(gh, gw).cpu().numpy()  # (gh, gw)

    # patch is OUTSIDE if the majority of its pixels are outside the edit mask
    om = Image.fromarray((outside.astype(np.uint8) * 255), "L").resize((gw, gh), Image.BILINEAR)
    out_patch = np.asarray(om, np.float32) / 255.0 > 0.5  # (gh, gw)
    if out_patch.sum() == 0:
        return None, "no-outside-patches"
    return float(cos[out_patch].mean()), int(out_patch.sum())


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--orig", required=True)
    ap.add_argument("--edited", required=True)
    ap.add_argument("--mask", required=True, help="white = EDITED region; metric scores OUTSIDE it")
    ap.add_argument("--thresh", type=float, default=0.06,
                    help="leak < thresh => PASS (default 0.06)")
    ap.add_argument("--lpips-ref", type=float, default=0.15,
                    help="LPIPS value mapped to leak=1.0 for normalization (default 0.15)")
    ap.add_argument("--no-dino", action="store_true", help="skip DINOv2 (LPIPS+SSIM only)")
    ap.add_argument("--json", default=None, help="optional path to write the verdict json")
    a = ap.parse_args()

    import torch
    device = "mps" if torch.backends.mps.is_available() else "cpu"

    orig = load_rgb(a.orig)
    edited = load_rgb(a.edited, size=orig.size)
    outside = load_mask(a.mask, orig.size)
    out_frac = float(outside.mean())

    res = {
        "orig": a.orig, "edited": a.edited, "mask": a.mask,
        "size": list(orig.size), "outside_fraction": round(out_frac, 4),
        "device": device,
    }

    # (a) SSIM
    ssim_v = ssim_outside(orig, edited, outside)
    res["ssim_outside"] = round(ssim_v, 6)

    # (b) LPIPS
    lp = lpips_outside(orig, edited, outside, device)
    res["lpips_outside"] = round(lp, 6)
    lpips_norm = min(1.0, lp / a.lpips_ref) if a.lpips_ref > 0 else lp

    # (c) DINOv2
    dino_cos = None
    if not a.no_dino:
        dino_cos, info = dino_outside(orig, edited, outside, device)
        if dino_cos is None:
            res["dino_outside"] = None
            res["dino_note"] = info
        else:
            res["dino_outside"] = round(dino_cos, 6)
            res["dino_patches"] = info
    else:
        res["dino_outside"] = None
        res["dino_note"] = "skipped (--no-dino)"

    # ---- leakage score = max of the available leak signals
    signals = {
        "ssim_leak": 1.0 - ssim_v,
        "lpips_leak": lpips_norm,
    }
    if dino_cos is not None:
        signals["dino_leak"] = 1.0 - dino_cos
    leak = max(signals.values())
    res["leak_signals"] = {k: round(v, 6) for k, v in signals.items()}
    res["leak_score"] = round(leak, 6)
    res["thresh"] = a.thresh
    res["verdict"] = "PASS" if leak < a.thresh else "FAIL"

    # ---- report
    print(f"[leak_metric] {a.orig}  vs  {a.edited}")
    print(f"  device={device}  size={tuple(orig.size)}  outside_fraction={out_frac:.3f}")
    print(f"  (a) SSIM_outside       = {ssim_v:.4f}   (1.0=identical)  -> ssim_leak  {1-ssim_v:.4f}")
    print(f"  (b) LPIPS_outside      = {lp:.4f}   (0.0=identical)  -> lpips_leak {lpips_norm:.4f}  (ref={a.lpips_ref})")
    if dino_cos is not None:
        print(f"  (c) DINOv2_cos_outside = {dino_cos:.4f}   (1.0=identical)  -> dino_leak  {1-dino_cos:.4f}  ({res.get('dino_patches')} patches)")
    else:
        print(f"  (c) DINOv2             = SKIPPED ({res.get('dino_note')})")
    print(f"  LEAK_SCORE = {leak:.4f}   (thresh {a.thresh})   => {res['verdict']}")

    if a.json:
        with open(a.json, "w") as f:
            json.dump(res, f, indent=2)
        print(f"  wrote {a.json}")

    sys.exit(0 if res["verdict"] == "PASS" else 1)


if __name__ == "__main__":
    main()
