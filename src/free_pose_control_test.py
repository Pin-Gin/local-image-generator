from __future__ import annotations

import json
import tempfile
from pathlib import Path

from free_compiler import compile_free_generation
from free_generation_plan import build_free_generation_engine_plan


ROOT = Path(__file__).resolve().parent.parent
PROFILE_PATH = ROOT / "profiles" / "free_sdxl_v1.json"
RENDERING_PATH = ROOT / "shared" / "rendering" / "matte_dimensional_anime.json"
LINEART_PATH = ROOT / "shared" / "lineart" / "strong_anime_lineart.json"
CONTROLNET_MODEL = "SDXL/controlnet-openpose-sdxl-1.0/diffusion_pytorch_model.safetensors"


def _load(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return payload


def main() -> int:
    profile = _load(PROFILE_PATH)
    rendering = _load(RENDERING_PATH)
    lineart_profile = _load(LINEART_PATH)

    workflow = dict(profile["workflow"])
    generation = rendering["generation"]
    workflow["checkpoint"] = generation["checkpoint"]
    workflow["steps"] = generation["steps"]
    workflow["cfg"] = generation["cfg"]
    workflow["sampler_name"] = generation["sampler_name"]
    workflow["scheduler"] = generation["scheduler"]
    workflow["denoise"] = 1.0

    pose_control = {
        "enabled": True,
        "backend": "dwpose",
        "source": {
            "local_path": "C:/test/pose-reference.png",
            "input_name": "LOCAL_RAG_POSE_TEST.png",
            "sha256": "0" * 64,
        },
        "preprocessor": {
            "detect_hand": True,
            "detect_body": True,
            "detect_face": False,
            "resolution": 1024,
            "bbox_detector": "yolox_l.onnx",
            "pose_estimator": "dw-ll_ucoco_384_bs5.torchscript.pt",
            "scale_stick_for_xinsr_cn": True,
        },
        "controlnet": {
            "model": CONTROLNET_MODEL,
            "strength": 0.9,
            "start_percent": 0.0,
            "end_percent": 1.0,
        },
    }

    plan = build_free_generation_engine_plan(
        content_positive="adult anime woman standing, full body",
        content_negative="bad anatomy, blurry",
        workflow=workflow,
        shared_rendering=rendering,
        lineart_profile=lineart_profile,
        lineart_enabled=True,
        lineart_strength=1.35,
        pose_control=pose_control,
    )

    if plan["pose_control"]["enabled"] is not True:
        raise AssertionError("pose control was not enabled")
    if plan["pose_control"]["backend"] != "dwpose":
        raise AssertionError("pose backend is not dwpose")

    with tempfile.TemporaryDirectory(prefix="local-rag-free-pose-") as temp_dir:
        compiled = compile_free_generation(
            ROOT,
            plan,
            Path(temp_dir),
            seed=779,
        ).compiled_workflow

        if compiled.get("20", {}).get("class_type") != "LoadImage":
            raise AssertionError("pose LoadImage node was not created")
        if compiled["20"]["inputs"].get("image") != "LOCAL_RAG_POSE_TEST.png":
            raise AssertionError("pose input filename was not preserved")

        if compiled.get("21", {}).get("class_type") != "DWPreprocessor":
            raise AssertionError("DWPose preprocessor node was not created")
        dw_inputs = compiled["21"]["inputs"]
        if dw_inputs.get("image") != ["20", 0]:
            raise AssertionError("DWPose is not connected to LoadImage")
        if dw_inputs.get("detect_hand") != "enable" or dw_inputs.get("detect_body") != "enable":
            raise AssertionError("DWPose body/hand detection is not enabled")
        if dw_inputs.get("detect_face") != "disable":
            raise AssertionError("DWPose face detection default changed")
        if dw_inputs.get("scale_stick_for_xinsr_cn") != "enable":
            raise AssertionError("Xinsir stick scaling is not enabled")

        if compiled.get("22", {}).get("class_type") != "ControlNetLoader":
            raise AssertionError("ControlNetLoader node was not created")
        expected_model = CONTROLNET_MODEL.replace("/", "\\")
        if compiled["22"]["inputs"].get("control_net_name") != expected_model:
            raise AssertionError("ControlNet model name was not compiled correctly")

        if compiled.get("23", {}).get("class_type") != "ControlNetApplyAdvanced":
            raise AssertionError("ControlNetApplyAdvanced node was not created")
        control_inputs = compiled["23"]["inputs"]
        if control_inputs.get("positive") != ["11", 0]:
            raise AssertionError("ControlNet positive input is not connected after lineart combine")
        if control_inputs.get("negative") != ["6", 0]:
            raise AssertionError("ControlNet negative input is not connected")
        if control_inputs.get("control_net") != ["22", 0]:
            raise AssertionError("ControlNetApplyAdvanced is not connected to ControlNetLoader")
        if control_inputs.get("image") != ["21", 0]:
            raise AssertionError("ControlNetApplyAdvanced is not connected to DWPose output")
        if control_inputs.get("strength") != 0.9:
            raise AssertionError("ControlNet strength changed")

        sampler = compiled["7"]["inputs"]
        if sampler.get("positive") != ["23", 0] or sampler.get("negative") != ["23", 1]:
            raise AssertionError("KSampler is not connected to ControlNet conditioned outputs")

    print("[FREE:POSE:PLAN:OK] backend=dwpose")
    print("[FREE:POSE:LOAD-IMAGE:OK]")
    print("[FREE:POSE:DWPOSE:OK]")
    print("[FREE:POSE:CONTROLNET:OK] strength=0.9")
    print("[FREE:POSE:SAMPLER-WIRING:OK]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
