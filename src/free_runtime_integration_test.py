from __future__ import annotations

import copy
import json
import tempfile
from pathlib import Path

from chat_contract import build_generation_request
from generation_bridge import run_chat_generation


ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "app.example.json"


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
            },
            ensure_ascii=False,
        ),
        "free-sdxl-v1",
        source="cli",
        seed_mode="FIXED",
        seed=123456,
    )

    if request.get("generation_domain") != "free":
        raise AssertionError(f"expected FREE route: {request.get('generation_domain')}")

    with tempfile.TemporaryDirectory(prefix="local-rag-free-runtime-") as temp_dir:
        temp = Path(temp_dir)
        config = copy.deepcopy(_load_config())
        config["paths"]["cache"] = str(temp / "cache")
        config["paths"]["outputs"] = str(temp / "outputs")
        config["paths"]["database"] = str(temp / "local_rag_test.db")

        result = run_chat_generation(ROOT, request, config)

        if result.generation_mode != "free_text2img_v2":
            raise AssertionError(f"unexpected generation mode: {result.generation_mode}")
        if result.learned_asset_ids:
            raise AssertionError(f"FREE runtime unexpectedly used learned AI assets: {result.learned_asset_ids}")
        if not result.output_path.is_file():
            raise AssertionError(f"output image missing: {result.output_path}")
        if not result.manifest_path.is_file():
            raise AssertionError(f"manifest missing: {result.manifest_path}")
        if not result.generation_plan_path.is_file():
            raise AssertionError(f"generation plan missing: {result.generation_plan_path}")
        if not result.database_path.is_file():
            raise AssertionError(f"test database missing: {result.database_path}")

        plan = json.loads(result.generation_plan_path.read_text(encoding="utf-8"))
        if plan.get("engine_id") != "free-deterministic-v1":
            raise AssertionError(f"unexpected engine id: {plan.get('engine_id')}")
        if plan.get("ai_interpretation", {}).get("enabled") is not False:
            raise AssertionError("FREE runtime unexpectedly enables AI interpretation")

        compiled_path = next((temp / "cache" / "compiled").glob("free-engine-*.json"), None)
        if compiled_path is None:
            raise AssertionError("compiled FREE workflow was not written")
        compiled = json.loads(compiled_path.read_text(encoding="utf-8"))
        if compiled.get("5", {}).get("class_type") != "ConditioningCombine":
            raise AssertionError("compiled FREE workflow is missing ConditioningCombine")
        if compiled.get("7", {}).get("inputs", {}).get("positive") != ["5", 0]:
            raise AssertionError("KSampler positive is not connected to combined conditioning")

        manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
        generation = manifest.get("generation", {})
        if generation.get("engine_id") != "free-deterministic-v1":
            raise AssertionError("manifest does not record FREE deterministic engine")
        if generation.get("seed") != 123456:
            raise AssertionError(f"manifest seed mismatch: {generation.get('seed')}")

        print(f"[FREE:RUNTIME:COMFYUI:OK] prompt_id={result.prompt_id}")
        print(f"[FREE:RUNTIME:OUTPUT:OK] {result.output_path.name}")
        print("[FREE:RUNTIME:CONDITIONING-COMBINE:OK]")
        print("[FREE:RUNTIME:MANIFEST-DB:OK]")
        print("[FREE:RUNTIME:INTEGRATION:OK]")

    print("[FREE:RUNTIME:TEST-CLEANUP:OK]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
