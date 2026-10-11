from __future__ import annotations

import argparse
import copy
import hashlib
import json
import tempfile
from pathlib import Path

from chat_contract import build_generation_request
from generation_bridge import run_chat_generation


ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "app.example.json"
CHECKPOINT = "sd_xl_base_1.0.safetensors"
POSE_MODEL = "SDXL/controlnet-openpose-sdxl-1.0/diffusion_pytorch_model.safetensors"
POSE_STRENGTH = 0.9


def _load_config() -> dict:
    payload = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("app config root must be an object")
    return payload


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the FREE DWPose -> SDXL OpenPose ControlNet integration test."
    )
    parser.add_argument(
        "pose_image",
        type=Path,
        help="Local PNG/JPG/JPEG/WEBP containing a clearly visible person pose.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    pose_image = args.pose_image.expanduser().resolve()
    if not pose_image.is_file():
        raise FileNotFoundError(f"pose reference image not found: {pose_image}")
    if pose_image.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
        raise ValueError(f"unsupported pose reference image type: {pose_image.suffix}")

    source_sha = _sha256(pose_image)
    request = build_generation_request(
        json.dumps(
            {
                "positive": "adult anime woman standing, full body, plain white background",
                "negative": "bad anatomy, blurry",
                "checkpoint": CHECKPOINT,
                "lineart": {
                    "enabled": True,
                    "preset": "strong-anime-lineart-v1",
                    "strength": 1.35,
                },
                "pose_control": {
                    "enabled": True,
                    "source": str(pose_image),
                    "strength": POSE_STRENGTH,
                    "start_percent": 0.0,
                    "end_percent": 1.0,
                    "resolution": 1024,
                    "detect_hand": True,
                    "detect_body": True,
                    "detect_face": False,
                    "scale_stick_for_xinsr_cn": True,
                    "model": POSE_MODEL,
                },
            },
            ensure_ascii=False,
        ),
        "free-sdxl-v1",
        source="cli",
        seed_mode="FIXED",
        seed=975310,
    )

    if request.get("generation_domain") != "free":
        raise AssertionError(f"expected FREE route: {request.get('generation_domain')}")

    with tempfile.TemporaryDirectory(prefix="local-rag-free-pose-") as temp_dir:
        temp = Path(temp_dir)
        config = copy.deepcopy(_load_config())
        config["paths"]["cache"] = str(temp / "cache")
        config["paths"]["outputs"] = str(temp / "outputs")
        config["paths"]["database"] = str(temp / "local_rag_pose_test.db")

        result = run_chat_generation(ROOT, request, config)

        if result.generation_mode != "free_text2img_v2":
            raise AssertionError(f"unexpected generation mode: {result.generation_mode}")
        if not result.output_path.is_file():
            raise AssertionError(f"output image missing: {result.output_path}")
        if not result.manifest_path.is_file():
            raise AssertionError(f"manifest missing: {result.manifest_path}")
        if not result.database_path.is_file():
            raise AssertionError(f"test database missing: {result.database_path}")

        plan = json.loads(result.generation_plan_path.read_text(encoding="utf-8"))
        pose = plan.get("pose_control", {})
        if pose.get("enabled") is not True or pose.get("backend") != "dwpose":
            raise AssertionError(f"pose plan was not enabled as DWPose: {pose}")
        source = pose.get("source", {})
        if source.get("sha256") != source_sha:
            raise AssertionError("pose source SHA256 changed between local source and GenerationPlan")
        input_name = source.get("input_name")
        if not isinstance(input_name, str) or not input_name.startswith("LOCAL_RAG_POSE_"):
            raise AssertionError(f"unexpected uploaded pose input name: {input_name!r}")
        controlnet = pose.get("controlnet", {})
        if controlnet.get("model") != POSE_MODEL:
            raise AssertionError(f"pose ControlNet model mismatch: {controlnet.get('model')}")
        if abs(float(controlnet.get("strength", 0.0)) - POSE_STRENGTH) > 1e-9:
            raise AssertionError(f"pose ControlNet strength mismatch: {controlnet.get('strength')}")

        compiled_path = next((temp / "cache" / "compiled").glob("free-engine-*.json"), None)
        if compiled_path is None:
            raise AssertionError("compiled FREE workflow was not written")
        compiled = json.loads(compiled_path.read_text(encoding="utf-8"))

        if compiled.get("20", {}).get("class_type") != "LoadImage":
            raise AssertionError("compiled FREE workflow is missing pose LoadImage")
        if compiled.get("20", {}).get("inputs", {}).get("image") != input_name:
            raise AssertionError("pose LoadImage does not use uploaded pose reference")
        if compiled.get("21", {}).get("class_type") != "DWPreprocessor":
            raise AssertionError("compiled FREE workflow is missing DWPreprocessor")
        if compiled.get("21", {}).get("inputs", {}).get("image") != ["20", 0]:
            raise AssertionError("DWPreprocessor is not connected to pose LoadImage")
        if compiled.get("22", {}).get("class_type") != "ControlNetLoader":
            raise AssertionError("compiled FREE workflow is missing ControlNetLoader")
        compiled_model = compiled.get("22", {}).get("inputs", {}).get("control_net_name", "")
        if str(compiled_model).replace("\\", "/") != POSE_MODEL:
            raise AssertionError(f"compiled pose ControlNet model mismatch: {compiled_model}")
        if compiled.get("23", {}).get("class_type") != "ControlNetApplyAdvanced":
            raise AssertionError("compiled FREE workflow is missing ControlNetApplyAdvanced")
        apply_inputs = compiled["23"]["inputs"]
        if apply_inputs.get("image") != ["21", 0]:
            raise AssertionError("ControlNetApplyAdvanced is not connected to DWPose output")
        if abs(float(apply_inputs.get("strength", 0.0)) - POSE_STRENGTH) > 1e-9:
            raise AssertionError(f"compiled pose strength mismatch: {apply_inputs.get('strength')}")
        if compiled.get("7", {}).get("inputs", {}).get("positive") != ["23", 0]:
            raise AssertionError("KSampler positive is not connected to ControlNet positive conditioning")
        if compiled.get("7", {}).get("inputs", {}).get("negative") != ["23", 1]:
            raise AssertionError("KSampler negative is not connected to ControlNet negative conditioning")

        manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
        manifest_pose = manifest.get("generation", {}).get("pose_control", {})
        if manifest_pose.get("enabled") is not True or manifest_pose.get("backend") != "dwpose":
            raise AssertionError(f"manifest does not record enabled DWPose control: {manifest_pose}")
        if manifest_pose.get("source", {}).get("sha256") != source_sha:
            raise AssertionError("manifest pose source SHA256 mismatch")

        print(f"[FREE:POSE:RUNTIME:UPLOAD:OK] {input_name}")
        print(f"[FREE:POSE:RUNTIME:COMFYUI:OK] prompt_id={result.prompt_id}")
        print(f"[FREE:POSE:RUNTIME:OUTPUT:OK] {result.output_path.name}")
        print("[FREE:POSE:RUNTIME:DWPOSE:OK]")
        print(f"[FREE:POSE:RUNTIME:CONTROLNET:OK] strength={POSE_STRENGTH}")
        print("[FREE:POSE:RUNTIME:SAMPLER-WIRING:OK]")
        print("[FREE:POSE:RUNTIME:MANIFEST-DB:OK]")
        print("[FREE:POSE:RUNTIME:INTEGRATION:OK]")

    print("[FREE:POSE:RUNTIME:TEST-CLEANUP:OK]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
