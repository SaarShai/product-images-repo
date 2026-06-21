#!/usr/bin/env python3
"""Build a JUDGE PACKET for a whole-panel illustration: the registered overlay + per-cutout
high-DPI crops + the deterministic geometry floor. A VLM judge (subagent / subscription) then
reads the packet and applies the A-G rubric (skills + tasks/whole-panel-build/B0-judge).

This is the automated B0 judge's input layer. Registration is exact (make_anchor_overlay draws
the SVG guide lines in true viewBox coords on the candidate); circles/transforms/hidden-layers/
viewBox-clip are all handled by the fixed svg_classify/svg_geometry.

Usage:
  # from a combined template+illustration SVG (anchor):
  judge_panel.py --svg COMBINED.svg --out OUTDIR
  # from a separate candidate PNG + a template SVG (real generated candidate):
  judge_panel.py --svg TEMPLATE.svg --candidate CAND.png --out OUTDIR
"""
from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import svg_classify as C  # noqa: E402
import svg_geometry as G  # noqa: E402

# Split into OBJECTIVE (VLM-reliable on hi-DPI tiles, multi-judge) vs AESTHETIC (VLM-UNRELIABLE → human).
# Evidence (princess panel02): 3 reference-anchored judges scored a POOR-style and a GOOD-style gen the
# SAME (~72-82) on style/proportions — VLMs cluster on "looks like the genre" and miss artist-level
# refinement. So NEVER auto-PASS on style; route style/proportions to the human. Conversely the same
# judges reliably caught structural defects (arch-frame, white bg, sharp edges, window presence) on
# HI-DPI TILES — those are gateable. A whole tall image (downsampled by the reader) makes judges
# HALLUCINATE (a present mid-panel feature scored "absent") — always judge from tiles, not the full.
OBJECTIVE = """A fill-to-contour (no empty gap inside the contour, esp. bottom) ·
B cutout-fit (empty cutout=clean bg + bleed margin + rim/bevel; feature cutout=present+faithful on the cut) ·
C keep-clear (NO focal motif inside a red zone) · D top-contour (top silhouette follows the green guide) ·
E arch/feature-fit (door/window/landmark present, faithful, at its marked position) ·
F margins/seams (bleed margin; no focal element split by a blue fold / panel seam) ·
H edges-organic (art runs organically to the panel edges / full-bleed; NO drawn arch-frame line, NO white
background panel, NO hard straight cut edge). No guide lines baked into art ·
I element-count / NO-DUPLICATES — COUNT every embedded window / door / gate across the WHOLE image AND
every tile; there must be EXACTLY the number the geometry specifies (a single-window panel = ONE). A second
or extra window/door/gate anywhere (commonly stacked vertically, or an added ground gate at the bottom) =
FAIL. 'double-door / double-window' is a KNOWN recurring failure mode — the model adds its own gate/window
on top of the intended one. Always report the integer count you actually see."""
AESTHETIC = """G style-quality + proportions (watercolor refinement, believable tower/feature proportions,
overall taste). VLM-UNRELIABLE — report as advisory only; the HUMAN decides PASS/FAIL on aesthetics."""
RUBRIC = ("OBJECTIVE (gate on these, from HI-DPI TILES, >=3 judges, verify on disagreement):\n" + OBJECTIVE
          + "\n\nAESTHETIC (advisory only, route to human):\n" + AESTHETIC
          + "\n\nVERDICT(objective)=PASS only if A-F + H + I hold; else FAIL + failing checks + one fix. "
            "Report style/proportions as advisory; do NOT auto-PASS aesthetics.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--svg", required=True)
    ap.add_argument("--candidate", help="candidate PNG (omit to use the SVG's embedded raster)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--width", type=int, default=1100)
    ap.add_argument("--max-crops", type=int, default=10)
    ap.add_argument("--expect-windows", type=int, default=1,
                    help="expected embedded window count (metric I); default 1")
    ap.add_argument("--panel", choices=["door", "left", "right"],
                    help="skyline panel → attaches the geometry-spec contract (aspect/contour/arch/keep-clear/must_not)")
    ap.add_argument("--spec", help="path to a .spec.json geometry contract (overrides --panel derivation)")
    ap.add_argument("--refs", nargs="*", default=[],
                    help="reference / gold style images the judge anchors style-faithfulness to")
    args = ap.parse_args()
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    (out / "crops").mkdir(exist_ok=True)

    # 1) registered overlay (exact: SVG guide lines drawn on the candidate in true coords).
    # --contrast recolors by role so monochrome/all-black templates stay readable (dark-on-dark
    # guide lines over a dark painted edge read as a false "misalignment").
    overlay = out / "overlay.png"
    cmd = [sys.executable, str(ROOT / "scripts/make_anchor_overlay.py"), args.svg,
           "--out", str(overlay), "--width", str(args.width), "--contrast"]
    if args.candidate:
        cmd += ["--base", args.candidate]
    subprocess.run(cmd, check=True, capture_output=True)
    ov = Image.open(overlay); W, H = ov.size

    # 2) geometry roles (transform/hidden/clip/circle all handled) + per-cutout high-DPI crops
    vb, shapes = C.extract_shapes(Path(args.svg))
    cl = C.classify(shapes)
    vx, vy, vw, vh = vb
    sf = W / vw

    # 2a) GEOMETRY SPEC contract — the judge must score against THIS, not a generic prior
    # (a judge with no contract scores against "what an arched poster should look like", which is
    # exactly how the tapered/trapezoid doors looked acceptable).
    spec = None
    if args.spec and Path(args.spec).exists():
        spec = json.loads(Path(args.spec).read_text())
    elif args.panel:
        try:
            import skyline_panel as SP
            spec = SP.panel_spec(args.svg, args.panel, vb, cl)
        except Exception as e:  # noqa: BLE001
            spec = {"error": f"spec derivation failed: {e}"}

    cutouts = [s for s in cl if s.role == "internal_cutout"]
    redzones = [s for s in cl if s.role == "no_focal_motif_zone"]
    crops = []
    for i, s in enumerate(sorted(cutouts, key=lambda s: -s.area)[: args.max_crops]):
        x0, y0, x1, y1 = s.bounds
        pad = max(40, 0.6 * max(x1 - x0, y1 - y0))
        box = (max(0, int((x0 - vx - pad) * sf)), max(0, int((y0 - vy - pad) * sf)),
               min(W, int((x1 - vx + pad) * sf)), min(H, int((y1 - vy + pad) * sf)))
        if box[2] - box[0] < 8 or box[3] - box[1] < 8:
            continue
        p = out / "crops" / f"cutout_{i}.png"
        ov.crop(box).save(p)
        crops.append(str(p))

    # 2a') KEEP-CLEAR LANE crops — so the judge can verify NO recognizable feature
    # (face/head/sign/roof-tip) sits in or is cropped at a keep-clear lane. This is the
    # exact miss on RC-right-geoK2 (a horse HEAD was cropped in the narrow center lane);
    # a pixel gate can't tell a tower facade from a head, so the judge must SEE the lane.
    keep_clear_crops = []
    src = Image.open(args.candidate) if args.candidate else ov
    src = src.convert("RGB"); SW, SH = src.size
    # These crops use FULL-TEMPLATE SVG coords, so they only align when the candidate IS
    # the full template raster. A single-panel raw (aspect far from the template's) would
    # produce misaligned slivers — for those use skyline_panel.py --mode check (panel-
    # relative lane crop) instead. Skip rather than emit a misleading crop.
    template_aspect = vw / vh
    lane_aligned = abs((SW / SH) - template_aspect) / template_aspect < 0.15
    for i, s in enumerate(redzones if lane_aligned else []):
        x0, y0, x1, y1 = s.bounds
        padx = 0.5 * (x1 - x0)
        box = (max(0, int((x0 - vx - padx) / vw * SW)), max(0, int((y0 - vy) / vh * SH)),
               min(SW, int((x1 - vx + padx) / vw * SW)), min(SH, int((y1 - vy) / vh * SH)))
        if box[2] - box[0] < 8 or box[3] - box[1] < 8:
            continue
        p = out / "crops" / f"keepclear_{i}.png"
        src.crop(box).save(p)
        keep_clear_crops.append(str(p))

    # 2b) HI-DPI TILES of the candidate — judges MUST read these (the whole tall image is downsampled
    # by the reader → hallucinations). Tiling is the fix for the "feature absent" false negatives.
    tiles = []
    context = None  # whole-panel downscaled image (judge_tiles.py emits "context.png")
    tdir = out / "tiles"
    src_for_tiles = args.candidate or overlay
    try:
        subprocess.run([sys.executable, str(ROOT / "scripts/judge_tiles.py"),
                        "--candidate", str(src_for_tiles), "--out", str(tdir)],
                       check=True, capture_output=True)
        man = json.loads((tdir / "manifest.json").read_text())
        tiles = [str(tdir / t["file"]) for t in man.get("tiles", [])]
        ctx_name = man.get("context", "context.png")
        ctx_path = tdir / ctx_name
        if ctx_path.exists():
            context = str(ctx_path)
    except Exception:
        tiles = []
        context = None

    # 3) deterministic geometry floor (best-effort; gross failures)
    geom = {}
    try:
        gj = out / "region_iou.json"
        subprocess.run([sys.executable, str(ROOT / "scripts/geom_iou.py"), str(args.candidate or overlay),
                        "--svg", args.svg, "--json-out", str(gj)], capture_output=True, timeout=120)
        if gj.exists():
            geom = json.loads(gj.read_text())
    except Exception as e:
        geom = {"error": str(e)}

    packet = {
        "protocol_version": 2,
        "overlay": str(overlay),
        "context": context,  # whole-panel downscaled image for the MANDATORY count step (metric I)
        "tiles": tiles,
        "crops": crops,
        "keep_clear_crops": keep_clear_crops,  # judge: no recognizable feature in/cropped at a keep-clear lane
        "geometry_spec": spec,  # the contract to score geometry against (None if --panel/--spec omitted)
        "references": [str(r) for r in args.refs],  # gold/style images for faithfulness (advisory)
        "counts": {"cutouts": len(cutouts), "red_keep_clear": len(redzones)},
        "expected_element_counts": {"windows": args.expect_windows},
        "geometry_floor": {k: geom.get(k) for k in ("mean_iou", "openings", "pass") if k in geom},
        "rubric": RUBRIC,
        "protocol": "Run >=3 INDEPENDENT judges; report per-metric median + spread; on disagreement a human "
                    "verifies. OBJECTIVE metrics gate; AESTHETIC (style/proportions) is advisory → human decides.",
        "instruction": "Read the TILES (hi-DPI) for any presence/position/detail/edge check — NOT the "
                       "downsampled overlay alone (causes false 'absent' calls). overlay+crops for "
                       "geometry/holes, tiles for edges & features. Apply OBJECTIVE rubric; AESTHETIC advisory. "
                       "MANDATORY count step (metric I): COUNT the embedded windows/doors/gates on the WHOLE-"
                       "PANEL context.png (the downscaled full image — large elements survive downscale and all "
                       "instances are visible AT ONCE). Do NOT count from tiles alone: tiling SPLITS a duplicate "
                       "across a seam so each tile shows one and you wrongly read the 2nd as the 'same instance "
                       "continuing' (this exact miss happened — two stacked windows passed). Use the context for "
                       "the count, tiles only to confirm each instance is real. A single-window panel must show "
                       "EXACTLY ONE — report window_count and FAIL if it is not the expected number. "
                       "GEOMETRY: if geometry_spec is present, score geometry ONLY against it — verify the "
                       "artwork fills the contour edge-to-edge (no taper/pinch/trapezoid, no background in the "
                       "bottom corners or mid-height sides), the gateway aligns to saloon_arch_frac, nothing "
                       "iconic sits in a keep_clear lane, and no landmark base is cropped; report EACH must_not "
                       "as pass/fail. STYLE: if references are present, judge style-faithfulness against them "
                       "(advisory only). "
                       "Return {objective_verdict, window_count, must_not_results{}, failing_checks[], reasons[], aesthetic_advisory, one_fix}.",
    }
    (out / "judge-packet.json").write_text(json.dumps(packet, indent=2))
    print(f"packet: {out/'judge-packet.json'}  overlay={overlay.name}  tiles={len(tiles)} crops={len(crops)}  cutouts={len(cutouts)} red={len(redzones)}")
    print(f"  geometry_floor: {packet['geometry_floor']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
