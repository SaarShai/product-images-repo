import json
import os
import subprocess
import sys
from pathlib import Path

from PIL import Image


REPO_ROOT = Path(__file__).resolve().parents[1]
FALGEN = REPO_ROOT / "scripts" / "falgen.py"


def make_png(tmp_path, name, color=(12, 34, 56)):
    path = tmp_path / name
    Image.new("RGB", (8, 6), color).save(path)
    return path


def run_dry(args):
    env = os.environ.copy()
    env.pop("FAL_KEY", None)
    result = subprocess.run(
        [sys.executable, str(FALGEN), *args],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_fluxgeneral_dry_run_builds_control_lora_reference_payload(tmp_path):
    control = make_png(tmp_path, "control.png")
    ref = make_png(tmp_path, "ref.png", (100, 20, 30))
    ip_adapter = make_png(tmp_path, "ip.png", (20, 100, 30))

    payload = run_dry(
        [
            "--mode",
            "fluxgeneral",
            "--out",
            str(tmp_path / "out.png"),
            "--prompt",
            "storybook panel",
            "--image-size",
            "16x24",
            "--loras",
            "style.safetensors,0.75",
            "--control-image",
            str(control),
            "--control-scale",
            "0.4",
            "--control-mode",
            "canny",
            "--ref-image",
            str(ref),
            "--ref-strength",
            "0.8",
            "--ip-adapter",
            str(ip_adapter),
            "--dry-run",
        ]
    )

    args = payload["arguments"]
    assert payload["endpoint"] == "fal-ai/flux-general"
    assert payload["dry_run"] is True
    assert args["image_size"] == {"width": 16, "height": 24}
    assert args["loras"] == [{"path": "style.safetensors", "scale": 0.75}]
    # live-schema fix (422 probe): control via control_loras (ControlLoraWeight),
    # preprocess "None" because our control maps are pre-rendered edge images
    (cl,) = args["control_loras"]
    assert cl["control_image_url"] == str(control)
    assert cl["scale"] == 0.4
    assert cl["preprocess"] == "None"
    assert cl["path"].endswith(".safetensors")
    assert args["reference_image_url"] == str(ref)
    assert args["reference_strength"] == 0.8
    assert args["ip_adapters"] == [{"image_url": str(ip_adapter)}]


def test_kontextlora_dry_run_builds_match_input_lora_payload(tmp_path):
    image = make_png(tmp_path, "input.png")
    loras = json.dumps([{"path": "kontext-style.safetensors", "scale": 1.1}])

    payload = run_dry(
        [
            "--mode",
            "kontextlora",
            "--image",
            str(image),
            "--out",
            str(tmp_path / "out.png"),
            "--prompt",
            "restyle without moving geometry",
            "--loras",
            loras,
            "--dry-run",
        ]
    )

    args = payload["arguments"]
    assert payload["endpoint"] == "fal-ai/flux-kontext-lora"
    assert args["image_url"] == str(image)
    assert args["resolution_mode"] == "match_input"
    assert args["loras"] == [{"path": "kontext-style.safetensors", "scale": 1.1}]


def test_aurasr_dry_run_builds_overlapping_tiles_payload(tmp_path):
    image = make_png(tmp_path, "input.png")

    payload = run_dry(
        [
            "--mode",
            "aurasr",
            "--image",
            str(image),
            "--out",
            str(tmp_path / "out.png"),
            "--dry-run",
        ]
    )

    args = payload["arguments"]
    assert payload["endpoint"] == "fal-ai/aura-sr"
    assert args["image_url"] == str(image)
    assert args["overlapping_tiles"] is True
    assert args["checkpoint"] == "v2"


def test_falesrgan_dry_run_builds_scale_tile_payload(tmp_path):
    image = make_png(tmp_path, "input.png")

    payload = run_dry(
        [
            "--mode",
            "falesrgan",
            "--image",
            str(image),
            "--out",
            str(tmp_path / "out.png"),
            "--dry-run",
        ]
    )

    args = payload["arguments"]
    assert payload["endpoint"] == "fal-ai/esrgan"
    assert args["image_url"] == str(image)
    assert args["scale"] == 4
    assert args["tile"] == 0


def test_nbpro_dry_run_builds_image_urls_aspect_resolution_payload(tmp_path):
    image = make_png(tmp_path, "primary.png")
    ref = make_png(tmp_path, "ref.png", (100, 20, 30))

    payload = run_dry(
        [
            "--mode",
            "nbpro",
            "--image",
            str(image),
            "--refs",
            str(ref),
            "--out",
            str(tmp_path / "out.png"),
            "--prompt",
            "storybook panel",
            "--dry-run",
        ]
    )

    args = payload["arguments"]
    assert payload["endpoint"] == "fal-ai/nano-banana-pro/edit"
    assert args["image_urls"] == [str(image), str(ref)]
    assert args["aspect_ratio"] == "2:3"
    assert args["resolution"] == "2K"
    assert args["output_format"] == "png"
    assert args["num_images"] == 1


def test_fluxgeneral_dry_run_records_provenance_loras_and_control_image(tmp_path):
    # t1 lesson: MRWC LoRA path was unrecoverable — the dry-run payload (the
    # request the artifact writer records) must carry full provenance: mode,
    # cli argv, and the resolved arguments incl. lora paths/scales + the
    # control image path as given.
    control = make_png(tmp_path, "control.png")
    out = tmp_path / "out.png"

    argv = [
        "--mode",
        "fluxgeneral",
        "--out",
        str(out),
        "--prompt",
        "storybook panel",
        "--image-size",
        "16x24",
        "--loras",
        "style.safetensors,0.75",
        "--control-image",
        str(control),
        "--control-scale",
        "0.4",
        "--dry-run",
    ]
    payload = run_dry(argv)

    assert payload["mode"] == "fluxgeneral"
    assert payload["cli_argv"][0].endswith("falgen.py")
    for a in argv:
        assert a in payload["cli_argv"]

    args = payload["arguments"]
    assert args["loras"] == [{"path": "style.safetensors", "scale": 0.75}]
    (cl,) = args["control_loras"]
    assert cl["control_image_url"] == str(control)


def test_gptimg2_dry_run_builds_image_urls_image_size_payload(tmp_path):
    image = make_png(tmp_path, "primary.png")
    ref = make_png(tmp_path, "ref.png", (100, 20, 30))

    payload = run_dry(
        [
            "--mode",
            "gptimg2",
            "--image",
            str(image),
            "--refs",
            str(ref),
            "--out",
            str(tmp_path / "out.png"),
            "--prompt",
            "storybook panel",
            "--dry-run",
        ]
    )

    args = payload["arguments"]
    assert payload["endpoint"] == "openai/gpt-image-2/edit"
    assert args["image_urls"] == [str(image), str(ref)]
    assert args["image_size"] == {"width": 832, "height": 1184}
    assert args["quality"] == "high"
    assert args["output_format"] == "png"


def test_nbpro_tall_panel_rejects_without_force_nano(tmp_path):
    """Tall image (aspect < 0.75) must fail unless --force-nano is passed."""
    # Create a tall image: 8x24 = 0.333 aspect ratio
    image = tmp_path / "tall.png"
    Image.new("RGB", (8, 24), (12, 34, 56)).save(image)

    env = os.environ.copy()
    env.pop("FAL_KEY", None)
    result = subprocess.run(
        [
            sys.executable,
            str(FALGEN),
            "--mode",
            "nbpro",
            "--image",
            str(image),
            "--out",
            str(tmp_path / "out.png"),
            "--prompt",
            "storybook panel",
            "--dry-run",
        ],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
    )

    assert result.returncode != 0
    assert "nano recomposes tall panels" in result.stderr


def test_nbpro_tall_panel_succeeds_with_force_nano(tmp_path):
    """Tall image with --force-nano succeeds but prints WARNING."""
    # Create a tall image: 8x24 = 0.333 aspect ratio
    image = tmp_path / "tall.png"
    Image.new("RGB", (8, 24), (12, 34, 56)).save(image)

    payload = run_dry(
        [
            "--mode",
            "nbpro",
            "--image",
            str(image),
            "--out",
            str(tmp_path / "out.png"),
            "--prompt",
            "storybook panel",
            "--force-nano",
            "--dry-run",
        ]
    )

    args = payload["arguments"]
    assert payload["endpoint"] == "fal-ai/nano-banana-pro/edit"
    assert args["image_urls"] == [str(image)]


def test_nbpro_square_image_unaffected(tmp_path):
    """Square image (aspect 1.0) passes without issue."""
    image = make_png(tmp_path, "square.png")  # 8x6, aspect > 0.75

    payload = run_dry(
        [
            "--mode",
            "nbpro",
            "--image",
            str(image),
            "--out",
            str(tmp_path / "out.png"),
            "--prompt",
            "storybook panel",
            "--dry-run",
        ]
    )

    args = payload["arguments"]
    assert payload["endpoint"] == "fal-ai/nano-banana-pro/edit"
    assert args["image_urls"] == [str(image)]
