from __future__ import annotations

import copy
from typing import Any


FREE_ENGINE_SCHEMA_VERSION = 1
FREE_ENGINE_ID = "free-deterministic-v1"


def _require_object(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be an object")
    return value


def _require_string(value: Any, field_name: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    if not allow_empty and not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip() if not allow_empty else value


def _require_number(value: Any, field_name: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{field_name} must be numeric")
    return float(value)


def build_free_generation_engine_plan(
    *,
    content_positive: str,
    content_negative: str | None,
    workflow: dict[str, Any],
    shared_rendering: dict[str, Any],
) -> dict[str, Any]:
    """Build the deterministic FREE engine contract.

    This contract intentionally separates content, rendering, line-art, pose control,
    and post-processing. It contains no local-AI/Qwen selection or rewriting step.
    The compiler will consume these channels incrementally as the new engine replaces
    the legacy single-prompt workflow.
    """

    positive = _require_string(content_positive, "content_positive")
    negative = "" if content_negative is None else _require_string(
        content_negative,
        "content_negative",
        allow_empty=True,
    )

    workflow_cfg = _require_object(workflow, "workflow")
    rendering_cfg = _require_object(shared_rendering, "shared_rendering")
    rendering_prompt = _require_object(rendering_cfg.get("prompt"), "shared_rendering.prompt")
    rendering_lora = _require_object(rendering_cfg.get("lora"), "shared_rendering.lora")

    checkpoint = _require_string(workflow_cfg.get("checkpoint"), "workflow.checkpoint")
    steps = workflow_cfg.get("steps")
    if not isinstance(steps, int) or isinstance(steps, bool) or steps <= 0:
        raise ValueError("workflow.steps must be a positive integer")
    cfg = _require_number(workflow_cfg.get("cfg"), "workflow.cfg")
    sampler_name = _require_string(workflow_cfg.get("sampler_name"), "workflow.sampler_name")
    scheduler = _require_string(workflow_cfg.get("scheduler"), "workflow.scheduler")
    denoise = _require_number(workflow_cfg.get("denoise", 1.0), "workflow.denoise")

    rendering_positive = _require_string(
        rendering_prompt.get("positive"),
        "shared_rendering.prompt.positive",
    )
    rendering_negative = _require_string(
        rendering_prompt.get("negative", ""),
        "shared_rendering.prompt.negative",
        allow_empty=True,
    )

    if not isinstance(rendering_lora.get("enabled"), bool):
        raise ValueError("shared_rendering.lora.enabled must be boolean")
    _require_string(rendering_lora.get("lora_name"), "shared_rendering.lora.lora_name")
    _require_number(rendering_lora.get("strength_model"), "shared_rendering.lora.strength_model")
    _require_number(rendering_lora.get("strength_clip"), "shared_rendering.lora.strength_clip")

    return {
        "schema_version": FREE_ENGINE_SCHEMA_VERSION,
        "engine_id": FREE_ENGINE_ID,
        "domain": "free",
        "ai_interpretation": {
            "enabled": False,
            "policy": "deterministic-input-only",
        },
        "checkpoint": {
            "name": checkpoint,
        },
        "conditioning": {
            "content": {
                "positive": positive,
                "negative": negative,
            },
            "rendering": {
                "positive": rendering_positive,
                "negative": rendering_negative,
            },
            "lineart": {
                "enabled": False,
                "positive": "",
                "negative": "",
            },
        },
        "loras": {
            "rendering": copy.deepcopy(rendering_lora),
            "lineart": None,
        },
        "pose_control": {
            "enabled": False,
            "backend": None,
            "source": None,
        },
        "sampler": {
            "steps": steps,
            "cfg": cfg,
            "sampler_name": sampler_name,
            "scheduler": scheduler,
            "denoise": denoise,
        },
        "postprocess": {
            "inpaint": {
                "enabled": False,
            },
            "detailer": {
                "enabled": False,
            },
            "upscale": {
                "enabled": False,
            },
        },
    }
