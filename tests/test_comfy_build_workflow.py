import importlib.util
import json
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
BUILDER_PATH = REPO_ROOT / "scripts" / "comfy_build_workflow.py"


spec = importlib.util.spec_from_file_location("comfy_build_workflow", BUILDER_PATH)
comfy_build_workflow = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(comfy_build_workflow)


def build_to_tmp(tmp_path, arm, extra_args):
    out = tmp_path / f"{arm}.json"
    args = comfy_build_workflow.parse_args(["--arm", arm, "--out", str(out), *extra_args])
    graph = comfy_build_workflow.build(args)
    comfy_build_workflow.validate_graph(graph)
    out.write_text(json.dumps(graph, indent=2) + "\n", encoding="utf-8")
    return json.loads(out.read_text(encoding="utf-8"))


def assert_node_refs_exist(graph):
    for node_id, input_name, ref_id, slot in comfy_build_workflow.graph_references(graph):
        assert ref_id in graph, f"{node_id}.{input_name} -> {ref_id}[{slot}]"


def class_types(graph):
    return [node["class_type"] for node in graph.values()]


def ksampler_node(graph):
    nodes = [node for node in graph.values() if node["class_type"] == "KSampler"]
    assert len(nodes) == 1
    return nodes[0]


def arm_required_args(arm):
    if arm == "geometry":
        return ["--control-map-name", "door-lineart.png"]
    if arm == "style":
        return ["--ref-names", "style-a.png"]
    if arm == "combined":
        return ["--control-map-name", "door-lineart.png", "--ref-names", "style-a.png"]
    if arm == "regional":
        return [
            "--control-map-name",
            "door-lineart.png",
            "--ref-names",
            "style-a.png",
            "--mask-name",
            "door-portal-mask.png",
        ]
    if arm == "dualregion":
        return [
            "--control-map-name",
            "door-lineart.png",
            "--ref-names",
            "style-a.png",
            "--mask-name",
            "door-portal-mask.png",
            "--refs2-names",
            "style-b.png",
            "--mask2-name",
            "door-background-mask.png",
        ]
    raise AssertionError(f"unexpected arm: {arm}")


def test_geometry_arm_builds_lineart_controlnet_only(tmp_path):
    graph = build_to_tmp(
        tmp_path,
        "geometry",
        ["--control-map-name", "door-lineart.png", "--control-strength", "0.8"],
    )

    assert_node_refs_exist(graph)
    classes = class_types(graph)
    assert "ControlNetApplyAdvanced" in classes
    assert "IPAdapterAdvanced" not in classes


def test_style_arm_builds_ipadapter_only(tmp_path):
    graph = build_to_tmp(
        tmp_path,
        "style",
        ["--ref-names", "style-a.png", "style-b.png", "style-c.png", "--ip-weight", "0.5"],
    )

    assert_node_refs_exist(graph)
    classes = class_types(graph)
    assert "IPAdapterAdvanced" in classes
    assert "ControlNetApplyAdvanced" not in classes


def test_combined_arm_chains_lineart_and_depth_controlnets_with_ipadapter(tmp_path):
    graph = build_to_tmp(
        tmp_path,
        "combined",
        [
            "--control-map-name",
            "door-lineart.png",
            "--depth-map-name",
            "door-depth.png",
            "--ref-names",
            "style-a.png",
        ],
    )

    assert_node_refs_exist(graph)
    classes = class_types(graph)
    assert classes.count("ControlNetApplyAdvanced") == 2
    assert "IPAdapterAdvanced" in classes


def test_regional_arm_wires_ipadapter_attention_mask(tmp_path):
    graph = build_to_tmp(
        tmp_path,
        "regional",
        [
            "--control-map-name",
            "door-lineart.png",
            "--ref-names",
            "style-a.png",
            "style-b.png",
            "--mask-name",
            "door-portal-mask.png",
        ],
    )

    assert_node_refs_exist(graph)
    ip_nodes = [node for node in graph.values() if node["class_type"] == "IPAdapterAdvanced"]
    assert len(ip_nodes) == 1
    assert "attn_mask" in ip_nodes[0]["inputs"]
    assert ip_nodes[0]["inputs"]["attn_mask"][1] == 1


@pytest.mark.parametrize("arm", comfy_build_workflow.ARMS)
def test_init_image_replaces_empty_latent_for_all_arms(tmp_path, arm):
    graph = build_to_tmp(
        tmp_path,
        arm,
        [*arm_required_args(arm), "--init-name", "init.png", "--denoise", "0.42"],
    )

    assert_node_refs_exist(graph)
    classes = class_types(graph)
    assert "EmptyLatentImage" not in classes
    vae_nodes = [(node_id, node) for node_id, node in graph.items() if node["class_type"] == "VAEEncode"]
    assert len(vae_nodes) == 1
    vae_node_id, vae_node = vae_nodes[0]
    init_image_id = vae_node["inputs"]["pixels"][0]
    assert graph[init_image_id]["class_type"] == "LoadImage"
    assert graph[init_image_id]["inputs"]["image"] == "init.png"
    assert vae_node["inputs"]["vae"][1] == 2
    sample = ksampler_node(graph)
    assert sample["inputs"]["latent_image"] == [vae_node_id, 0]
    assert sample["inputs"]["denoise"] == 0.42


def test_controlnet_start_and_end_percent_propagate_to_lineart_and_depth(tmp_path):
    graph = build_to_tmp(
        tmp_path,
        "combined",
        [
            "--control-map-name",
            "door-lineart.png",
            "--depth-map-name",
            "door-depth.png",
            "--ref-names",
            "style-a.png",
            "--cn-start-percent",
            "0.25",
            "--cn-end-percent",
            "0.8",
        ],
    )

    assert_node_refs_exist(graph)
    controlnet_nodes = [node for node in graph.values() if node["class_type"] == "ControlNetApplyAdvanced"]
    assert len(controlnet_nodes) == 2
    for node in controlnet_nodes:
        assert node["inputs"]["start_percent"] == 0.25
        assert node["inputs"]["end_percent"] == 0.8


def test_hires_mode_adds_upscale_and_second_ksampler(tmp_path):
    graph = build_to_tmp(
        tmp_path,
        "combined",
        [
            "--control-map-name",
            "door-lineart.png",
            "--ref-names",
            "style-a.png",
            "--denoise",
            "0.82",
            "--seed",
            "100",
            "--hires-scale",
            "1.6",
            "--hires-denoise",
            "0.38",
        ],
    )

    assert_node_refs_exist(graph)
    upscales = [node for node in graph.values() if node["class_type"] == "LatentUpscaleBy"]
    assert len(upscales) == 1
    assert upscales[0]["inputs"]["scale_by"] == 1.6
    samplers = [node for node in graph.values() if node["class_type"] == "KSampler"]
    assert len(samplers) == 2
    assert samplers[0]["inputs"]["denoise"] == 0.82
    assert samplers[1]["inputs"]["denoise"] == 0.38
    assert samplers[0]["inputs"]["seed"] == 100
    assert samplers[1]["inputs"]["seed"] == 101


def test_dualregion_chains_two_ipadapters_with_shared_loaders_and_distinct_masks(tmp_path):
    graph = build_to_tmp(
        tmp_path,
        "dualregion",
        [
            "--control-map-name",
            "door-lineart.png",
            "--ref-names",
            "portal-style.png",
            "--mask-name",
            "door-portal-mask.png",
            "--refs2-names",
            "background-style.png",
            "--mask2-name",
            "background-mask.png",
            "--ip-weight",
            "0.4",
            "--ip-weight2",
            "0.7",
        ],
    )

    assert_node_refs_exist(graph)
    ip_nodes = [(node_id, node) for node_id, node in graph.items() if node["class_type"] == "IPAdapterAdvanced"]
    assert len(ip_nodes) == 2
    first_id, first = ip_nodes[0]
    _, second = ip_nodes[1]
    assert second["inputs"]["model"] == [first_id, 0]
    assert first["inputs"]["weight"] == 0.4
    assert second["inputs"]["weight"] == 0.7
    assert first["inputs"]["ipadapter"] == second["inputs"]["ipadapter"]
    assert first["inputs"]["clip_vision"] == second["inputs"]["clip_vision"]
    assert class_types(graph).count("IPAdapterModelLoader") == 1
    assert class_types(graph).count("CLIPVisionLoader") == 1

    first_mask_ref = first["inputs"]["attn_mask"]
    second_mask_ref = second["inputs"]["attn_mask"]
    assert first_mask_ref != second_mask_ref
    assert graph[first_mask_ref[0]]["class_type"] == "LoadImage"
    assert graph[second_mask_ref[0]]["class_type"] == "LoadImage"
    assert graph[first_mask_ref[0]]["inputs"]["image"] == "door-portal-mask.png"
    assert graph[second_mask_ref[0]]["inputs"]["image"] == "background-mask.png"
