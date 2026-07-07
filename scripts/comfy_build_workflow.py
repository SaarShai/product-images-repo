#!/usr/bin/env python3
"""Build ComfyUI API-format workflow JSON for the C2 experiment arms.

Outputs an API-format dict (node-id -> {class_type, inputs}) suitable for
POST /prompt. Image inputs are referenced by filename relative to
~/ComfyUI/input; use --stage-inputs to copy local source files there first.

Examples:
  comfy_build_workflow.py --arm geometry --control-map guide.png --out geom.json
  comfy_build_workflow.py --arm style --refs r1.png r2.png --out style.json
  comfy_build_workflow.py --arm combined --control-map line.png --refs r1.png \
      --depth-map depth.png --out combined.json
  comfy_build_workflow.py --arm regional --control-map line.png --refs r1.png \
      --mask door-portal-mask.png --out regional.json --stage-inputs
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Iterable


ARMS = ("geometry", "style", "combined", "regional", "dualregion")
CONTROL_ARMS = {"geometry", "combined", "regional", "dualregion"}
IP_ARMS = {"style", "combined", "regional", "dualregion"}


def _ref(node_id: str, slot: int = 0) -> list[object]:
    return [node_id, slot]


class GraphBuilder:
    def __init__(self) -> None:
        self.graph: dict[str, dict] = {}
        self._next_id = 1

    def add(self, class_type: str, inputs: dict) -> str:
        node_id = str(self._next_id)
        self._next_id += 1
        self.graph[node_id] = {"class_type": class_type, "inputs": inputs}
        return node_id


def build(args) -> dict:
    if args.arm not in ARMS:
        raise ValueError(f"unknown arm: {args.arm}")
    if args.arm in CONTROL_ARMS and not args.control_map_name:
        raise ValueError(f"--arm {args.arm} requires --control-map or --control-map-name")
    if args.arm in IP_ARMS and not args.ref_names:
        raise ValueError(f"--arm {args.arm} requires --refs or --ref-names")
    if args.arm == "regional" and not args.mask_name:
        raise ValueError("--arm regional requires --mask or --mask-name")
    if args.arm == "dualregion":
        if not args.mask_name:
            raise ValueError("--arm dualregion requires --mask or --mask-name")
        if not args.refs2_names:
            raise ValueError("--arm dualregion requires --refs2 or --refs2-names")
        if not args.mask2_name:
            raise ValueError("--arm dualregion requires --mask2 or --mask2-name")
    if args.ref_names and not (1 <= len(args.ref_names) <= 3):
        raise ValueError("--refs/--ref-names accepts 1-3 reference images")
    if args.refs2_names and not (1 <= len(args.refs2_names) <= 3):
        raise ValueError("--refs2/--refs2-names accepts 1-3 reference images")
    if args.depth_map_name and args.arm not in {"combined", "regional", "dualregion"}:
        raise ValueError("--depth-map/--depth-map-name is only valid for combined, regional, or dualregion arms")
    if not (0.0 <= args.cn_start_percent <= 1.0):
        raise ValueError("--cn-start-percent must be between 0 and 1")
    if not (0.0 <= args.cn_end_percent <= 1.0):
        raise ValueError("--cn-end-percent must be between 0 and 1")
    if args.hires_scale is not None and args.hires_scale <= 0:
        raise ValueError("--hires-scale must be greater than 0")

    neg = args.negative_prompt
    b = GraphBuilder()

    checkpoint = b.add("CheckpointLoaderSimple", {"ckpt_name": args.ckpt})
    positive_prompt = b.add("CLIPTextEncode", {"text": args.prompt, "clip": _ref(checkpoint, 1)})
    negative_prompt = b.add("CLIPTextEncode", {"text": neg, "clip": _ref(checkpoint, 1)})
    if args.init_name:
        init_image = b.add("LoadImage", {"image": args.init_name})
        latent = b.add("VAEEncode", {"pixels": _ref(init_image, 0), "vae": _ref(checkpoint, 2)})
    else:
        latent = b.add(
            "EmptyLatentImage",
            {"width": args.width, "height": args.height, "batch_size": args.batch_size},
        )

    model_ref = _ref(checkpoint, 0)
    positive_ref = _ref(positive_prompt, 0)
    negative_ref = _ref(negative_prompt, 0)

    if args.arm in CONTROL_ARMS:
        positive_ref, negative_ref = _apply_controlnet(
            b,
            positive_ref,
            negative_ref,
            args.control_map_name,
            args.controlnet,
            args.control_strength,
            args.cn_start_percent,
            args.cn_end_percent,
        )
        if args.depth_map_name:
            positive_ref, negative_ref = _apply_controlnet(
                b,
                positive_ref,
                negative_ref,
                args.depth_map_name,
                args.depth_controlnet,
                args.depth_strength,
                args.cn_start_percent,
                args.cn_end_percent,
            )

    if args.arm in IP_ARMS:
        model_ref = _apply_ipadapter(b, model_ref, args)

    sample = b.add(
        "KSampler",
        {
            "model": model_ref,
            "positive": positive_ref,
            "negative": negative_ref,
            "latent_image": _ref(latent, 0),
            "seed": args.seed,
            "steps": args.steps,
            "cfg": args.cfg,
            "sampler_name": args.sampler,
            "scheduler": args.scheduler,
            "denoise": args.denoise,
        },
    )
    if args.hires_scale is not None:
        upscaled = b.add(
            "LatentUpscaleBy",
            {"samples": _ref(sample, 0), "upscale_method": "nearest-exact", "scale_by": args.hires_scale},
        )
        sample = b.add(
            "KSampler",
            {
                "model": model_ref,
                "positive": positive_ref,
                "negative": negative_ref,
                "latent_image": _ref(upscaled, 0),
                "seed": args.seed + 1,
                "steps": args.steps,
                "cfg": args.cfg,
                "sampler_name": args.sampler,
                "scheduler": args.scheduler,
                "denoise": args.hires_denoise,
            },
        )
    decoded = b.add("VAEDecode", {"samples": _ref(sample, 0), "vae": _ref(checkpoint, 2)})
    b.add("SaveImage", {"images": _ref(decoded, 0), "filename_prefix": args.prefix})
    return b.graph


def _apply_controlnet(
    b: GraphBuilder,
    positive_ref: list[object],
    negative_ref: list[object],
    image_name: str,
    controlnet_name: str,
    strength: float,
    start_percent: float,
    end_percent: float,
) -> tuple[list[object], list[object]]:
    image = b.add("LoadImage", {"image": image_name})
    controlnet = b.add("ControlNetLoader", {"control_net_name": controlnet_name})
    applied = b.add(
        "ControlNetApplyAdvanced",
        {
            "positive": positive_ref,
            "negative": negative_ref,
            "control_net": _ref(controlnet, 0),
            "image": _ref(image, 0),
            "strength": strength,
            "start_percent": start_percent,
            "end_percent": end_percent,
        },
    )
    return _ref(applied, 0), _ref(applied, 1)


def _apply_ipadapter(b: GraphBuilder, model_ref: list[object], args) -> list[object]:
    ipadapter = b.add("IPAdapterModelLoader", {"ipadapter_file": args.ipadapter})
    clip_vision = b.add("CLIPVisionLoader", {"clip_name": args.clip_vision})
    if args.arm == "dualregion":
        model_ref = _apply_ipadapter_region(
            b,
            model_ref,
            _ref(ipadapter, 0),
            _ref(clip_vision, 0),
            args.ref_names,
            args.mask_name,
            args.ip_weight,
            args,
        )
        return _apply_ipadapter_region(
            b,
            model_ref,
            _ref(ipadapter, 0),
            _ref(clip_vision, 0),
            args.refs2_names,
            args.mask2_name,
            args.ip_weight2,
            args,
        )

    image_ref = _load_ref_batch(b, args.ref_names)

    inputs = {
        "model": model_ref,
        "ipadapter": _ref(ipadapter, 0),
        "image": image_ref,
        "clip_vision": _ref(clip_vision, 0),
        "weight": args.ip_weight,
        "weight_type": args.ip_weight_type,
        "combine_embeds": args.combine_embeds,
        "start_at": 0.0,
        "end_at": 1.0,
        "embeds_scaling": args.embeds_scaling,
    }
    if args.arm == "regional":
        mask = b.add("LoadImage", {"image": args.mask_name})
        inputs["attn_mask"] = _ref(mask, 1)

    return _ref(b.add("IPAdapterAdvanced", inputs), 0)


def _apply_ipadapter_region(
    b: GraphBuilder,
    model_ref: list[object],
    ipadapter_ref: list[object],
    clip_vision_ref: list[object],
    ref_names: list[str],
    mask_name: str,
    weight: float,
    args,
) -> list[object]:
    image_ref = _load_ref_batch(b, ref_names)
    mask = b.add("LoadImage", {"image": mask_name})
    return _ref(
        b.add(
            "IPAdapterAdvanced",
            {
                "model": model_ref,
                "ipadapter": ipadapter_ref,
                "image": image_ref,
                "clip_vision": clip_vision_ref,
                "weight": weight,
                "weight_type": args.ip_weight_type,
                "combine_embeds": args.combine_embeds,
                "start_at": 0.0,
                "end_at": 1.0,
                "embeds_scaling": args.embeds_scaling,
                "attn_mask": _ref(mask, 1),
            },
        ),
        0,
    )


def _load_ref_batch(b: GraphBuilder, ref_names: list[str]) -> list[object]:
    last_image = None
    for ref_name in ref_names:
        image = b.add("LoadImage", {"image": ref_name})
        if last_image is None:
            last_image = image
        else:
            last_image = b.add("ImageBatch", {"image1": _ref(last_image, 0), "image2": _ref(image, 0)})
    if last_image is None:
        raise ValueError("at least one reference image is required")
    return _ref(last_image, 0)


def graph_references(graph: dict) -> Iterable[tuple[str, str, str, int]]:
    for node_id, node in graph.items():
        for input_name, value in node.get("inputs", {}).items():
            if _is_node_ref(value):
                yield node_id, input_name, value[0], value[1]


def validate_graph(graph: dict) -> None:
    missing = []
    for node_id, input_name, ref_id, slot in graph_references(graph):
        if ref_id not in graph:
            missing.append(f"{node_id}.{input_name} -> {ref_id}[{slot}]")
    if missing:
        raise ValueError("missing node references: " + ", ".join(missing))


def _is_node_ref(value: object) -> bool:
    return (
        isinstance(value, list)
        and len(value) == 2
        and isinstance(value[0], str)
        and isinstance(value[1], int)
    )


def stage_inputs(args) -> None:
    input_dir = args.comfy_input_dir.expanduser()
    staged: list[tuple[Path, str]] = []
    if args.ref_names and not args.refs:
        raise ValueError("--stage-inputs needs --refs source paths for reference images")
    if args.refs and len(args.refs) != len(args.ref_names or []):
        raise ValueError("--refs and --ref-names must have the same length when staging")
    if args.refs2 and len(args.refs2) != len(args.refs2_names or []):
        raise ValueError("--refs2 and --refs2-names must have the same length when staging")
    for src, name in (
        (args.control_map, args.control_map_name),
        (args.depth_map, args.depth_map_name),
        (args.mask, args.mask_name),
        (args.mask2, args.mask2_name),
        (args.init_image, args.init_name),
    ):
        if name:
            staged.extend(_stage_pair(src, name))
    for src, name in zip(args.refs or [], args.ref_names or []):
        staged.extend(_stage_pair(src, name))
    for src, name in zip(args.refs2 or [], args.refs2_names or []):
        staged.extend(_stage_pair(src, name))

    for src, name in staged:
        dest = input_dir / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        print(f"staged {src} -> {dest}", file=sys.stderr)


def _stage_pair(src: Path | None, name: str) -> list[tuple[Path, str]]:
    if src is None:
        raise ValueError(f"--stage-inputs needs a source path for {name}")
    return [(src, name)]


def _image_name(path: Path | None, explicit_name: str | None) -> str | None:
    if explicit_name:
        return explicit_name
    if path is not None:
        return path.name
    return None


def parse_args(argv: list[str] | None = None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=ARMS, default="combined")
    ap.add_argument("--control-map", type=Path, help="local control map path, optionally staged")
    ap.add_argument("--control-map-name", help="control map filename in ComfyUI/input/")
    ap.add_argument("--refs", nargs="+", type=Path, help="1-3 local reference image paths, optionally staged")
    ap.add_argument("--ref-names", nargs="+", help="1-3 reference filenames in ComfyUI/input/")
    ap.add_argument("--refs2", nargs="+", type=Path, help="1-3 second-region reference image paths, optionally staged")
    ap.add_argument("--refs2-names", nargs="+", help="1-3 second-region reference filenames in ComfyUI/input/")
    ap.add_argument("--depth-map", type=Path, help="optional local depth map path for combined/regional arms")
    ap.add_argument("--depth-map-name", help="optional depth map filename in ComfyUI/input/")
    ap.add_argument("--mask", type=Path, help="local regional mask path, optionally staged")
    ap.add_argument("--mask-name", help="regional mask filename in ComfyUI/input/")
    ap.add_argument("--mask2", type=Path, help="local second-region mask path, optionally staged")
    ap.add_argument("--mask2-name", help="second-region mask filename in ComfyUI/input/")
    ap.add_argument("--init-image", type=Path, help="local init image path, optionally staged")
    ap.add_argument("--init-name", help="init image filename in ComfyUI/input/")
    ap.add_argument("--stage-inputs", action="store_true", help="copy local image paths to --comfy-input-dir")
    ap.add_argument("--comfy-input-dir", type=Path, default=Path("~/ComfyUI/input"))
    ap.add_argument("--print-graph", action="store_true", help="print workflow JSON to stdout")
    ap.add_argument("--prompt", default=(
        "professional children's book watercolor hospital door panel, clean die-cut product art, "
        "blank signage, no words, coherent architectural details"))
    ap.add_argument("--negative-prompt", default=(
        "blurry, low quality, jpeg artifacts, text, letters, logo, watermark, signature, frame, "
        "border, extra openings, deformed holes, photo, 3d render, cluttered"))
    ap.add_argument("--width", type=int, default=512)
    ap.add_argument("--height", type=int, default=728)
    ap.add_argument("--batch-size", type=int, default=1)
    ap.add_argument("--control-strength", "--cond", dest="control_strength", type=float, default=1.0)
    ap.add_argument("--depth-strength", type=float, default=1.0)
    ap.add_argument("--cn-start-percent", type=float, default=0.0)
    ap.add_argument("--cn-end-percent", type=float, default=1.0)
    ap.add_argument("--ip-weight", type=float, default=0.8)
    ap.add_argument("--ip-weight2", type=float, default=0.8)
    ap.add_argument("--ip-weight-type", default="linear")
    ap.add_argument("--combine-embeds", default="average")
    ap.add_argument("--embeds-scaling", default="V only")
    ap.add_argument("--steps", type=int, default=30)
    ap.add_argument("--cfg", type=float, default=6.5)
    ap.add_argument("--seed", type=int, default=12345)
    ap.add_argument("--sampler", default="dpmpp_2m")
    ap.add_argument("--scheduler", default="karras")
    ap.add_argument("--denoise", type=float, default=1.0)
    ap.add_argument("--hires-scale", type=float)
    ap.add_argument("--hires-denoise", type=float, default=0.45)
    ap.add_argument("--ckpt", default="v1-5-pruned-emaonly-fp16.safetensors")
    ap.add_argument("--controlnet", default="control_v11p_sd15_lineart_fp16.safetensors")
    ap.add_argument("--depth-controlnet", default="control_v11f1p_sd15_depth_fp16.safetensors")
    ap.add_argument("--ipadapter", default="ip-adapter_sd15.safetensors")
    ap.add_argument("--clip-vision", default="CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors")
    ap.add_argument("--prefix", help="SaveImage filename_prefix; defaults to C2-<arm>")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args(argv)

    args.control_map_name = _image_name(args.control_map, args.control_map_name)
    args.depth_map_name = _image_name(args.depth_map, args.depth_map_name)
    args.mask_name = _image_name(args.mask, args.mask_name)
    args.mask2_name = _image_name(args.mask2, args.mask2_name)
    args.init_name = _image_name(args.init_image, args.init_name)
    args.ref_names = args.ref_names or ([p.name for p in args.refs] if args.refs else None)
    args.refs2_names = args.refs2_names or ([p.name for p in args.refs2] if args.refs2 else None)
    args.prefix = args.prefix or f"C2-{args.arm}"
    if not args.out and not args.print_graph:
        ap.error("one of --out or --print-graph is required")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.stage_inputs:
        stage_inputs(args)
    graph = build(args)
    validate_graph(graph)
    text = json.dumps(graph, indent=2)
    if args.print_graph:
        print(text)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
        print(f"wrote {args.out}  ({len(graph)} nodes)", file=sys.stderr if args.print_graph else sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
