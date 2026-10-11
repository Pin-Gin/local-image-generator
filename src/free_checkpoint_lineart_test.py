from __future__ import annotations

import copy
import json
import tempfile
from pathlib import Path

from free_compiler import compile_free_generation
from free_generation_plan import build_free_generation_engine_plan
from model_catalog import list_project_checkpoints, resolve_project_checkpoint


ROOT = Path(__file__).resolve().parent.parent
PROFILE_PATH = ROOT / "profiles" / "free_sdxl_v1.json"
RENDERING_PATH = ROOT / "shared" / "rendering" / "matte_dimensional_anime.json"
LINEART_PATH = ROOT / "shared" / "lineart" / "strong_anime_lineart.json"
BASE_CHECKPOINT = "sd_xl_base_1.0.safetensors"


def _load(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return payload


def main() -> int:
    checkpoints = list_project_checkpoints(ROOT)
    if BASE_CHECKPOINT not in checkpoints:
        raise AssertionError(f"base checkpoint missing from project catalog: {checkpoints}")
    selected = resolve_project_checkpoint(ROOT, BASE_CHECKPOINT)
    if selected != BASE_CHECKPOINT:
        raise AssertionError(f"checkpoint resolution changed the selected name: {selected}")

    profile = _load(PROFILE_PATH)
    rendering = _load(RENDERING_PATH)
    lineart_profile = _load(LINEART_PATH)

    workflow = dict(profile["workflow"])
    generation = rendering["generation"]
    workflow["checkpoint"] = selected
    workflow["steps"] = generation["steps"]
    workflow["cfg"] = generation["cfg"]
    workflow["sampler_name"] = generation["sampler_name"]
    workflow["scheduler"] = generation["scheduler"]
    workflow["denoise"] = 1.0

    plan = build_free_generation_engine_plan(
        content_positive="adult anime woman standing, full body",
        content_negative="bad anatomy, blurry",
        workflow=workflow,
        shared_rendering=rendering,
        lineart_profile=lineart_profile,
        lineart_enabled=True,
        lineart_strength=1.35,
    )

    lineart = plan["conditioning"]["lineart"]
    if lineart.get("enabled") is not True:
        raise AssertionError("lineart conditioning was not enabled")
    if lineart.get("profile_id") != "strong-anime-lineart-v1":
        raise AssertionError(f"unexpected lineart profile: {lineart.get('profile_id')}")
    if lineart.get("strength") != 1.35:
        raise AssertionError(f"unexpected lineart strength: {lineart.get('strength')}")
    if plan["checkpoint"]["name"] != BASE_CHECKPOINT:
        raise AssertionError(f"plan checkpoint mismatch: {plan['checkpoint']['name']}")

    with tempfile.TemporaryDirectory(prefix="local-rag-free-lineart-") as temp_dir:
        compiled = compile_free_generation(
            ROOT,
            plan,
            Path(temp_dir),
            seed=777,
        ).compiled_workflow

        if compiled["1"]["inputs"]["ckpt_name"] != BASE_CHECKPOINT:
            raise AssertionError(f"compiled checkpoint mismatch: {compiled['1']['inputs']['ckpt_name']}")
        if compiled.get("10", {}).get("class_type") != "CLIPTextEncode":
            raise AssertionError("lineart CLIP node was not created")
        lineart_text = compiled["10"]["inputs"].get("text", "")
        if "strong clean anime lineart" not in lineart_text or ":1.35)" not in lineart_text:
            raise AssertionError(f"lineart weighting was not compiled: {lineart_text!r}")
        if compiled.get("11", {}).get("class_type") != "ConditioningCombine":
            raise AssertionError("second ConditioningCombine for lineart was not created")
        if compiled["7"]["inputs"]["positive"] != ["11", 0]:
            raise AssertionError("KSampler positive is not connected to content+rendering+lineart")
        if "weak lineart" not in compiled["6"]["inputs"].get("text", ""):
            raise AssertionError("lineart negative conditioning was not merged")

        lineart_lora = plan["loras"].get("lineart")
        if not isinstance(lineart_lora, dict) or lineart_lora.get("enabled") is not False:
            raise AssertionError(f"lineart LoRA slot is not present/disabled: {lineart_lora}")

        lora_plan = copy.deepcopy(plan)
        lora_plan["loras"]["rendering"]["enabled"] = True
        lora_plan["loras"]["lineart"]["enabled"] = True
        lora_compiled = compile_free_generation(
            ROOT,
            lora_plan,
            Path(temp_dir) / "lora-chain",
            seed=778,
        ).compiled_workflow
        if lora_compiled.get("90", {}).get("class_type") != "LoraLoader":
            raise AssertionError("rendering LoRA loader was not compiled")
        if lora_compiled.get("91", {}).get("class_type") != "LoraLoader":
            raise AssertionError("lineart LoRA loader slot was not compiled")
        if lora_compiled["91"]["inputs"]["model"] != ["90", 0]:
            raise AssertionError("lineart LoRA is not chained after rendering LoRA")
        if lora_compiled["7"]["inputs"]["model"] != ["91", 0]:
            raise AssertionError("KSampler model is not connected to final LoRA chain")
        for node_id in ("3", "4", "6", "10"):
            if lora_compiled[node_id]["inputs"]["clip"] != ["91", 1]:
                raise AssertionError(f"node {node_id} is not connected to final LoRA CLIP")

    print(f"[FREE:CHECKPOINT:CATALOG:OK] count={len(checkpoints)}")
    print(f"[FREE:CHECKPOINT:SELECT:OK] {selected}")
    print("[FREE:LINEART:CONDITIONING:OK] strength=1.35")
    print("[FREE:LINEART:COMBINE:OK]")
    print("[FREE:LINEART:LORA-SLOT:OK]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
