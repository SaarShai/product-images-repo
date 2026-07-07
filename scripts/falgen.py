#!/usr/bin/env python3
"""falgen.py — image edit via fal.ai (Flux Fill masked inpaint / Flux Kontext instruction edit / Flux.2 edit).

The high-ceiling engine: hosted Flux on real GPUs. Reads FAL_KEY from .secrets/fal.env.
Auth scheme is `Key <id:secret>` (NOT Bearer). Local images are sent as base64 data URIs.

Modes:
  fill      : fal-ai/flux-pro/v1/fill  — masked inpaint (mask white=repaint). Best for "change nothing else".
  kontext   : fal-ai/flux-pro/kontext  — instruction edit (whole image; strong consistency).
  flux2edit : fal-ai/flux-2-pro/edit   — reference-based edit (prose + up to 9 refs).

Usage (fill):
  python3 scripts/falgen.py --mode fill --image CROP.png --out OUT.png --prompt-file P.md \
      --mask-box 100,100,420,550 --feather 24
Usage (kontext):
  python3 scripts/falgen.py --mode kontext --image CROP.png --out OUT.png --prompt "redraw only the fairy ..."
"""
import argparse, base64, hashlib, io, json, os, sys
from pathlib import Path
import requests
from PIL import Image, ImageDraw, ImageFilter
from _falcommon import load_fal_key as load_key, data_uri

ENDPOINTS = {
    "fill": "fal-ai/flux-pro/v1/fill",
    "kontext": "fal-ai/flux-pro/kontext",
    "flux2edit": "fal-ai/flux-2-pro/edit",
    "i2i": "fal-ai/flux/dev/image-to-image",   # low-strength img2img: keep structure, restyle. --strength (0=keep, 1=ignore)
    "eraser": "fal-ai/bria/eraser",
    "fluxgeneral": "fal-ai/flux-general",
    "kontextlora": "fal-ai/flux-kontext-lora",
    "kontextmax": "fal-ai/flux-pro/kontext/max",
    "aurasr": "fal-ai/aura-sr",
    "falesrgan": "fal-ai/esrgan",
    "nbpro": "fal-ai/nano-banana-pro/edit",
    "gptimg2": "openai/gpt-image-2/edit",
}

LEGACY_IMAGE_MODES = {"fill", "kontext", "flux2edit", "i2i", "eraser"}
IMAGE_REQUIRED_MODES = LEGACY_IMAGE_MODES | {"kontextlora", "kontextmax", "aurasr", "falesrgan", "nbpro", "gptimg2"}


def parse_image_size(value):
    try:
        w, h = value.lower().split("x", 1)
        w, h = int(w), int(h)
    except Exception as exc:
        raise argparse.ArgumentTypeError("--image-size must be WxH, e.g. 1024x1536") from exc
    if w <= 0 or h <= 0:
        raise argparse.ArgumentTypeError("--image-size width/height must be positive")
    return {"width": w, "height": h}


def parse_loras(values):
    if not values:
        return []
    if len(values) == 1:
        raw = values[0]
        path = Path(raw)
        if raw.lstrip().startswith("["):
            return json.loads(raw)
        if path.exists() and path.is_file() and path.suffix.lower() == ".json":
            return json.loads(path.read_text())
    loras = []
    for item in values:
        if "," not in item:
            raise SystemExit(f"--loras item must be JSON/list file or path,scale pair: {item}")
        path, scale = item.rsplit(",", 1)
        loras.append({"path": path, "scale": float(scale)})
    return loras


def is_url(value):
    return value.startswith(("http://", "https://", "data:"))


def image_value(value, dry_run=False):
    if not value:
        return None
    if dry_run or is_url(value):
        return value
    return data_uri(Image.open(value).convert("RGB"))


def dry_run(endpoint, body, mode=None, argv=None):
    record = {"endpoint": endpoint, "arguments": body, "dry_run": True}
    if mode is not None:
        record["mode"] = mode
    if argv is not None:
        record["cli_argv"] = argv
    print(json.dumps(record, indent=2))


def request_sha256(body):
    blob = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def input_paths_from_args(a):
    """Original CLI-given path/string values (never base64/URL-resolved) — the
    'as given' provenance that image_value()/data_uri() overwrite in the live
    request body. Keys are only included when set, so recovery tools can tell
    a path was actually passed."""
    fields = ("image", "refs", "mask", "control_image", "ref_image", "ip_adapter")
    paths = {}
    for f in fields:
        v = getattr(a, f, None)
        if v:
            paths[f] = v
    return paths


def redact_data_uris(value):
    """Deep-copy `value`, replacing inline base64 data-URI strings with a short
    marker. Keeps the artifact JSON small and free of huge blobs; the actual
    source paths for those fields are recovered from input_paths instead."""
    if isinstance(value, str):
        if value.startswith("data:") and ";base64," in value:
            return f"<data-uri redacted, {len(value)} chars>"
        return value
    if isinstance(value, dict):
        return {k: redact_data_uris(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact_data_uris(v) for v in value]
    return value


def seed_from_response(response):
    for key in ("seed", "seeds"):
        if key in response:
            return response[key]
    for item in response.get("images") or []:
        if isinstance(item, dict) and "seed" in item:
            return item["seed"]
    if isinstance(response.get("image"), dict) and "seed" in response["image"]:
        return response["image"]["seed"]
    return None


def write_artifact(out, endpoint, mode, body, response, requested_size, input_paths=None, argv=None):
    out_path = Path(out)
    try:
        with Image.open(out_path) as im:
            actual_size = {"width": im.width, "height": im.height}
    except Exception:
        actual_size = None
    record = {
        "endpoint": endpoint,
        "mode": mode,
        "requested_size": requested_size,
        "actual_size": actual_size,
        "seed_used": seed_from_response(response),
        "request_sha256": request_sha256(body),
        "response_keys": sorted(response.keys()),
        # full provenance (t1 lesson: MRWC LoRA path was unrecoverable) — never includes
        # FAL_KEY/secrets; inline base64 image data is redacted (input_paths below
        # carries the actual source paths as given on the CLI instead).
        "arguments": redact_data_uris(body),
        "input_paths": input_paths or {},
        "cli_argv": argv or [],
    }
    Path(str(out_path) + ".artifact.json").write_text(json.dumps(record, indent=2) + "\n")


def build_fluxgeneral(a, prompt, dry=False):
    if not a.image_size:
        raise SystemExit("--image-size WxH is required for --mode fluxgeneral")
    body = {
        "prompt": prompt,
        "image_size": a.image_size,
        "output_format": "png",
        "num_images": 1,
    }
    loras = parse_loras(a.loras)
    if loras:
        body["loras"] = loras
    if a.control_image:
        # LIVE-SCHEMA FIX (422 probe, 2026-07-05): controlnet_unions items REQUIRE a
        # "path" (union model weights) + nested "controls" list — a bare
        # control_image_url is rejected. For our use (pre-rendered edge maps) the
        # right surface is control_loras (ControlLoraWeight: path/scale/
        # control_image_url/preprocess), using the BFL canny control-LoRA with
        # preprocess "None" because our control map already IS an edge image.
        body["control_loras"] = [{
            "path": "https://huggingface.co/black-forest-labs/FLUX.1-Canny-dev-lora/resolve/main/flux1-canny-dev-lora.safetensors",
            "control_image_url": image_value(a.control_image, dry),
            "scale": a.control_scale,
            "preprocess": "None",
        }]
    if a.ref_image:
        # see FAL-CAPABILITIES.md §N2: reference_image_url/reference_strength style lock.
        body["reference_image_url"] = image_value(a.ref_image, dry)
        body["reference_strength"] = a.ref_strength
    if a.ip_adapter:
        # see FAL-CAPABILITIES.md §N2: flux-general exposes ip_adapters.
        body["ip_adapters"] = [{"image_url": image_value(a.ip_adapter, dry)}]
    return body, a.image_size


def build_kontextlora(a, prompt, dry=False):
    # see FAL-CAPABILITIES.md §N2: flux-kontext-lora supports LoRA edits with match_input.
    body = {
        "prompt": prompt,
        "image_url": image_value(a.image, dry),
        "resolution_mode": a.resolution_mode,
        "output_format": "png",
    }
    loras = parse_loras(a.loras)
    if loras:
        body["loras"] = loras
    return body, None


def build_kontextmax(a, prompt, dry=False):
    # premium instruction-restyle endpoint (no LoRA support); minimal payload
    # per fal-ai/flux-pro/kontext/max schema.
    body = {
        "prompt": prompt,
        "image_url": image_value(a.image, dry),
        "output_format": "png",
    }
    if a.guidance is not None:
        body["guidance_scale"] = a.guidance
    return body, None


def build_aurasr(a, dry=False):
    # see FAL-CAPABILITIES.md §N4: AuraSR is the faithful 4x overlapping-tile branch.
    return {
        "image_url": image_value(a.image, dry),
        "overlapping_tiles": a.overlapping_tiles,
        "checkpoint": a.checkpoint,
    }, None


def build_falesrgan(a, dry=False):
    # see FAL-CAPABILITIES.md §N4: ESRGAN exposes scale and tile for large-image fallback.
    return {
        "image_url": image_value(a.image, dry),
        "scale": a.esrgan_scale,
        "tile": a.tile,
        "output_format": "png",
    }, None


def build_nbpro(a, prompt, dry=False):
    # premium named-tier edit: fal-ai/nano-banana-pro/edit. image_urls[] = primary + refs.
    # ENFORCEMENT: nano recomposes tall die-cut panels (aspect < 0.75).
    # Compute aspect ratio from primary image and check before building payload.
    # Check always applies (both dry-run and live), unless --force-nano is set.
    img = Image.open(a.image).convert("RGB")
    aspect = img.width / img.height
    if aspect < 0.75:
        if not getattr(a, "force_nano", False):
            raise SystemExit(
                "nano recomposes tall panels; use gpt-image path\n"
                "If you intend to use nano anyway, pass --force-nano"
            )
        else:
            print(
                f"WARNING: nano enforces 2:3 aspect ratio; "
                f"tall panel aspect {aspect:.3f} < 0.75 will be recomposed",
                file=sys.stderr
            )

    image_urls = [image_value(a.image, dry)] + [image_value(r, dry) for r in a.refs]
    return {
        "prompt": prompt,
        "image_urls": image_urls,
        "aspect_ratio": "2:3",
        "resolution": "2K",
        "output_format": "png",
        "num_images": getattr(a, "num_images", None) or 1,
    }, None


def build_gptimg2(a, prompt, dry=False):
    # premium named-tier edit: openai/gpt-image-2/edit. image_urls[] = primary + refs.
    image_urls = [image_value(a.image, dry)] + [image_value(r, dry) for r in a.refs]
    return {
        "prompt": prompt,
        "image_urls": image_urls,
        "image_size": {"width": 832, "height": 1184},
        "quality": "high",
        "output_format": "png",
        "num_images": 1,
    }, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", required=True, choices=list(ENDPOINTS))
    ap.add_argument("--image")
    ap.add_argument("--refs", nargs="*", default=[], help="extra reference images (flux2edit only; appended to image_urls)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--prompt"); ap.add_argument("--prompt-file")
    ap.add_argument("--mask"); ap.add_argument("--mask-box"); ap.add_argument("--feather", type=int, default=24)
    ap.add_argument("--maxside", type=int, default=1024, help="resize longer side to this before sending")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--guidance", type=float, default=None)
    ap.add_argument("--strength", type=float, default=None, help="i2i denoise strength (low=keep structure, e.g. 0.3)")
    ap.add_argument("--cache", action="store_true", help="reuse cached result for identical deterministic calls")
    ap.add_argument("--dry-run", action="store_true", help="print request JSON for new modes; no spend")
    ap.add_argument("--image-size", type=parse_image_size, help="fluxgeneral size as WxH")
    ap.add_argument("--loras", nargs="*", default=[], help="JSON list/file or path,scale pairs")
    ap.add_argument("--control-image")
    ap.add_argument("--control-scale", type=float, default=0.5)
    ap.add_argument("--control-mode", choices=["canny", "depth"])
    ap.add_argument("--ref-image")
    ap.add_argument("--ref-strength", type=float, default=0.5)
    ap.add_argument("--ip-adapter")
    ap.add_argument("--resolution-mode", default="match_input")
    ap.add_argument("--overlapping-tiles", dest="overlapping_tiles", action="store_true", default=True)
    ap.add_argument("--no-overlapping-tiles", dest="overlapping_tiles", action="store_false")
    ap.add_argument("--checkpoint", choices=["v1", "v2"], default="v2")
    ap.add_argument("--esrgan-scale", type=int, default=4)
    ap.add_argument("--tile", type=int, default=0)
    ap.add_argument("--num-images", dest="num_images", type=int, default=None, help="nbpro: num_images (default 1)")
    ap.add_argument("--force-nano", dest="force_nano", action="store_true", default=False, help="nbpro: proceed even for tall panels (aspect < 0.75)")
    a = ap.parse_args()

    prompt = a.prompt or (Path(a.prompt_file).read_text() if a.prompt_file else "")
    if a.mode in IMAGE_REQUIRED_MODES and not a.image:
        ap.error(f"--image is required for --mode {a.mode}")

    ckey = None
    sent_label = "n/a"
    if a.mode == "fluxgeneral":
        body, requested_size = build_fluxgeneral(a, prompt, dry=a.dry_run)
    elif a.mode == "kontextlora":
        body, requested_size = build_kontextlora(a, prompt, dry=a.dry_run)
    elif a.mode == "kontextmax":
        body, requested_size = build_kontextmax(a, prompt, dry=a.dry_run)
    elif a.mode == "aurasr":
        body, requested_size = build_aurasr(a, dry=a.dry_run)
    elif a.mode == "falesrgan":
        body, requested_size = build_falesrgan(a, dry=a.dry_run)
    elif a.mode == "nbpro":
        body, requested_size = build_nbpro(a, prompt, dry=a.dry_run)
    elif a.mode == "gptimg2":
        body, requested_size = build_gptimg2(a, prompt, dry=a.dry_run)
    else:
        img = Image.open(a.image).convert("RGB")
        if a.maxside:
            w, h = img.size; s = a.maxside / max(w, h)
            if s < 1:
                img = img.resize((round(w * s), round(h * s)), Image.LANCZOS)
        W, H = img.size
        requested_size = {"width": W, "height": H}
        sent_label = f"{W}x{H}"

        # cache only deterministic calls: eraser (no seed) or an explicit seed was given
        import sys as _sys
        _sys.path.insert(0, str(Path(__file__).resolve().parent))
        from gencache import cache_key, cache_get, cache_put
        deterministic = (a.mode == "eraser") or (a.seed is not None)
        if a.cache and deterministic:
            mb = Path(a.mask).read_bytes() if a.mask else (a.mask_box or "")
            ckey = cache_key(a.mode, a.image, prompt, mb, a.seed if a.seed is not None else "", a.guidance or "", a.maxside, a.feather)
            hit = cache_get(ckey)
            if hit:
                Path(a.out).parent.mkdir(parents=True, exist_ok=True)
                import shutil; shutil.copy(hit, a.out)
                print(f"[falgen] CACHE HIT mode={a.mode} -> {a.out} (0 API calls)"); return
        elif a.cache and not deterministic:
            print("[falgen] --cache ignored: non-deterministic call (set --seed to enable caching)", file=sys.stderr)

        if a.mode == "eraser":
            body = {"image_url": data_uri(img)}  # bria eraser: image_url + mask_url, no prompt
        elif a.mode == "flux2edit":
            # flux-2-pro/edit takes image_urls[] (up to 9 refs) + prose; resize refs to maxside
            def _ref(p):
                r = Image.open(p).convert("RGB")
                if a.maxside:
                    w, h = r.size; s = a.maxside / max(w, h)
                    if s < 1: r = r.resize((round(w * s), round(h * s)), Image.LANCZOS)
                return data_uri(r)
            body = {"prompt": prompt, "image_urls": [data_uri(img)] + [_ref(r) for r in a.refs],
                    "output_format": "png", "num_images": 1}
        else:
            body = {"prompt": prompt, "image_url": data_uri(img), "output_format": "png", "num_images": 1}
        if a.mode == "i2i" and a.strength is not None: body["strength"] = a.strength
        # fal Flux safety checker false-flags innocuous content (e.g. skin/fairy hands) and
        # returns a BLANK BLACK image. Disable it + max tolerance so legit edits aren't blanked.
        body["enable_safety_checker"] = False
        if a.mode != "i2i":  # safety_tolerance is a flux-pro param; flux/dev i2i rejects it
            body["safety_tolerance"] = "5" if a.mode == "flux2edit" else "6"  # flux-2-pro validates 1-5; kontext/fill accept 6

        if a.mode in ("fill", "eraser"):
            if a.mask:
                m = Image.open(a.mask).convert("L").resize((W, H))
            else:
                m = Image.new("L", (W, H), 0)
                if a.mask_box:
                    x0, y0, x1, y1 = (int(v) for v in a.mask_box.split(","))
                    ImageDraw.Draw(m).rectangle([x0, y0, x1, y1], fill=255)  # white=repaint/erase
                    if a.feather > 0: m = m.filter(ImageFilter.GaussianBlur(a.feather))
            body["mask_url"] = data_uri(m.convert("RGB"))

    if a.seed is not None: body["seed"] = a.seed
    if a.guidance is not None: body["guidance_scale"] = a.guidance

    if a.dry_run:
        if a.mode not in {"fluxgeneral", "kontextlora", "kontextmax", "aurasr", "falesrgan", "nbpro", "gptimg2"}:
            raise SystemExit("--dry-run is supported for fluxgeneral, kontextlora, kontextmax, aurasr, falesrgan, nbpro, and gptimg2")
        dry_run(ENDPOINTS[a.mode], body, mode=a.mode, argv=sys.argv)
        return

    key = load_key()
    url = f"https://fal.run/{ENDPOINTS[a.mode]}"
    r = requests.post(url, headers={"Authorization": f"Key {key}", "Content-Type": "application/json"},
                      json=body, timeout=300)
    if r.status_code != 200:
        print(f"ERROR {r.status_code}: {r.text[:600]}", file=sys.stderr); raise SystemExit(1)
    j = r.json()
    imgs = j.get("images") or ([j["image"]] if j.get("image") else [])
    if not imgs:
        print(f"no images in response: {str(j)[:400]}", file=sys.stderr); raise SystemExit(1)
    out_url = imgs[0]["url"] if isinstance(imgs[0], dict) else imgs[0]
    data = requests.get(out_url, timeout=120).content
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_bytes(data)
    write_artifact(a.out, ENDPOINTS[a.mode], a.mode, body, j, requested_size,
                   input_paths=input_paths_from_args(a), argv=sys.argv)
    if ckey is not None:
        cache_put(ckey, a.out)
    print(f"[falgen] OK mode={a.mode} -> {a.out}  sent={sent_label} seed={j.get('seed')}")


if __name__ == "__main__":
    main()
