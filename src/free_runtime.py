from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from comfyui_client import run_workflow_and_download, upload_input_image
from database import import_manifest
from free_compiler import CompiledFreeGeneration, compile_free_generation
from free_generation_plan import build_free_generation_engine_plan
from manifest import write_manifest
from model_catalog import resolve_project_checkpoint


FREE_PROFILE_PATH = Path("profiles/free_sdxl_v1.json")
SHARED_RENDERING_PATH = Path("shared/rendering/matte_dimensional_anime.json")
LINEART_PROFILE_PATH = Path("shared/lineart/strong_anime_lineart.json")
POSE_CONTROLNET_MODEL = "SDXL/controlnet-openpose-sdxl-1.0/diffusion_pytorch_model.safetensors"
POSE_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


@dataclass(frozen=True)
class FreeGenerationResult:
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
    learned_asset_ids: tuple[str, ...]


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def _canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _resolve_runtime_path(root: Path, value: Any, field_name: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"config.paths.{field_name} must be a non-empty string")
    path = Path(value)
    return path if path.is_absolute() else root / path


def _require_pose_number(value: Any, field_name: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"FREE pose_control.{field_name} must be numeric")
    return float(value)


def _resolve_pose_request(root: Path, source_json: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(source_json, dict) or "pose_control" not in source_json:
        return None

    request = source_json.get("pose_control")
    if request is False or request is None:
        return None
    if not isinstance(request, dict):
        raise ValueError("FREE pose_control must be an object, false, or omitted")

    enabled = request.get("enabled", True)
    if not isinstance(enabled, bool):
        raise ValueError("FREE pose_control.enabled must be boolean")
    if not enabled:
        return None

    source_value = request.get("source")
    if not isinstance(source_value, str) or not source_value.strip():
        raise ValueError("FREE pose_control.source must be a non-empty image path")
    source_path = Path(source_value.strip())
    if not source_path.is_absolute():
        source_path = root / source_path
    source_path = source_path.resolve()
    if not source_path.is_file():
        raise ValueError(f"FREE pose_control.source was not found: {source_path}")
    if source_path.suffix.lower() not in POSE_IMAGE_SUFFIXES:
        raise ValueError(f"FREE pose_control.source has unsupported image type: {source_path.suffix}")

    strength = _require_pose_number(request.get("strength", 0.9), "strength")
    start_percent = _require_pose_number(request.get("start_percent", 0.0), "start_percent")
    end_percent = _require_pose_number(request.get("end_percent", 1.0), "end_percent")
    if strength <= 0 or strength > 2.0:
        raise ValueError("FREE pose_control.strength must be > 0 and <= 2.0")
    if not 0 <= start_percent < end_percent <= 1:
        raise ValueError("FREE pose_control percent range must satisfy 0 <= start < end <= 1")

    resolution = request.get("resolution", 1024)
    if not isinstance(resolution, int) or isinstance(resolution, bool) or resolution <= 0:
        raise ValueError("FREE pose_control.resolution must be a positive integer")

    switches: dict[str, bool] = {}
    for key, default in (
        ("detect_hand", True),
        ("detect_body", True),
        ("detect_face", False),
        ("scale_stick_for_xinsr_cn", True),
    ):
        value = request.get(key, default)
        if not isinstance(value, bool):
            raise ValueError(f"FREE pose_control.{key} must be boolean")
        switches[key] = value

    model = request.get("model", POSE_CONTROLNET_MODEL)
    if not isinstance(model, str) or not model.strip():
        raise ValueError("FREE pose_control.model must be a non-empty string")

    return {
        "source_path": source_path,
        "source_sha256": _sha256_file(source_path),
        "strength": strength,
        "start_percent": start_percent,
        "end_percent": end_percent,
        "resolution": resolution,
        "detect_hand": switches["detect_hand"],
        "detect_body": switches["detect_body"],
        "detect_face": switches["detect_face"],
        "scale_stick_for_xinsr_cn": switches["scale_stick_for_xinsr_cn"],
        "model": model.strip(),
    }


def _resolve_free_controls(
    *,
    root: Path,
    prompt_input: dict[str, Any],
    default_checkpoint: str,
    lineart_profile: dict[str, Any],
) -> tuple[str, bool, float | None, dict[str, Any] | None]:
    source_json = prompt_input.get("json")
    if source_json is not None and not isinstance(source_json, dict):
        raise ValueError("request.prompt_input.json must be an object or null")

    requested_checkpoint: Any = default_checkpoint
    lineart_request: Any = None
    if isinstance(source_json, dict):
        if "checkpoint" in source_json:
            requested_checkpoint = source_json.get("checkpoint")
        if "lineart" in source_json:
            lineart_request = source_json.get("lineart")

    checkpoint_name = resolve_project_checkpoint(root, requested_checkpoint)

    lineart_enabled = False
    lineart_strength: float | None = None
    if lineart_request is not None:
        if isinstance(lineart_request, bool):
            lineart_enabled = lineart_request
        elif isinstance(lineart_request, dict):
            enabled = lineart_request.get("enabled", True)
            if not isinstance(enabled, bool):
                raise ValueError("FREE lineart.enabled must be boolean")
            lineart_enabled = enabled

            preset = lineart_request.get("preset")
            if preset is not None:
                expected_preset = lineart_profile.get("lineart_id")
                if not isinstance(preset, str) or preset != expected_preset:
                    raise ValueError(f"unsupported FREE lineart preset: {preset}")

            if "strength" in lineart_request:
                strength = lineart_request.get("strength")
                if not isinstance(strength, (int, float)) or isinstance(strength, bool):
                    raise ValueError("FREE lineart.strength must be numeric")
                lineart_strength = float(strength)
        else:
            raise ValueError("FREE lineart must be boolean, object, or omitted")

    pose_request = _resolve_pose_request(root, source_json)
    return checkpoint_name, lineart_enabled, lineart_strength, pose_request


def _build_manifest(
    *,
    request: dict[str, Any],
    engine_plan: dict[str, Any],
    plan_path: Path,
    profile_path: Path,
    profile: dict[str, Any],
    shared_rendering: dict[str, Any],
    compiled: CompiledFreeGeneration,
    result: Any,
    generation_id: str,
    seed: int,
    filename_prefix: str,
) -> dict[str, Any]:
    sampler = engine_plan["sampler"]
    content = engine_plan["conditioning"]["content"]
    rendering = engine_plan["conditioning"]["rendering"]
    lineart = engine_plan["conditioning"]["lineart"]

    return {
        "schema_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "generated",
        "generation_id": generation_id,
        "profile": {
            "path": str(profile_path),
            "sha256": _sha256_file(profile_path),
            "profile_id": profile.get("profile_id"),
            "profile_version": profile.get("profile_version"),
            "character": None,
            "authority_mode": "none",
        },
        "authority": {},
        "workflow": {
            "template_path": str(compiled.workflow_template_path),
            "template_sha256": compiled.workflow_template_sha256,
            "compiled_path": str(compiled.compiled_workflow_path),
            "compiled_sha256": compiled.compiled_workflow_sha256,
        },
        "generation": {
            "engine_id": engine_plan.get("engine_id"),
            "checkpoint": engine_plan["checkpoint"]["name"],
            "seed": seed,
            "steps": sampler["steps"],
            "cfg": sampler["cfg"],
            "sampler_name": sampler["sampler_name"],
            "scheduler": sampler["scheduler"],
            "denoise": sampler["denoise"],
            "filename_prefix": filename_prefix,
            "positive_prompt": content["positive"],
            "negative_prompt": content["negative"],
            "rendering_positive": rendering["positive"],
            "rendering_negative": rendering["negative"],
            "lineart": lineart,
            "pose_control": engine_plan.get("pose_control"),
            "loras": engine_plan.get("loras"),
        },
        "comfyui": {
            "prompt_id": result.prompt_id,
            "remote_filename": result.remote_filename,
            "remote_subfolder": result.remote_subfolder,
            "remote_type": result.remote_type,
        },
        "output": {
            "path": str(result.output_path),
            "sha256": _sha256_file(result.output_path),
            "size": result.output_path.stat().st_size,
        },
        "qa": {
            "status": "unreviewed",
        },
        "request": request,
        "shared_rendering": shared_rendering,
        "learned_assets": [],
        "generation_plan": {
            "path": str(plan_path),
            "sha256": _sha256_file(plan_path),
            "mode": "text2img",
            "domain": "free",
            "engine_id": engine_plan.get("engine_id"),
        },
    }


def run_free_generation(
    root: Path,
    request: dict[str, Any],
    config: dict[str, Any],
) -> FreeGenerationResult:
    if request.get("generation_domain") != "free":
        raise ValueError("run_free_generation requires generation_domain=free")
    if request.get("target_mode") not in {"free_text2img", "generic_text2img"}:
        raise ValueError("run_free_generation requires a FREE target_mode")

    prompt_input = request.get("prompt_input")
    if not isinstance(prompt_input, dict):
        raise ValueError("request.prompt_input must be an object")
    content_positive = prompt_input.get("positive")
    content_negative = prompt_input.get("negative")
    if not isinstance(content_positive, str) or not content_positive.strip():
        raise ValueError("request.prompt_input.positive must be a non-empty string")
    if content_negative is not None and not isinstance(content_negative, str):
        raise ValueError("request.prompt_input.negative must be string or null")

    paths = config.get("paths")
    comfyui = config.get("comfyui")
    if not isinstance(paths, dict) or not isinstance(comfyui, dict):
        raise ValueError("config.paths and config.comfyui must be objects")

    cache_root = _resolve_runtime_path(root, paths.get("cache"), "cache")
    outputs_root = _resolve_runtime_path(root, paths.get("outputs"), "outputs")
    database_path = _resolve_runtime_path(root, paths.get("database"), "database")

    base_url = comfyui.get("base_url")
    if not isinstance(base_url, str) or not base_url.strip():
        raise ValueError("config.comfyui.base_url must be a non-empty string")
    request_timeout = float(comfyui.get("timeout_seconds", 5))
    generation_timeout = float(comfyui.get("generation_timeout_seconds", 180))

    profile_path = root / FREE_PROFILE_PATH
    rendering_path = root / SHARED_RENDERING_PATH
    lineart_path = root / LINEART_PROFILE_PATH
    profile = _load_json(profile_path)
    shared_rendering = _load_json(rendering_path)
    lineart_profile = _load_json(lineart_path)

    workflow = profile.get("workflow")
    if not isinstance(workflow, dict):
        raise ValueError("FREE profile.workflow must be an object")
    workflow = dict(workflow)

    generation = shared_rendering.get("generation")
    if not isinstance(generation, dict):
        raise ValueError("shared rendering generation must be an object")

    checkpoint_name, lineart_enabled, lineart_strength, pose_request = _resolve_free_controls(
        root=root,
        prompt_input=prompt_input,
        default_checkpoint=generation.get("checkpoint"),
        lineart_profile=lineart_profile,
    )

    workflow["checkpoint"] = checkpoint_name
    for key in ("steps", "cfg", "sampler_name", "scheduler"):
        workflow[key] = generation[key]
    workflow["denoise"] = 1.0

    resolved_pose_control: dict[str, Any] | None = None
    if pose_request is not None:
        source_path = pose_request["source_path"]
        suffix = source_path.suffix.lower()
        remote_name = f"LOCAL_RAG_POSE_{pose_request['source_sha256'][:12]}{suffix}"
        uploaded_name = upload_input_image(
            base_url=base_url,
            source=source_path,
            remote_name=remote_name,
            timeout_seconds=max(request_timeout, 30.0),
        )
        resolved_pose_control = {
            "enabled": True,
            "backend": "dwpose",
            "source": {
                "local_path": str(source_path),
                "input_name": uploaded_name,
                "sha256": pose_request["source_sha256"],
            },
            "preprocessor": {
                "detect_hand": pose_request["detect_hand"],
                "detect_body": pose_request["detect_body"],
                "detect_face": pose_request["detect_face"],
                "resolution": pose_request["resolution"],
                "bbox_detector": "yolox_l.onnx",
                "pose_estimator": "dw-ll_ucoco_384_bs5.torchscript.pt",
                "scale_stick_for_xinsr_cn": pose_request["scale_stick_for_xinsr_cn"],
            },
            "controlnet": {
                "model": pose_request["model"],
                "strength": pose_request["strength"],
                "start_percent": pose_request["start_percent"],
                "end_percent": pose_request["end_percent"],
            },
        }

    engine_plan = build_free_generation_engine_plan(
        content_positive=content_positive,
        content_negative=content_negative,
        workflow=workflow,
        shared_rendering=shared_rendering,
        lineart_profile=lineart_profile,
        lineart_enabled=lineart_enabled,
        lineart_strength=lineart_strength,
        pose_control=resolved_pose_control,
    )

    options = request.get("options")
    seed_value = options.get("seed") if isinstance(options, dict) else None
    if seed_value is None:
        seed_value = workflow.get("seed", 1)
    if not isinstance(seed_value, int) or isinstance(seed_value, bool) or seed_value < 0:
        raise ValueError("FREE seed must be a non-negative integer")

    request_id = request.get("request_id")
    if not isinstance(request_id, str) or not request_id:
        raise ValueError("request.request_id must be a non-empty string")

    plan_document = dict(engine_plan)
    plan_document["request_context"] = {
        "request_id": request_id,
        "source": request.get("source"),
        "user_text": request.get("user_text"),
        "prompt_input": prompt_input,
        "generation_domain": "free",
        "target_mode": request.get("target_mode"),
        "generation_mode": "free_text2img_v2",
        "learning_selection": request.get("learning"),
        "learned_assets": [],
        "learned_asset_ids": [],
    }

    plan_dir = cache_root / "requests"
    plan_dir.mkdir(parents=True, exist_ok=True)
    plan_path = plan_dir / f"{request_id}.free-generation.json"
    plan_path.write_bytes(_canonical_json_bytes(plan_document) + b"\n")

    filename_prefix = "LOCAL_RAG_FREE"
    compiled = compile_free_generation(
        root,
        plan_document,
        cache_root,
        seed=seed_value,
        filename_prefix=filename_prefix,
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

    manifest_payload = _build_manifest(
        request=request,
        engine_plan=engine_plan,
        plan_path=plan_path,
        profile_path=profile_path,
        profile=profile,
        shared_rendering=shared_rendering,
        compiled=compiled,
        result=result,
        generation_id=generation_id,
        seed=seed_value,
        filename_prefix=filename_prefix,
    )
    manifest_path = run_dir / "manifest.json"
    manifest_sha256 = write_manifest(manifest_path, manifest_payload)
    import_manifest(database_path, manifest_path)

    return FreeGenerationResult(
        request=request,
        generation_plan_path=plan_path,
        generation_id=generation_id,
        prompt_id=result.prompt_id,
        output_path=result.output_path,
        output_sha256=manifest_payload["output"]["sha256"],
        manifest_path=manifest_path,
        manifest_sha256=manifest_sha256,
        database_path=database_path,
        generation_mode="free_text2img_v2",
        learned_asset_ids=(),
    )
