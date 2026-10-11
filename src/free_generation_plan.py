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


def _validate_lora_config(value: Any, field_name: str) -> dict[str, Any]:
    lora = _require_object(value, field_name)
    enabled = lora.get("enabled")
    if not isinstance(enabled, bool):
        raise ValueError(f"{field_name}.enabled must be boolean")
    name = _require_string(lora.get("lora_name"), f"{field_name}.lora_name")
    strength_model = _require_number(lora.get("strength_model"), f"{field_name}.strength_model")
    strength_clip = _require_number(lora.get("strength_clip"), f"{field_name}.strength_clip")
    return {
        "enabled": enabled,
        "lora_name": name,
        "strength_model": strength_model,
        "strength_clip": strength_clip,
    }


def build_free_generation_engine_plan(
    *,
    content_positive: str,
    content_negative: str | None,
    workflow: dict[str, Any],
    shared_rendering: dict[str, Any],
    lineart_profile: dict[str, Any] | None = None,
    lineart_enabled: bool = False,
    lineart_strength: float | None = None,
) -> dict[str, Any]:
    """Build the deterministic FREE engine contract.

    Content, rendering, line-art, pose control, and post-processing remain separate.
    This contract contains no local-AI/Qwen selection or rewriting step.
    """

    positive = _require_string(content_positive, "content_positive")
    negative = "" if content_negative is None else _require_string(
        content_negative,
        "content_negative",
        allow_empty=True,
    )

    if not isinstance(lineart_enabled, bool):
        raise ValueError("lineart_enabled must be boolean")

    workflow_cfg = _require_object(workflow, "workflow")
    rendering_cfg = _require_object(shared_rendering, "shared_rendering")
    rendering_prompt = _require_object(rendering_cfg.get("prompt"), "shared_rendering.prompt")
    rendering_lora = _validate_lora_config(rendering_cfg.get("lora"), "shared_rendering.lora")

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

    lineart_id: str | None = None
    lineart_positive = ""
    lineart_negative = ""
    resolved_lineart_strength = 1.0
    lineart_lora: dict[str, Any] | None = None

    if lineart_profile is not None:
        profile = _require_object(lineart_profile, "lineart_profile")
        if profile.get("schema_version") != 1:
            raise ValueError("lineart_profile.schema_version must be 1")
        lineart_id = _require_string(profile.get("lineart_id"), "lineart_profile.lineart_id")
        lineart_prompt = _require_object(profile.get("prompt"), "lineart_profile.prompt")
        lineart_positive = _require_string(
            lineart_prompt.get("positive"),
            "lineart_profile.prompt.positive",
        )
        lineart_negative = _require_string(
            lineart_prompt.get("negative", ""),
            "lineart_profile.prompt.negative",
            allow_empty=True,
        )
        default_strength = _require_number(
            profile.get("default_strength", 1.0),
            "lineart_profile.default_strength",
        )
        resolved_lineart_strength = default_strength if lineart_strength is None else _require_number(
            lineart_strength,
            "lineart_strength",
        )
        if resolved_lineart_strength <= 0 or resolved_lineart_strength > 2.0:
            raise ValueError("lineart_strength must be > 0 and <= 2.0")
        lineart_lora = _validate_lora_config(profile.get("lora"), "lineart_profile.lora")
    elif lineart_enabled:
        raise ValueError("lineart_profile is required when lineart is enabled")

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
                "enabled": lineart_enabled,
                "profile_id": lineart_id,
                "strength": resolved_lineart_strength,
                "positive": lineart_positive if lineart_enabled else "",
                "negative": lineart_negative if lineart_enabled else "",
            },
        },
        "loras": {
            "rendering": copy.deepcopy(rendering_lora),
            "lineart": copy.deepcopy(lineart_lora),
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
