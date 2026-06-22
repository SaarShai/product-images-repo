#!/usr/bin/env python3
"""edit.py — one-command element edit dispatcher. Ties the verified pieces together:

  automask (text->mask) -> mask_check guardrail -> route engine by op -> diff-mask composite
  + pixel gate -> judge (leftover-text/artifacts).

Ops:
  remove  : erase the element (fal Bria eraser) and reconstruct bg.
  redraw  : repaint the element in place (fal Flux Fill) from a prompt/template.

Auto-crops a context window around the auto-found element bbox so the engine gets a small,
in-context crop; composites back into the full image so the rest stays byte-identical.

Usage:
  python3 scripts/edit.py --src IMG --op remove  --element "the small yellow taxi" [--box x0,y0,x1,y1]
  python3 scripts/edit.py --src IMG --op remove  --element "..." --free   # FREE local LaMa eraser (no fal cost)
  python3 scripts/edit.py --src IMG --op redraw  --element "the yellow taxi" --desc "a clean classic NYC sedan"
Outputs <stem>.edited.png next to --src (or --out), plus _editov overlay + judge JSON
+ a <out>.json provenance sidecar (every input/decision needed to reproduce/audit the edit).

Upgrades layered on the proven pipeline (all degrade gracefully if a sub-venv is missing):
  - PROVENANCE : <out>.json sidecar with src/op/element/box/engine/seed/mask_bbox/crop/
                 gate results/judge verdict/tool-versions (git rev).
  - --free     : op=remove uses the FREE local eraser (.venv-iopaint LaMa) instead of fal Bria.
  - AUTO-GATES : after compose, run leak_metric (perceptual outside-mask leak) and, for
                 op=remove, text_gate (deterministic leftover-text OCR) in their own venvs;
                 their exit codes fold into the final SUCCESS/NEEDS-REVIEW decision.
"""
import argparse, json, subprocess, sys, tempfile
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter

R = Path(__file__).resolve().parent  # scripts/
ROOT = R.parent                      # repo root (holds the .venv-* dirs)
PY = sys.executable

# Dedicated sub-venv pythons for the cross-venv auto-gates / free eraser.
VENV_IOPAINT = ROOT / ".venv-iopaint" / "bin" / "python"
VENV_METRIC = ROOT / ".venv-metric" / "bin" / "python"
VENV_OCR = ROOT / ".venv-ocr" / "bin" / "python"


def git_rev():
    """Short git rev of the repo (for provenance); None if unavailable."""
    try:
        p = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
                           capture_output=True, text=True)
        return p.stdout.strip() or None if p.returncode == 0 else None
    except Exception:
        return None


def run(cmd):
    print("  $", " ".join(str(c) for c in cmd))
    p = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
    if p.stdout.strip():
        print("   ", p.stdout.strip().replace("\n", "\n    "))
    return p


def mask_bbox(mask_path, pad=0, shape=None):
    m = np.asarray(Image.open(mask_path).convert("L")) > 128
    ys, xs = np.where(m)
    if not len(xs):
        raise SystemExit("empty mask")
    x0, y0, x1, y1 = xs.min(), ys.min(), xs.max(), ys.max()
    if pad:
        x0, y0, x1, y1 = x0 - pad, y0 - pad, x1 + pad, y1 + pad
    if shape:
        H, W = shape
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(W, x1), min(H, y1)
    return int(x0), int(y0), int(x1), int(y1)


def judge_region(out_path, jcrop_box, element, work):
    """Crop the result to jcrop_box and run the VLM judge; return its parsed verdict."""
    jcrop = work / "jcrop.png"
    Image.open(out_path).convert("RGB").crop(jcrop_box).save(jcrop)
    jr = subprocess.run([str(PY), str(R/"judge.py"), "--image", str(jcrop),
                         "--element", element], capture_output=True, text=True)
    try:
        verdict = json.loads(jr.stdout)
    except Exception:
        verdict = {"raw": jr.stdout[:300]}
    return verdict, jcrop


def run_text_gate(jcrop, applicable):
    """Run the deterministic OCR text gate (own venv) on the judge crop.

    Returns a dict with: available / applicable / exit_code / no_text plus the
    gate's own JSON (has_text/found/kept[box]/region_origin/upscale). A missing
    venv or parse failure degrades gracefully (available=False) and never raises.
    Always passes --json so box geometry is emitted for auto-repair targeting.
    """
    tg = {"available": False, "applicable": applicable}
    if not VENV_OCR.exists():
        print(f"  [warn] text_gate SKIPPED: {VENV_OCR} missing")
        return tg
    tp = run([VENV_OCR, R/"text_gate.py", "--image", jcrop, "--json"])
    tg = {"available": True, "applicable": applicable, "exit_code": tp.returncode}
    try:
        tg.update(json.loads(tp.stdout))
    except Exception:
        pass
    # exit 0 = no text (clean); exit 2 = text found
    tg["no_text"] = (tp.returncode == 0)
    return tg


def textgate_boxes_to_full(tg, jcrop_box=(0, 0, 0, 0)):
    """Map text_gate `kept` boxes to FULL-image [x0,y0,x1,y1] coords.

    text_gate ran on the JCROP image, so boxes are jcrop-local; full =
    jcrop_origin + region_origin + box/upscale. (The missing jcrop offset was the
    auto-repair bug that erased the wrong region.) Returns [] if no usable boxes."""
    if not tg.get("available"):
        return []
    jx0, jy0 = jcrop_box[0], jcrop_box[1]
    ox, oy = tg.get("region_origin", [0, 0])
    up = float(tg.get("upscale") or 1.0) or 1.0
    boxes = []
    for det in tg.get("kept", []):
        b = det.get("box")
        if not b or len(b) != 4:
            continue
        x0, y0, x1, y1 = b
        boxes.append([jx0 + int(round(ox + x0 / up)), jy0 + int(round(oy + y0 / up)),
                      jx0 + int(round(ox + x1 / up)), jy0 + int(round(oy + y1 / up))])
    return boxes


def _has_unwanted_text(verdict, textgate):
    """True if EITHER signal sees text: the VLM judge's leftover_text flag, or the
    deterministic OCR gate finding any kept detection. Belt-and-suspenders so a
    single flaky signal can't let stamped text slip through."""
    judge_text = (verdict.get("leftover_text") is True)
    gate_text = bool(textgate.get("available") and not textgate.get("no_text"))
    return judge_text or gate_text


def autorepair_text(a, src, out, work, W, H, elem_bbox, jcrop_box,
                    verdict, textgate, max_passes):
    """SELF-HEALING: erase unwanted text the redraw stamped on, then re-gate.

    Operates IN PLACE on `out` (each pass erases from the current `out` and writes
    back). Returns (repair_passes, repair_log, verdict, textgate) with the LATEST
    gate results so the caller's decision step sees the post-repair state.

    Targeting, in order of preference:
      1. PaddleOCR boxes (text_gate --json) mapped to full coords -> tight mask.
      2. Fallback: automask "text and lettering on the car" over the element bbox.
    Erase = fal Bria eraser on a context crop -> compose_fairy --diffmask (keeps
    everything outside the text byte-exact). Bounded to `max_passes`; degrades to a
    no-op (leaving NEEDS-REVIEW) if it cannot locate text or the eraser is missing.
    """
    ex0, ey0, ex1, ey1 = elem_bbox
    repair_log = []
    passes = 0

    if not _has_unwanted_text(verdict, textgate):
        return passes, repair_log, verdict, textgate

    print(f"\n[edit] AUTO-REPAIR: unwanted text detected on redraw "
          f"(judge.leftover_text={verdict.get('leftover_text')}, "
          f"gate.found={textgate.get('found')}); erasing up to {max_passes} pass(es)")

    for p in range(1, max_passes + 1):
        # --- locate the text: prefer OCR boxes, else automask over the element ---
        boxes = textgate_boxes_to_full(textgate, jcrop_box)
        tmask = work / f"repair_mask_{p}.png"
        method = None
        if boxes:
            method = "ocr_boxes"
            mimg = Image.new("L", (W, H), 0)
            from PIL import ImageDraw as _ID
            dr = _ID.Draw(mimg)
            pad = 10  # small pad so the glyph's anti-aliased halo is covered
            for (bx0, by0, bx1, by1) in boxes:
                dr.rectangle([max(0, bx0 - pad), max(0, by0 - pad),
                              min(W, bx1 + pad), min(H, by1 + pad)], fill=255)
            mimg.filter(ImageFilter.MaxFilter(9)).save(tmask)  # dilate union
            tx0 = max(0, min(b[0] for b in boxes) - 12)
            ty0 = max(0, min(b[1] for b in boxes) - 12)
            tx1 = min(W, max(b[2] for b in boxes) + 12)
            ty1 = min(H, max(b[3] for b in boxes) + 12)
        else:
            # fallback: SAM mask of "text and lettering" within the element bbox
            method = "automask_fallback"
            ebpad = 40
            ax0, ay0 = max(0, ex0 - ebpad), max(0, ey0 - ebpad)
            ax1, ay1 = min(W, ex1 + ebpad), min(H, ey1 + ebpad)
            elem_crop = work / f"repair_elem_{p}.png"
            Image.open(out).convert("RGB").crop((ax0, ay0, ax1, ay1)).save(elem_crop)
            elem_mask = work / f"repair_elem_mask_{p}.png"
            am = run([PY, R/"automask.py", "--image", elem_crop,
                      "--prompt", "text and lettering on the car",
                      "--out", elem_mask, "--dilate", 10, "--max-masks", 6])
            if am.returncode != 0:
                repair_log.append({"pass": p, "method": method,
                                   "status": "no_text_mask_found"})
                print(f"  [repair {p}] could not locate text (automask failed); "
                      f"leaving result for review")
                break
            # paste the element-crop mask into a full-size mask
            mimg = Image.new("L", (W, H), 0)
            mimg.paste(Image.open(elem_mask).convert("L"), (ax0, ay0))
            mimg.save(tmask)
            mb = np.asarray(mimg) > 128
            ys, xs = np.where(mb)
            if not len(xs):
                repair_log.append({"pass": p, "method": method,
                                   "status": "empty_text_mask"})
                print(f"  [repair {p}] text mask empty; leaving result for review")
                break
            tx0, ty0, tx1, ty1 = int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())

        # --- erase the text on a context crop, compose back IN PLACE ---
        cpad = 80
        rcx0, rcy0 = max(0, tx0 - cpad), max(0, ty0 - cpad)
        rcx1, rcy1 = min(W, tx1 + cpad), min(H, ty1 + cpad)
        rctx = work / f"repair_ctx_{p}.png"
        Image.open(out).convert("RGB").crop((rcx0, rcy0, rcx1, rcy1)).save(rctx)
        rctx_mask = work / f"repair_ctx_mask_{p}.png"
        Image.open(tmask).convert("L").crop((rcx0, rcy0, rcx1, rcy1)).save(rctx_mask)
        rregen = work / f"repair_regen_{p}.png"
        # FREE local LaMa eraser when available + requested; else fal Bria.
        if a.free and VENV_IOPAINT.exists():
            er = run([VENV_IOPAINT, R/"lama_erase.py", "--image", rctx,
                      "--mask", rctx_mask, "--out", rregen])
        else:
            er = run([PY, R/"falgen.py", "--mode", "eraser", "--image", rctx,
                      "--mask", rctx_mask, "--out", rregen, "--maxside", "1400", "--cache"])
        if er.returncode != 0:
            repair_log.append({"pass": p, "method": method, "status": "eraser_failed"})
            print(f"  [repair {p}] eraser failed; leaving result for review")
            break
        rcomp = run([PY, R/"compose_fairy.py", "--orig", out, "--regen", rregen,
                     "--out", out, "--crop", f"{rcx0},{rcy0},{rcx1},{rcy1}",
                     "--mask", f"{tx0},{ty0},{tx1},{ty1}",
                     "--diffmask", "--diff-thresh", "20", "--diff-close", "5",
                     "--diff-dilate", "4", "--diff-feather", "3"])
        comp_ok = rcomp.returncode == 0 and "outside_max_delta=0" in rcomp.stdout  # returncode guards a crashed compose

        # --- re-gate the repaired result ---
        verdict, jcrop = judge_region(out, jcrop_box, a.element, work)
        textgate = run_text_gate(jcrop, applicable=True)
        still = _has_unwanted_text(verdict, textgate)
        passes = p
        repair_log.append({
            "pass": p, "method": method,
            "text_bbox": [tx0, ty0, tx1, ty1],
            "ctx_crop": [rcx0, rcy0, rcx1, rcy1],
            "compose_outside_clean": bool(comp_ok),
            "judge_leftover_text": verdict.get("leftover_text"),
            "gate_found": textgate.get("found"),
            "gate_no_text": textgate.get("no_text"),
            "cleared": (not still),
        })
        print(f"  [repair {p}] method={method} -> judge.leftover_text="
              f"{verdict.get('leftover_text')} gate.found={textgate.get('found')} "
              f"cleared={not still}")
        if not still:
            break

    return passes, repair_log, verdict, textgate


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--op", required=True, choices=["remove", "redraw"])
    ap.add_argument("--element", required=True)
    ap.add_argument("--desc", default="a clean version")
    ap.add_argument("--box", help="x0,y0,x1,y1 px to disambiguate which instance")
    ap.add_argument("--out")
    ap.add_argument("--ctx-pad", type=int, default=240, help="context margin around element for the engine")
    ap.add_argument("--mask-dilate", type=int, default=8)
    ap.add_argument("--seed", type=int, default=12345)
    ap.add_argument("--free", action="store_true",
                    help="op=remove: use the FREE local LaMa eraser (.venv-iopaint) instead of fal Bria (cost saver)")
    a = ap.parse_args()

    src = Path(a.src)
    out = Path(a.out) if a.out else src.with_suffix(".edited.png")
    img = Image.open(src).convert("RGB"); W, H = img.size
    work = Path(tempfile.mkdtemp(prefix="edit_"))
    print(f"[edit] {a.op} '{a.element}' on {src.name} ({W}x{H}) work={work}")

    # 1) crop to --box first (isolates the right instance), then auto-mask WITHIN the ctx
    if a.box:
        bx0, by0, bx1, by1 = (int(v) for v in a.box.split(","))
        cx0, cy0 = max(0, bx0 - a.ctx_pad), max(0, by0 - a.ctx_pad)
        cx1, cy1 = min(W, bx1 + a.ctx_pad), min(H, by1 + a.ctx_pad)
    else:
        cx0, cy0, cx1, cy1 = 0, 0, W, H
    ctx = work / "ctx.png"; img.crop((cx0, cy0, cx1, cy1)).save(ctx)
    ctx_mask = work / "ctx_mask.png"
    if run([PY, R/"automask.py", "--image", ctx, "--prompt", a.element, "--out", ctx_mask,
            "--dilate", a.mask_dilate, "--max-masks", 6]).returncode != 0:
        raise SystemExit("[edit] automask failed")

    # 2) if no --box, re-crop tight around the found element (+ re-slice the mask)
    lx0, ly0, lx1, ly1 = mask_bbox(ctx_mask)
    if not a.box:
        nx0, ny0 = max(0, lx0 - a.ctx_pad), max(0, ly0 - a.ctx_pad)
        nx1, ny1 = min(W, lx1 + a.ctx_pad), min(H, ly1 + a.ctx_pad)
        img.crop((nx0, ny0, nx1, ny1)).save(ctx)
        Image.open(ctx_mask).convert("L").crop((nx0, ny0, nx1, ny1)).save(ctx_mask)
        cx0, cy0, cx1, cy1 = nx0, ny0, nx1, ny1
        lx0, ly0, lx1, ly1 = mask_bbox(ctx_mask)
    ex0, ey0, ex1, ey1 = cx0 + lx0, cy0 + ly0, cx0 + lx1, cy0 + ly1  # full-coord element bbox

    # 3) guardrail: mask non-empty + covers element ink edges; overlay for inspection.
    # SURFACE the exit code (was discarded => the gate was decorative). WARN-loud rather than hard-exit:
    # target=edges on soft watercolor can yield sparse edges -> a good mask could dip below contain 0.4,
    # so a hard refusal would false-fail legit edits; a visible warning still kills the silent-discard.
    # ratio guard disabled here (--max-ratio 999): target=edges makes mask/edge-px ratio naturally high.
    if run([PY, R/"mask_check.py", "--image", ctx, "--mask", ctx_mask, "--target", "edges",
            "--region", f"{lx0},{ly0},{lx1},{ly1}", "--min-contain", "0.4", "--max-leak", "0.9",
            "--max-ratio", "999", "--out", str(work/"_mc_ov.png")]).returncode == 2:
        print("  [edit][WARN] mask_check FAIL — mask may miss the element or leak heavily; "
              "inspect _mc_ov.png before trusting this edit", flush=True)

    # 4) route engine
    regen = work / "regen.png"
    engine_id = None  # recorded in provenance
    if a.op == "remove":
        if a.free and VENV_IOPAINT.exists():
            # FREE local LaMa eraser (.venv-iopaint) — no fal cost.
            engine_id = "lama_local"
            eng = [VENV_IOPAINT, R/"lama_erase.py", "--image", ctx, "--mask", ctx_mask,
                   "--out", regen]
        else:
            if a.free:
                # degrade gracefully so --free never silently no-ops the edit
                print(f"  [warn] --free requested but {VENV_IOPAINT} missing; "
                      f"falling back to fal Bria eraser")
            engine_id = "fal_bria"
            eng = [PY, R/"falgen.py", "--mode", "eraser", "--image", ctx, "--mask", ctx_mask,
                   "--out", regen, "--maxside", "1400", "--cache"]
    else:  # redraw
        engine_id = "fal_flux_fill"
        prompt = subprocess.run([str(PY), str(R/"prompt_templates.py"), "redraw", "--element", a.element,
                                 "--desc", a.desc], capture_output=True, text=True).stdout.strip()
        (work/"p.txt").write_text(prompt)
        eng = [PY, R/"falgen.py", "--mode", "fill", "--image", ctx, "--mask", ctx_mask,
               "--out", regen, "--prompt-file", work/"p.txt", "--maxside", "1400", "--seed", a.seed, "--cache"]
    if run(eng).returncode != 0:
        raise SystemExit("[edit] engine failed")

    # 5) composite back + pixel gate
    comp = run([PY, R/"compose_fairy.py", "--orig", src, "--regen", regen, "--out", out,
                "--crop", f"{cx0},{cy0},{cx1},{cy1}", "--mask", f"{ex0},{ey0},{ex1},{ey1}",
                "--diffmask", "--diff-thresh", "28", "--diff-close", "5", "--diff-dilate", "3", "--diff-feather", "3"])
    gate_ok = comp.returncode == 0 and "outside_max_delta=0" in comp.stdout  # returncode guards a crashed compose

    # 6) judge the result region
    jcrop_box = (max(0,ex0-60), max(0,ey0-60), min(W,ex1+60), min(H,ey1+60))
    verdict, jcrop = judge_region(out, jcrop_box, a.element, work)

    # 7) AUTO-GATES (cross-venv, non-fatal): perceptual leak + leftover-text OCR.
    #    Each runs in its own sub-venv; a missing venv / nonzero error degrades to a
    #    warning (gate marked unavailable, never blocks). Exit codes fold into the
    #    decision: leak_metric 0=PASS; text_gate 0=no-text.
    #    text_gate is now run for BOTH ops (a clean redraw must also be text-free);
    #    for redraw it both folds into the decision AND seeds the auto-repair loop.
    # leak_metric needs a FULL-SIZE mask whose white = the EDITED region; synthesize
    # one from the full-coord element bbox (ex0,ey0,ex1,ey1).
    fullmask = work / "fullmask.png"
    _fm = Image.new("L", (W, H), 0)
    from PIL import ImageDraw as _ImageDraw
    _ImageDraw.Draw(_fm).rectangle([ex0, ey0, ex1, ey1], fill=255)
    _fm.save(fullmask)

    leak = {"available": False}
    if VENV_METRIC.exists():
        lj = work / "leak.json"
        lp = run([VENV_METRIC, R/"leak_metric.py", "--orig", src, "--edited", out,
                  "--mask", fullmask, "--json", lj])
        leak = {"available": True, "exit_code": lp.returncode}
        try:
            leak.update(json.loads(lj.read_text()))
        except Exception:
            pass
        leak["pass"] = (lp.returncode == 0)
    else:
        print(f"  [warn] leak_metric SKIPPED: {VENV_METRIC} missing")

    # text gate applies to BOTH ops: an unwanted "TAXI"/"CLASSIC" stamped by the
    # redraw engine is exactly the leftover text we want to catch + auto-erase.
    textgate = run_text_gate(jcrop, applicable=True)

    # 8) SELF-HEALING auto-repair (redraw only): if the redraw came back with
    #    unwanted text, locate + erase it, re-gate, up to MAX_REPAIR passes. Each
    #    pass: get text boxes from the OCR gate (PaddleOCR) and erase exactly those
    #    (fal Bria eraser on a context crop -> diffmask composite); if no boxes are
    #    available, fall back to automask over the element bbox. Bounded + graceful:
    #    a missing eraser/key or an unlocatable text run leaves the result as-is so
    #    the decision step can still mark NEEDS-REVIEW (never fakes success).
    MAX_REPAIR = 2
    repair_passes = 0
    repair_log = []
    if a.op == "redraw":
        repair_passes, repair_log, verdict, textgate = autorepair_text(
            a, src, out, work, W, H,
            (ex0, ey0, ex1, ey1), jcrop_box, verdict, textgate, MAX_REPAIR)

    # overlay
    ov = out.with_name(out.stem + "_editov.png")
    Image.open(out).convert("RGB").crop((max(0,cx0-40),max(0,cy0-40),min(W,cx1+40),min(H,cy1+40))).save(ov)

    # ---- fold gates into the SUCCESS/NEEDS-REVIEW decision ----
    # Auto-gates only BLOCK when available and failing; an unavailable (skipped) gate
    # does not flip a pass to a fail (graceful degradation). text_gate now blocks for
    # BOTH ops — after auto-repair, the post-repair textgate reflects the final state,
    # so a still-failing gate correctly keeps the result NEEDS-REVIEW (no faked pass).
    leak_blocks = leak.get("available") and not leak.get("pass")
    text_blocks = textgate.get("available") and textgate.get("applicable") and not textgate.get("no_text")
    if a.op == "remove":
        ok = (gate_ok and (verdict.get("leftover_text") is False)
              and not leak_blocks and not text_blocks)
    else:
        ok = (gate_ok and (verdict.get("verdict") == "PASS") and (verdict.get("leftover_text") is False)
              and not leak_blocks and not text_blocks)

    print(f"\n[edit] DONE -> {out}")
    print(f"  pixel gate outside-mask delta 0: {gate_ok}")
    print(f"  judge: leftover_text={verdict.get('leftover_text')} text={verdict.get('text_found')} "
          f"artifacts={verdict.get('artifacts')} verdict={verdict.get('verdict')}")
    if leak.get("available"):
        print(f"  leak_metric: verdict={leak.get('verdict')} leak_score={leak.get('leak_score')} "
              f"ssim_outside={leak.get('ssim_outside')} lpips_outside={leak.get('lpips_outside')} "
              f"dino_outside={leak.get('dino_outside')} (exit={leak.get('exit_code')})")
    else:
        print(f"  leak_metric: UNAVAILABLE (skipped)")
    if textgate.get("available"):
        print(f"  text_gate: no_text={textgate.get('no_text')} found={textgate.get('found')} "
              f"(exit={textgate.get('exit_code')})")
    else:
        print(f"  text_gate: UNAVAILABLE (skipped)")
    if a.op == "redraw":
        print(f"  auto-repair: passes={repair_passes} log={json.dumps(repair_log)}")
    print(f"  overlay -> {ov}")

    # ---- provenance sidecar (<out>.json): everything needed to reproduce/audit ----
    prov = {
        "src": str(src),
        "op": a.op,
        "element": a.element,
        "desc": a.desc if a.op == "redraw" else None,
        "box": a.box,
        "free": bool(a.free),
        "engine": engine_id,
        "seed": a.seed,
        "mask_dilate": a.mask_dilate,
        "ctx_pad": a.ctx_pad,
        "src_size": [W, H],
        "crop": [cx0, cy0, cx1, cy1],          # context crop fed to the engine
        "mask_bbox": [ex0, ey0, ex1, ey1],     # full-coord element bbox (edit region)
        "jcrop": [jcrop_box[0], jcrop_box[1], jcrop_box[2], jcrop_box[3]],
        "out": str(out),
        "overlay": str(ov),
        "pixel_gate_ok": bool(gate_ok),
        "leak_metric": leak,
        "text_gate": textgate,
        "judge": verdict,
        "repair_passes": repair_passes,        # self-healing text-erase passes run
        "repair_log": repair_log,              # per-pass method/bbox/clear status
        "result": "SUCCESS" if ok else "NEEDS-REVIEW",
        "timestamp": None,                     # harness has no clock; placeholder
        "tool_versions": {"git_rev": git_rev()},
    }
    prov_path = Path(str(out) + ".json")
    prov_path.write_text(json.dumps(prov, indent=2))
    print(f"  provenance -> {prov_path}")

    print(f"  RESULT: {'SUCCESS' if ok else 'NEEDS-REVIEW'} (op={a.op})")
    raise SystemExit(0 if ok else 2)


if __name__ == "__main__":
    main()
