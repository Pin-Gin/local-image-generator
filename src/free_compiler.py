from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


FREE_WORKFLOW_TEMPLATE = Path("workflows/free_sdxl_conditioned_api.json")


@dataclass(frozen=True)
class CompiledFreeGeneration:
    workflow_template_path: Path
    workflow_template_sha256: str
    compiled_workflow_path: Path
    compiled_workflow_sha256: str
    compiled_workflow: dict[str, Any]


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def _canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _join_negative(*values: str) -> str:
    parts: list[str] = []
    for value in values:
        text = value.strip()
        if text and text not in parts:
            parts.append(text)
    return ", ".join(parts)


def _normalize_comfy_lora_name(value: str) -> str:
    return value.replace("/", "\\")


def compile_free_generation(
    root: Path,
    engine_plan: dict[str, Any],
    cache_root: Path,
    *,
    seed: int = 1,
    filename_prefix: str = "LOCAL_RAG_FREE",
) -> CompiledFreeGeneration:
    if engine_plan.get("schema_version") != 1:
        raise ValueError("FREE engine plan schema_version must be 1")
    if engine_plan.get("engine_id") != "free-deterministic-v1":
        raise ValueError("unsupported FREE engine_id")
    if engine_plan.get("domain") != "free":
        raise ValueError("FREE engine plan domain must be free")

    ai = engine_plan.get("ai_interpretation")
    if not isinstance(ai, dict) or ai.get("enabled") is not False:
        raise ValueError("FREE engine plan must keep AI interpretation disabled")

    checkpoint = engine_plan.get("checkpoint")
    conditioning = engine_plan.get("conditioning")
    loras = engine_plan.get("loras")
    sampler_cfg = engine_plan.get("sampler")
    pose_control = engine_plan.get("pose_control")
    postprocess = engine_plan.get("postprocess")
    if not all(isinstance(item, dict) for item in (checkpoint, conditioning, loras, sampler_cfg, pose_control, postprocess)):
        raise ValueError("FREE engine plan sections are incomplete")

    checkpoint_name = checkpoint.get("name")
    if not isinstance(checkpoint_name, str) or not checkpoint_name.strip():
        raise ValueError("FREE checkpoint.name must be non-empty")

    content = conditioning.get("content")
    rendering = conditioning.get("rendering")
    lineart = conditioning.get("lineart")
    if not all(isinstance(item, dict) for item in (content, rendering, lineart)):
        raise ValueError("FREE conditioning sections are incomplete")
    if lineart.get("enabled") is not False:
        raise ValueError("lineart conditioning is not implemented in this compiler stage")
    if pose_control.get("enabled") is not False:
        raise ValueError("pose control is not implemented in this compiler stage")
    for stage in ("inpaint", "detailer", "upscale"):
        cfg = postprocess.get(stage)
        if not isinstance(cfg, dict) or cfg.get("enabled") is not False:
            raise ValueError(f"{stage} is not implemented in this compiler stage")

    content_positive = content.get("positive")
    content_negative = content.get("negative", "")
    rendering_positive = rendering.get("positive")
    rendering_negative = rendering.get("negative", "")
    for field_name, value, allow_empty in (
        ("content.positive", content_positive, False),
        ("content.negative", content_negative, True),
        ("rendering.positive", rendering_positive, False),
        ("rendering.negative", rendering_negative, True),
    ):
        if not isinstance(value, str) or (not allow_empty and not value.strip()):
            raise ValueError(f"FREE conditioning.{field_name} has invalid text")

    steps = sampler_cfg.get("steps")
    cfg = sampler_cfg.get("cfg")
    sampler_name = sampler_cfg.get("sampler_name")
    scheduler = sampler_cfg.get("scheduler")
    denoise = sampler_cfg.get("denoise")
    if not isinstance(steps, int) or isinstance(steps, bool) or steps <= 0:
        raise ValueError("FREE sampler.steps must be a positive integer")
    if not isinstance(cfg, (int, float)) or isinstance(cfg, bool):
        raise ValueError("FREE sampler.cfg must be numeric")
    if not isinstance(sampler_name, str) or not sampler_name.strip():
        raise ValueError("FREE sampler.sampler_name must be non-empty")
    if not isinstance(scheduler, str) or not scheduler.strip():
        raise ValueError("FREE sampler.scheduler must be non-empty")
    if not isinstance(denoise, (int, float)) or isinstance(denoise, bool):
        raise ValueError("FREE sampler.denoise must be numeric")
    if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
        raise ValueError("FREE seed must be a non-negative integer")
    if not isinstance(filename_prefix, str) or not filename_prefix.strip():
        raise ValueError("FREE filename_prefix must be non-empty")

    template_path = (root / FREE_WORKFLOW_TEMPLATE).resolve()
    workflow = copy.deepcopy(_read_json(template_path))
    template_sha = _sha256_bytes(template_path.read_bytes())

    workflow["1"]["inputs"]["ckpt_name"] = checkpoint_name.strip()
    workflow["3"]["inputs"]["text"] = content_positive
    workflow["4"]["inputs"]["text"] = rendering_positive
    workflow["6"]["inputs"]["text"] = _join_negative(content_negative, rendering_negative)

    sampler = workflow["7"]["inputs"]
    sampler["seed"] = seed
    sampler["steps"] = steps
    sampler["cfg"] = float(cfg)
    sampler["sampler_name"] = sampler_name.strip()
    sampler["scheduler"] = scheduler.strip()
    sampler["denoise"] = float(denoise)
    workflow["9"]["inputs"]["filename_prefix"] = filename_prefix.strip()

    rendering_lora = loras.get("rendering")
    if not isinstance(rendering_lora, dict):
        raise ValueError("FREE loras.rendering must be an object")
    enabled = rendering_lora.get("enabled")
    if not isinstance(enabled, bool):
        raise ValueError("FREE loras.rendering.enabled must be boolean")

    if enabled:
        lora_name = rendering_lora.get("lora_name")
        strength_model = rendering_lora.get("strength_model")
        strength_clip = rendering_lora.get("strength_clip")
        if not isinstance(lora_name, str) or not lora_name.strip():
            raise ValueError("FREE rendering LoRA name must be non-empty")
        if not isinstance(strength_model, (int, float)) or isinstance(strength_model, bool):
            raise ValueError("FREE rendering LoRA strength_model must be numeric")
        if not isinstance(strength_clip, (int, float)) or isinstance(strength_clip, bool):
            raise ValueError("FREE rendering LoRA strength_clip must be numeric")

        workflow["90"] = {
            "class_type": "LoraLoader",
            "inputs": {
                "lora_name": _normalize_comfy_lora_name(lora_name.strip()),
                "strength_model": float(strength_model),
                "strength_clip": float(strength_clip),
                "model": ["1", 0],
                "clip": ["1", 1],
            },
        }
        workflow["3"]["inputs"]["clip"] = ["90", 1]
        workflow["4"]["inputs"]["clip"] = ["90", 1]
        workflow["6"]["inputs"]["clip"] = ["90", 1]
        sampler["model"] = ["90", 0]

    compiled_bytes = _canonical_json_bytes(workflow)
    compiled_sha = _sha256_bytes(compiled_bytes)
    compiled_dir = cache_root / "compiled"
    compiled_dir.mkdir(parents=True, exist_ok=True)
    compiled_path = compiled_dir / f"free-engine-{compiled_sha[:12]}.json"
    compiled_path.write_bytes(compiled_bytes + b"\n")

    return CompiledFreeGeneration(
        workflow_template_path=template_path,
        workflow_template_sha256=template_sha,
        compiled_workflow_path=compiled_path,
        compiled_workflow_sha256=compiled_sha,
        compiled_workflow=workflow,
    )
