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
    "rendering": {
        "ANIME_2D": "2D anime illustration",
    },
}


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


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


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
    if intent.get("status") != "parsed":
        raise ValueError("Generation requires request.intent.status=parsed")

    profile_id = request.get("profile_id")
    if not isinstance(profile_id, str) or not profile_id:
        raise ValueError("request.profile_id must be a non-empty string")

    profile_path = find_profile_path(profiles_root, profile_id)
    base_profile = _load_json(profile_path)
    derived = copy.deepcopy(base_profile)

    base_prompt = derived.get("prompt")
    if not isinstance(base_prompt, dict):
        raise ValueError("profile.prompt must be an object")
    positive = base_prompt.get("positive")
    if not isinstance(positive, str) or not positive.strip():
        raise ValueError("profile.prompt.positive must be a non-empty string")

    fragments: list[str] = []
    for category, mapping in INTENT_PROMPT_FRAGMENTS.items():
        value = intent.get(category)
        if value is None:
            continue
        if not isinstance(value, str):
            raise ValueError(f"request.intent.{category} must be string or null")
        fragment = mapping.get(value)
        if fragment is None:
            raise ValueError(f"Unsupported normalized intent: {category}={value}")
        fragments.append(fragment)

    effective_positive = ", ".join([positive.strip(), *fragments]) if fragments else positive.strip()
    derived["prompt"]["positive"] = effective_positive

    options = request.get("options")
    if isinstance(options, dict):
        seed = options.get("seed")
        if seed is not None:
            if not isinstance(seed, int) or seed < 0:
                raise ValueError("request.options.seed must be a non-negative integer or null")
            derived["workflow"]["seed"] = seed

    derived["request_context"] = {
        "request_id": request.get("request_id"),
        "source": request.get("source"),
        "user_text": request.get("user_text"),
        "normalized_intent": intent,
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
    manifest_payload["generation_plan"] = {
        "path": str(plan_path),
        "sha256": _sha256_bytes(plan_path.read_bytes()),
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
    )
