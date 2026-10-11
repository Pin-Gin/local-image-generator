from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from comfyui_client import run_workflow_and_download, upload_input_image
from compiler import CompiledGeneration, compile_generation
from database import import_manifest, initialize_database
from manifest import build_generation_manifest, write_manifest


INTENT_PROMPT_FRAGMENTS = {
    "character": {
        "YURA": "preserve the referenced YURA character identity",
    },
    "outfit": {
        "MASTER_REFERENCE": "preserve the referenced outfit",
    },
    "background": {
        "WHITE": "plain white background",
    },
    "pose": {
        "FRONT_STANDING": "full body, front view, standing",
    },
    "expression": {
        "CALM_NEUTRAL": "calm neutral expression",
    },
    "hair": {
        "MASTER_REFERENCE": "preserve the referenced hair identity and hairstyle",
    },
}

SHARED_RENDERING_PATH = Path("shared/rendering/matte_dimensional_anime.json")
FREE_PROFILE_ID = "free-sdxl-v1"
MEMORIELA_PROFILE_BY_CHARACTER = {
    "YURA": "yura-working-master-g3",
}
FREE_MODES = {"free_text2img", "generic_text2img"}
MEMORIELA_MODES = {"memoriela_character", "yura_img2img"}


@dataclass(frozen=True)
class ChatGenerationResult:
    request: dict[str, Any]
    generation_plan_path: Path
    generation_id: str
    prompt_id: str
    output_path: Path
    output_sha256: str
    manifest_path: Path
    manifest_sha256: str
    database_path: Path
    generation_mode: str


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def _append_prompt(base: str, additions: list[str]) -> str:
    parts: list[str] = []
    if base.strip():
        parts.append(base.strip())
    for value in additions:
        text = value.strip()
        if text and text not in parts:
            parts.append(text)
    return ", ".join(parts)


def _load_shared_rendering(root: Path) -> tuple[dict[str, Any], str, str]:
    path = root / SHARED_RENDERING_PATH
    payload = _load_json(path)
    if payload.get("schema_version") != 1:
        raise ValueError("shared rendering schema_version must be 1")

    prompt = payload.get("prompt")
    generation = payload.get("generation")
    lora = payload.get("lora")
    if not isinstance(prompt, dict):
        raise ValueError("shared rendering prompt must be an object")
    if not isinstance(generation, dict):
        raise ValueError("shared rendering generation must be an object")
    if not isinstance(lora, dict):
        raise ValueError("shared rendering lora must be an object")

    positive = prompt.get("positive")
    negative = prompt.get("negative")
    if not isinstance(positive, str) or not positive.strip():
        raise ValueError("shared rendering prompt.positive must be a non-empty string")
    if not isinstance(negative, str):
        raise ValueError("shared rendering prompt.negative must be a string")

    required_generation = {
        "checkpoint": str,
        "steps": int,
        "cfg": (int, float),
        "sampler_name": str,
        "scheduler": str,
    }
    for key, expected_type in required_generation.items():
        if not isinstance(generation.get(key), expected_type):
            raise ValueError(f"shared rendering generation.{key} has invalid type")

    if not isinstance(lora.get("enabled"), bool):
        raise ValueError("shared rendering lora.enabled must be boolean")
    if not isinstance(lora.get("lora_name"), str) or not lora.get("lora_name"):
        raise ValueError("shared rendering lora.lora_name must be a non-empty string")
    for key in ("strength_model", "strength_clip"):
        if not isinstance(lora.get(key), (int, float)):
            raise ValueError(f"shared rendering lora.{key} must be numeric")

    return payload, positive.strip(), negative.strip()


def find_profile_path(profiles_root: Path, profile_id: str) -> Path:
    for path in sorted(profiles_root.glob("*.json")):
        try:
            payload = _load_json(path)
        except (OSError, json.JSONDecodeError, ValueError):
            continue
        if payload.get("profile_id") == profile_id:
            return path
    raise ValueError(f"Unknown profile_id: {profile_id}")


def build_generation_plan(
    root: Path,
    request: dict[str, Any],
    profiles_root: Path,
    cache_root: Path,
) -> Path:
    intent = request.get("intent")
    if not isinstance(intent, dict):
        raise ValueError("request.intent must be an object")
    if intent.get("status") not in {"parsed", "unparsed", "needs_confirmation"}:
        raise ValueError("request.intent.status is invalid")

    prompt_input = request.get("prompt_input")
    if not isinstance(prompt_input, dict):
        raise ValueError("request.prompt_input must be an object")
    freeform_positive = prompt_input.get("positive")
    freeform_negative = prompt_input.get("negative")
    if not isinstance(freeform_positive, str) or not freeform_positive.strip():
        raise ValueError("request.prompt_input.positive must be a non-empty string")
    if freeform_negative is not None and not isinstance(freeform_negative, str):
        raise ValueError("request.prompt_input.negative must be string or null")

    target_mode = request.get("target_mode")
    if target_mode not in FREE_MODES | MEMORIELA_MODES:
        raise ValueError("request.target_mode must be free_text2img or memoriela_character")

    generation_domain = request.get("generation_domain")
    if generation_domain not in {"free", "memoriela", None}:
        raise ValueError("request.generation_domain must be free or memoriela")

    requested_profile_id = request.get("profile_id")
    if not isinstance(requested_profile_id, str) or not requested_profile_id:
        raise ValueError("request.profile_id must be a non-empty string")

    if target_mode in FREE_MODES:
        effective_profile_id = FREE_PROFILE_ID
    else:
        character_id = intent.get("character")
        if not isinstance(character_id, str) or character_id not in MEMORIELA_PROFILE_BY_CHARACTER:
            raise ValueError(
                f"MEMORIELA character route is not registered yet: {character_id or 'unknown'}"
            )
        effective_profile_id = MEMORIELA_PROFILE_BY_CHARACTER[character_id]

    profile_path = find_profile_path(profiles_root, effective_profile_id)
    base_profile = _load_json(profile_path)
    derived = copy.deepcopy(base_profile)

    base_prompt = derived.get("prompt")
    workflow = derived.get("workflow")
    if not isinstance(base_prompt, dict):
        raise ValueError("profile.prompt must be an object")
    if not isinstance(workflow, dict):
        raise ValueError("profile.workflow must be an object")

    positive = base_prompt.get("positive")
    negative = base_prompt.get("negative")
    if not isinstance(positive, str) or not positive.strip():
        raise ValueError("profile.prompt.positive must be a non-empty string")
    if not isinstance(negative, str):
        raise ValueError("profile.prompt.negative must be a string")

    shared_rendering, shared_positive, shared_negative = _load_shared_rendering(root)
    shared_generation = shared_rendering["generation"]
    workflow["checkpoint"] = shared_generation["checkpoint"]
    workflow["steps"] = shared_generation["steps"]
    workflow["cfg"] = shared_generation["cfg"]
    workflow["sampler_name"] = shared_generation["sampler_name"]
    workflow["scheduler"] = shared_generation["scheduler"]
    derived["rendering_lora"] = copy.deepcopy(shared_rendering["lora"])

    fragments: list[str] = []
    for category, mapping in INTENT_PROMPT_FRAGMENTS.items():
        value = intent.get(category)
        if value is None:
            continue
        if not isinstance(value, str):
            raise ValueError(f"request.intent.{category} must be string or null")
        fragment = mapping.get(value)
        if fragment is not None:
            fragments.append(fragment)

    if target_mode in MEMORIELA_MODES:
        workflow["mode"] = "img2img"
        derived["prompt"]["positive"] = _append_prompt(
            positive,
            [shared_positive, *fragments, freeform_positive],
        )
        negative_additions = [shared_negative]
        if isinstance(freeform_negative, str) and freeform_negative.strip():
            negative_additions.append(freeform_negative)
        derived["prompt"]["negative"] = _append_prompt(negative, negative_additions)
        generation_mode = "memoriela_yura_img2img"
        generation_domain = "memoriela"
    else:
        workflow["mode"] = "text2img"
        workflow["template"] = "workflows/sdxl_text2img_api.json"
        workflow["denoise"] = 1.0
        workflow["filename_prefix"] = "LOCAL_RAG_FREE"
        generic_fragments = [
            fragment
            for category, mapping in INTENT_PROMPT_FRAGMENTS.items()
            if category != "character"
            for value in [intent.get(category)]
            if isinstance(value, str) and (fragment := mapping.get(value)) is not None
        ]
        derived["prompt"]["positive"] = _append_prompt(
            "",
            [shared_positive, *generic_fragments, freeform_positive],
        )
        additions = [shared_negative, "blurry, low quality"]
        if isinstance(freeform_negative, str) and freeform_negative.strip():
            additions.append(freeform_negative)
        derived["prompt"]["negative"] = _append_prompt("", additions)
        generation_mode = "free_text2img"
        generation_domain = "free"

    options = request.get("options")
    if isinstance(options, dict):
        seed = options.get("seed")
        if seed is not None:
            if not isinstance(seed, int) or seed < 0:
                raise ValueError("request.options.seed must be a non-negative integer or null")
            workflow["seed"] = seed

    derived["shared_rendering"] = shared_rendering
    derived["request_context"] = {
        "request_id": request.get("request_id"),
        "source": request.get("source"),
        "user_text": request.get("user_text"),
        "normalized_intent": intent,
        "prompt_input": prompt_input,
        "generation_domain": generation_domain,
        "target_mode": target_mode,
        "generation_mode": generation_mode,
        "rendering_id": shared_rendering.get("rendering_id"),
        "rendering_version": shared_rendering.get("rendering_version"),
        "rendering_lora_enabled": shared_rendering["lora"].get("enabled"),
        "requested_profile_id": requested_profile_id,
        "effective_profile_id": effective_profile_id,
        "base_profile_path": str(profile_path.relative_to(root)),
        "base_profile_sha256": hashlib.sha256(profile_path.read_bytes()).hexdigest(),
    }

    plan_bytes = _canonical_json_bytes(derived)
    request_id = request.get("request_id")
    if not isinstance(request_id, str) or not request_id:
        raise ValueError("request.request_id must be a non-empty string")

    plan_dir = cache_root / "requests"
    plan_dir.mkdir(parents=True, exist_ok=True)
    plan_path = plan_dir / f"{request_id}.generation.json"
    plan_path.write_bytes(plan_bytes + b"\n")
    return plan_path


def run_chat_generation(
    root: Path,
    request: dict[str, Any],
    config: dict[str, Any],
) -> ChatGenerationResult:
    paths = config.get("paths")
    comfyui = config.get("comfyui")
    if not isinstance(paths, dict) or not isinstance(comfyui, dict):
        raise ValueError("config.paths and config.comfyui must be objects")

    profiles_root = root / str(paths["profiles"])
    cache_root = root / str(paths["cache"])
    outputs_root = root / str(paths["outputs"])
    database_path = root / str(paths["database"])

    base_url = comfyui.get("base_url")
    if not isinstance(base_url, str) or not base_url:
        raise ValueError("config.comfyui.base_url must be a non-empty string")
    request_timeout = float(comfyui.get("timeout_seconds", 5))
    generation_timeout = float(comfyui.get("generation_timeout_seconds", 180))

    plan_path = build_generation_plan(root, request, profiles_root, cache_root)
    compiled: CompiledGeneration = compile_generation(root, plan_path, cache_root)
    plan = _load_json(plan_path)

    workflow_cfg = plan.get("workflow")
    if not isinstance(workflow_cfg, dict):
        raise ValueError("generation plan workflow must be an object")

    mode = workflow_cfg.get("mode", "img2img")
    if mode == "img2img":
        if compiled.authority is None:
            raise RuntimeError("img2img authority was not resolved")
        master_path = plan["authority"]["master_image_path"]
        master_file = compiled.authority.files[master_path]
        remote_name = master_file.local_path.name
        uploaded_name = upload_input_image(
            base_url=base_url,
            source=master_file.local_path,
            remote_name=remote_name,
            timeout_seconds=request_timeout,
        )
        if uploaded_name != remote_name:
            raise RuntimeError(
                f"Unexpected ComfyUI upload name: expected={remote_name} actual={uploaded_name}"
            )

    generation_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_dir = outputs_root / generation_id
    run_dir.mkdir(parents=True, exist_ok=False)

    result = run_workflow_and_download(
        base_url=base_url,
        workflow=compiled.compiled_workflow,
        output_dir=run_dir,
        request_timeout_seconds=request_timeout,
        generation_timeout_seconds=generation_timeout,
    )

    manifest_payload = build_generation_manifest(compiled, result, result.output_path)
    manifest_payload["generation_id"] = generation_id
    manifest_payload["request"] = request
    manifest_payload["shared_rendering"] = plan.get("shared_rendering")
    manifest_payload["generation_plan"] = {
        "path": str(plan_path),
        "sha256": _sha256_bytes(plan_path.read_bytes()),
        "mode": mode,
        "domain": plan.get("request_context", {}).get("generation_domain"),
    }
    manifest_path = run_dir / "manifest.json"
    manifest_sha256 = write_manifest(manifest_path, manifest_payload)

    initialize_database(database_path)
    import_manifest(database_path, manifest_path)

    return ChatGenerationResult(
        request=request,
        generation_plan_path=plan_path,
        generation_id=generation_id,
        prompt_id=result.prompt_id,
        output_path=result.output_path,
        output_sha256=manifest_payload["output"]["sha256"],
        manifest_path=manifest_path,
        manifest_sha256=manifest_sha256,
        database_path=database_path,
        generation_mode=str(plan.get("request_context", {}).get("generation_mode", mode)),
    )
