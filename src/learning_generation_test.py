from __future__ import annotations

import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

from compiler import compile_generation
from learning_registry import (
    resolve_selected_assets,
    select_assets_with_local_ai,
    validate_registry,
)


def _test_registry() -> dict:
    return validate_registry(
        {
            "schema_version": 1,
            "registry_version": 7,
            "assets": [
                {
                    "asset_id": "pose-hair-touch-v1",
                    "enabled": True,
                    "selection_mode": "ai",
                    "domains": ["free", "memoriela"],
                    "category": "pose",
                    "description": "Learned pose for naturally touching hair with one raised arm.",
                    "concepts": ["touching hair", "raised arm", "relaxed elbow"],
                    "runtime": {
                        "type": "lora",
                        "lora_name": "local-rag/pose/hair_touch_v1.safetensors",
                        "strength_model": 0.75,
                        "strength_clip": 0.65,
                        "trigger": "lr_pose_hair_touch",
                    },
                },
                {
                    "asset_id": "prompt-three-quarter-v1",
                    "enabled": True,
                    "selection_mode": "ai",
                    "domains": ["free"],
                    "category": "camera",
                    "description": "Learned reusable three-quarter camera phrasing.",
                    "concepts": ["three-quarter view", "3/4 view"],
                    "runtime": {
                        "type": "prompt",
                        "positive": "three-quarter view",
                        "negative": "flat frontal passport composition",
                    },
                },
            ],
        }
    )


class FakeClient:
    def __init__(self, response: str) -> None:
        self.response = response

    def chat(
        self,
        role: str,
        message: str,
        *,
        history=None,
        images_base64=None,
        json_mode: bool = False,
    ):
        assert role == "generate"
        assert "PRE-GENERATION" in message
        assert json_mode is True
        return SimpleNamespace(model="fake-selector", content=self.response)


def test_ai_selection() -> None:
    registry = _test_registry()
    selection = select_assets_with_local_ai(
        FakeClient('{"selected_asset_ids":["pose-hair-touch-v1"],"reason":"pose match"}'),
        registry,
        user_text="髪に片手を添えて立っている女性",
        generation_domain="free",
    )
    assert selection.selected_asset_ids == ("pose-hair-touch-v1",)
    assert selection.registry_version == 7
    assert selection.selector_model == "fake-selector"

    resolved = resolve_selected_assets(
        registry,
        selected_asset_ids=list(selection.selected_asset_ids),
        generation_domain="free",
    )
    assert resolved[0]["runtime"]["type"] == "lora"


def test_unknown_asset_rejected() -> None:
    registry = _test_registry()
    try:
        select_assets_with_local_ai(
            FakeClient('{"selected_asset_ids":["invented-id"],"reason":"bad"}'),
            registry,
            user_text="test",
            generation_domain="free",
        )
    except ValueError as exc:
        assert "unknown/ineligible" in str(exc)
    else:
        raise AssertionError("hallucinated asset ID was not rejected")


def test_lora_chain() -> None:
    root = Path(__file__).resolve().parent.parent
    with tempfile.TemporaryDirectory() as temp_dir:
        temp = Path(temp_dir)
        plan_path = temp / "plan.json"
        cache_root = temp / "cache"
        plan = {
            "profile_id": "learned-lora-chain-test",
            "workflow": {
                "mode": "text2img",
                "template": "workflows/sdxl_text2img_api.json",
                "checkpoint": "sd_xl_base_1.0.safetensors",
                "seed": 1,
                "steps": 20,
                "cfg": 6.5,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1.0,
                "filename_prefix": "TEST",
            },
            "prompt": {
                "positive": "test image",
                "negative": "",
            },
            "rendering_lora": {
                "enabled": True,
                "lora_name": "local-rag/rendering/matte_dimensional_anime_v1.safetensors",
                "strength_model": 0.9,
                "strength_clip": 0.7,
            },
            "learned_loras": [
                {
                    "asset_id": "pose-hair-touch-v1",
                    "lora_name": "local-rag/pose/hair_touch_v1.safetensors",
                    "strength_model": 0.75,
                    "strength_clip": 0.65,
                },
                {
                    "asset_id": "hand-natural-v1",
                    "lora_name": "local-rag/anatomy/hand_natural_v1.safetensors",
                    "strength_model": 0.6,
                    "strength_clip": 0.5,
                },
            ],
        }
        plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
        compiled = compile_generation(root, plan_path, cache_root).compiled_workflow

        assert compiled["90"]["inputs"]["model"] == ["1", 0]
        assert compiled["91"]["inputs"]["model"] == ["90", 0]
        assert compiled["92"]["inputs"]["model"] == ["91", 0]
        assert compiled["5"]["inputs"]["model"] == ["92", 0]
        assert compiled["3"]["inputs"]["clip"] == ["92", 1]
        assert compiled["4"]["inputs"]["clip"] == ["92", 1]


def main() -> int:
    test_ai_selection()
    test_unknown_asset_rejected()
    test_lora_chain()
    print("[LEARNED-GENERATION:TEST:OK]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
