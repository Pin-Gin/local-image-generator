from __future__ import annotations

import copy
import json
import tempfile
from pathlib import Path

from free_compiler import compile_free_generation
from free_generation_plan import build_free_generation_engine_plan


ROOT = Path(__file__).resolve().parent.parent
PROFILE_PATH = ROOT / "profiles" / "free_sdxl_v1.json"
RENDERING_PATH = ROOT / "shared" / "rendering" / "matte_dimensional_anime.json"


def _load(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return payload


def _engine_plan(rendering: dict, *, lora_enabled: bool) -> dict:
    profile = _load(PROFILE_PATH)
    workflow = dict(profile["workflow"])
    generation = rendering["generation"]
    workflow["checkpoint"] = generation["checkpoint"]
    workflow["steps"] = generation["steps"]
    workflow["cfg"] = generation["cfg"]
    workflow["sampler_name"] = generation["sampler_name"]
    workflow["scheduler"] = generation["scheduler"]

    rendering_copy = copy.deepcopy(rendering)
    rendering_copy["lora"]["enabled"] = lora_enabled

    return build_free_generation_engine_plan(
        content_positive="CONTENT_ONLY_MARKER, pose.body.state: standing",
        content_negative="CONTENT_NEGATIVE_MARKER",
        workflow=workflow,
        shared_rendering=rendering_copy,
    )


def main() -> int:
    rendering = _load(RENDERING_PATH)

    with tempfile.TemporaryDirectory() as temp_dir:
        cache_root = Path(temp_dir) / "cache"
        compiled = compile_free_generation(
            ROOT,
            _engine_plan(rendering, lora_enabled=False),
            cache_root,
            seed=123,
        ).compiled_workflow

        if compiled["3"]["class_type"] != "CLIPTextEncode":
            raise AssertionError("content CLIP node is missing")
        if compiled["4"]["class_type"] != "CLIPTextEncode":
            raise AssertionError("rendering CLIP node is missing")
        if compiled["5"]["class_type"] != "ConditioningCombine":
            raise AssertionError("ConditioningCombine node is missing")

        content_text = compiled["3"]["inputs"]["text"]
        rendering_text = compiled["4"]["inputs"]["text"]
        if content_text != "CONTENT_ONLY_MARKER, pose.body.state: standing":
            raise AssertionError(f"content text was changed: {content_text!r}")
        if rendering_text != rendering["prompt"]["positive"]:
            raise AssertionError("rendering text is not isolated in its own CLIP node")
        if "CONTENT_ONLY_MARKER" in rendering_text:
            raise AssertionError("content leaked into rendering conditioning")
        if "mdanime_style" in content_text:
            raise AssertionError("rendering leaked into content conditioning")

        combine_inputs = compiled["5"]["inputs"]
        if combine_inputs.get("conditioning_1") != ["3", 0]:
            raise AssertionError(f"content conditioning is not wired to combine: {combine_inputs}")
        if combine_inputs.get("conditioning_2") != ["4", 0]:
            raise AssertionError(f"rendering conditioning is not wired to combine: {combine_inputs}")
        if compiled["7"]["inputs"].get("positive") != ["5", 0]:
            raise AssertionError("KSampler positive does not use combined conditioning")

        negative_text = compiled["6"]["inputs"]["text"]
        if "CONTENT_NEGATIVE_MARKER" not in negative_text:
            raise AssertionError("content negative is missing")
        if rendering["prompt"]["negative"] not in negative_text:
            raise AssertionError("rendering negative is missing")
        if compiled["7"]["inputs"].get("negative") != ["6", 0]:
            raise AssertionError("negative conditioning must remain separate from positive combine")

        if compiled["1"]["inputs"].get("ckpt_name") != "sd_xl_base_1.0.safetensors":
            raise AssertionError("checkpoint was not compiled")
        if compiled["7"]["inputs"].get("seed") != 123:
            raise AssertionError("sampler seed was not compiled")

        lora_compiled = compile_free_generation(
            ROOT,
            _engine_plan(rendering, lora_enabled=True),
            cache_root,
            seed=456,
        ).compiled_workflow
        if lora_compiled["90"]["class_type"] != "LoraLoader":
            raise AssertionError("rendering LoRA node is missing when enabled")
        for node_id in ("3", "4", "6"):
            if lora_compiled[node_id]["inputs"].get("clip") != ["90", 1]:
                raise AssertionError(f"node {node_id} is not using rendering-LoRA CLIP")
        if lora_compiled["7"]["inputs"].get("model") != ["90", 0]:
            raise AssertionError("KSampler is not using rendering-LoRA model")

    print("[FREE:CONDITIONING:CONTENT-CLIP:OK]")
    print("[FREE:CONDITIONING:RENDERING-CLIP:OK]")
    print("[FREE:CONDITIONING:COMBINE:OK]")
    print("[FREE:CONDITIONING:NEGATIVE-SEPARATE:OK]")
    print("[FREE:CONDITIONING:RENDERING-LORA-WIRING:OK]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
