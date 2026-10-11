from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from authority import AuthorityBundle, resolve_authority_bundle


@dataclass(frozen=True)
class CompiledGeneration:
    profile_path: Path
    profile_sha256: str
    authority: AuthorityBundle | None
    workflow_template_path: Path
    workflow_template_sha256: str
    compiled_workflow_path: Path
    compiled_workflow_sha256: str
    compiled_workflow: dict[str, Any]


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _normalize_comfy_lora_name(value: str) -> str:
    # ComfyUI on Windows exposes nested LoRAs with backslashes in the
    # LoraLoader input list. Normalize at compile time so stale/shared config
    # using forward slashes cannot produce a prompt validation mismatch.
    return value.replace("/", "\\")


def _validate_rendering_lora(profile: dict[str, Any]) -> dict[str, Any] | None:
    value = profile.get("rendering_lora")
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("profile.rendering_lora must be an object")
    enabled = value.get("enabled")
    if not isinstance(enabled, bool):
        raise ValueError("profile.rendering_lora.enabled must be boolean")
    if not enabled:
        return None

    lora_name = value.get("lora_name")
    strength_model = value.get("strength_model")
    strength_clip = value.get("strength_clip")
    if not isinstance(lora_name, str) or not lora_name.strip():
        raise ValueError("profile.rendering_lora.lora_name must be a non-empty string")
    if not isinstance(strength_model, (int, float)):
        raise ValueError("profile.rendering_lora.strength_model must be numeric")
    if not isinstance(strength_clip, (int, float)):
        raise ValueError("profile.rendering_lora.strength_clip must be numeric")
    return value


def compile_generation(root: Path, profile_path: Path, cache_root: Path) -> CompiledGeneration:
    profile = _read_json(profile_path)
    profile_sha256 = _sha256_file(profile_path)

    workflow_cfg = profile.get("workflow")
    prompt_cfg = profile.get("prompt")
    if not isinstance(workflow_cfg, dict):
        raise ValueError("profile.workflow must be an object")
    if not isinstance(prompt_cfg, dict):
        raise ValueError("profile.prompt must be an object")

    mode = workflow_cfg.get("mode", "img2img")
    if mode not in {"img2img", "text2img"}:
        raise ValueError("profile.workflow.mode must be img2img or text2img")

    # Only MEMORIELA reference generation needs remote authority.
    # FREE text2img remains fully local.
    authority: AuthorityBundle | None = None
    if mode == "img2img":
        authority = resolve_authority_bundle(profile, cache_root)

    template_value = workflow_cfg.get("template")
    if not isinstance(template_value, str) or not template_value:
        raise ValueError("profile.workflow.template must be a non-empty string")
    workflow_template_path = (root / template_value).resolve()
    workflow = _read_json(workflow_template_path)
    workflow_template_sha256 = _sha256_file(workflow_template_path)

    required_workflow_fields = {
        "checkpoint": str,
        "seed": int,
        "steps": int,
        "cfg": (int, float),
        "sampler_name": str,
        "scheduler": str,
        "denoise": (int, float),
        "filename_prefix": str,
    }
    for key, expected_type in required_workflow_fields.items():
        value = workflow_cfg.get(key)
        if not isinstance(value, expected_type):
            raise ValueError(f"profile.workflow.{key} has invalid type")

    positive = prompt_cfg.get("positive")
    negative = prompt_cfg.get("negative")
    if not isinstance(positive, str) or not positive.strip():
        raise ValueError("profile.prompt.positive must be a non-empty string")
    if not isinstance(negative, str):
        raise ValueError("profile.prompt.negative must be a string")

    rendering_lora = _validate_rendering_lora(profile)

    compiled = copy.deepcopy(workflow)
    try:
        compiled["1"]["inputs"]["ckpt_name"] = workflow_cfg["checkpoint"]

        if mode == "img2img":
            if authority is None:
                raise RuntimeError("img2img authority was not resolved")
            master_path = profile["authority"]["master_image_path"]
            master_file = authority.files[master_path]
            compiled["2"]["inputs"]["image"] = master_file.local_path.name
            compiled["4"]["inputs"]["text"] = positive
            compiled["5"]["inputs"]["text"] = negative
            positive_node = compiled["4"]["inputs"]
            negative_node = compiled["5"]["inputs"]
            sampler = compiled["6"]["inputs"]
            save_node = compiled["8"]["inputs"]
        else:
            compiled["3"]["inputs"]["text"] = positive
            compiled["4"]["inputs"]["text"] = negative
            positive_node = compiled["3"]["inputs"]
            negative_node = compiled["4"]["inputs"]
            sampler = compiled["5"]["inputs"]
            save_node = compiled["7"]["inputs"]

        if rendering_lora is not None:
            compiled["90"] = {
                "class_type": "LoraLoader",
                "inputs": {
                    "lora_name": _normalize_comfy_lora_name(rendering_lora["lora_name"]),
                    "strength_model": rendering_lora["strength_model"],
                    "strength_clip": rendering_lora["strength_clip"],
                    "model": ["1", 0],
                    "clip": ["1", 1],
                },
            }
            positive_node["clip"] = ["90", 1]
            negative_node["clip"] = ["90", 1]
            sampler["model"] = ["90", 0]

        sampler["seed"] = workflow_cfg["seed"]
        sampler["steps"] = workflow_cfg["steps"]
        sampler["cfg"] = workflow_cfg["cfg"]
        sampler["sampler_name"] = workflow_cfg["sampler_name"]
        sampler["scheduler"] = workflow_cfg["scheduler"]
        sampler["denoise"] = workflow_cfg["denoise"]
        save_node["filename_prefix"] = workflow_cfg["filename_prefix"]
    except (KeyError, TypeError) as exc:
        raise RuntimeError(f"Workflow template does not match the expected {mode} node contract") from exc

    compiled_bytes = _canonical_json_bytes(compiled)
    compiled_sha256 = _sha256_bytes(compiled_bytes)

    compiled_dir = cache_root / "compiled"
    compiled_dir.mkdir(parents=True, exist_ok=True)
    profile_id = profile.get("profile_id", "generation")
    if not isinstance(profile_id, str) or not profile_id:
        raise ValueError("profile.profile_id must be a non-empty string")
    compiled_workflow_path = compiled_dir / f"{profile_id}-{compiled_sha256[:12]}.json"
    compiled_workflow_path.write_bytes(compiled_bytes + b"\n")

    return CompiledGeneration(
        profile_path=profile_path,
        profile_sha256=profile_sha256,
        authority=authority,
        workflow_template_path=workflow_template_path,
        workflow_template_sha256=workflow_template_sha256,
        compiled_workflow_path=compiled_workflow_path,
        compiled_workflow_sha256=compiled_sha256,
        compiled_workflow=compiled,
    )
