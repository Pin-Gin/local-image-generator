from __future__ import annotations

import copy
import json
import tempfile
from pathlib import Path

from chat_contract import build_generation_request
from generation_bridge import run_chat_generation


ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "app.example.json"
CHECKPOINT = "sd_xl_base_1.0.safetensors"
LINEART_PRESET = "strong-anime-lineart-v1"
LINEART_STRENGTH = 1.35


def _load_config() -> dict:
    payload = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("app config root must be an object")
    return payload


def main() -> int:
    request = build_generation_request(
        json.dumps(
            {
                "positive": "adult anime woman standing, full body, plain white background",
                "negative": "bad anatomy, blurry",
                "checkpoint": CHECKPOINT,
                "lineart": {
                    "enabled": True,
                    "preset": LINEART_PRESET,
                    "strength": LINEART_STRENGTH,
                },
            },
            ensure_ascii=False,
        ),
        "free-sdxl-v1",
        source="cli",
        seed_mode="FIXED",
        seed=246810,
    )

    if request.get("generation_domain") != "free":
        raise AssertionError(f"expected FREE route: {request.get('generation_domain')}")

    with tempfile.TemporaryDirectory(prefix="local-rag-free-lineart-") as temp_dir:
        temp = Path(temp_dir)
        config = copy.deepcopy(_load_config())
        config["paths"]["cache"] = str(temp / "cache")
        config["paths"]["outputs"] = str(temp / "outputs")
        config["paths"]["database"] = str(temp / "local_rag_lineart_test.db")

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
        if plan.get("checkpoint", {}).get("name") != CHECKPOINT:
            raise AssertionError(f"checkpoint selection mismatch: {plan.get('checkpoint')}")
        lineart = plan.get("conditioning", {}).get("lineart", {})
        if lineart.get("enabled") is not True:
            raise AssertionError(f"lineart was not enabled in plan: {lineart}")
        if abs(float(lineart.get("strength", 0.0)) - LINEART_STRENGTH) > 1e-9:
            raise AssertionError(f"lineart strength mismatch: {lineart.get('strength')}")

        compiled_path = next((temp / "cache" / "compiled").glob("free-engine-*.json"), None)
        if compiled_path is None:
            raise AssertionError("compiled FREE workflow was not written")
        compiled = json.loads(compiled_path.read_text(encoding="utf-8"))

        if compiled.get("1", {}).get("inputs", {}).get("ckpt_name") != CHECKPOINT:
            raise AssertionError("compiled checkpoint does not match requested project checkpoint")
        if compiled.get("10", {}).get("class_type") != "CLIPTextEncode":
            raise AssertionError("compiled FREE workflow is missing Lineart CLIPTextEncode")
        if compiled.get("11", {}).get("class_type") != "ConditioningCombine":
            raise AssertionError("compiled FREE workflow is missing Lineart ConditioningCombine")
        if compiled.get("11", {}).get("inputs", {}).get("conditioning_1") != ["5", 0]:
            raise AssertionError("lineart combine does not receive content+rendering conditioning")
        if compiled.get("11", {}).get("inputs", {}).get("conditioning_2") != ["10", 0]:
            raise AssertionError("lineart combine does not receive lineart conditioning")
        if compiled.get("7", {}).get("inputs", {}).get("positive") != ["11", 0]:
            raise AssertionError("KSampler positive is not connected to lineart-combined conditioning")

        lineart_text = compiled.get("10", {}).get("inputs", {}).get("text", "")
        if not isinstance(lineart_text, str) or ":1.35)" not in lineart_text:
            raise AssertionError(f"weighted lineart prompt missing expected strength: {lineart_text!r}")

        manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
        generation = manifest.get("generation", {})
        if generation.get("checkpoint") != CHECKPOINT:
            raise AssertionError(f"manifest checkpoint mismatch: {generation.get('checkpoint')}")
        manifest_lineart = generation.get("lineart", {})
        if manifest_lineart.get("enabled") is not True:
            raise AssertionError(f"manifest does not record enabled lineart: {manifest_lineart}")
        if abs(float(manifest_lineart.get("strength", 0.0)) - LINEART_STRENGTH) > 1e-9:
            raise AssertionError(f"manifest lineart strength mismatch: {manifest_lineart.get('strength')}")

        print(f"[FREE:LINEART:RUNTIME:COMFYUI:OK] prompt_id={result.prompt_id}")
        print(f"[FREE:LINEART:RUNTIME:OUTPUT:OK] {result.output_path.name}")
        print(f"[FREE:LINEART:RUNTIME:CHECKPOINT:OK] {CHECKPOINT}")
        print(f"[FREE:LINEART:RUNTIME:CONDITIONING:OK] strength={LINEART_STRENGTH}")
        print("[FREE:LINEART:RUNTIME:MANIFEST-DB:OK]")
        print("[FREE:LINEART:RUNTIME:INTEGRATION:OK]")

    print("[FREE:LINEART:RUNTIME:TEST-CLEANUP:OK]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
