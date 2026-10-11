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
    authority: AuthorityBundle
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


def compile_generation(root: Path, profile_path: Path, cache_root: Path) -> CompiledGeneration:
    profile = _read_json(profile_path)
    profile_sha256 = _sha256_file(profile_path)

    authority = resolve_authority_bundle(profile, cache_root)

    workflow_cfg = profile.get("workflow")
    prompt_cfg = profile.get("prompt")
    if not isinstance(workflow_cfg, dict):
        raise ValueError("profile.workflow must be an object")
    if not isinstance(prompt_cfg, dict):
        raise ValueError("profile.prompt must be an object")

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

    master_path = profile["authority"]["master_image_path"]
    master_file = authority.files[master_path]

    compiled = copy.deepcopy(workflow)
    try:
        compiled["1"]["inputs"]["ckpt_name"] = workflow_cfg["checkpoint"]
        compiled["2"]["inputs"]["image"] = master_file.local_path.name
        compiled["4"]["inputs"]["text"] = positive
        compiled["5"]["inputs"]["text"] = negative
        sampler = compiled["6"]["inputs"]
        sampler["seed"] = workflow_cfg["seed"]
        sampler["steps"] = workflow_cfg["steps"]
        sampler["cfg"] = workflow_cfg["cfg"]
        sampler["sampler_name"] = workflow_cfg["sampler_name"]
        sampler["scheduler"] = workflow_cfg["scheduler"]
        sampler["denoise"] = workflow_cfg["denoise"]
        compiled["8"]["inputs"]["filename_prefix"] = workflow_cfg["filename_prefix"]
    except (KeyError, TypeError) as exc:
        raise RuntimeError("Workflow template does not match the expected G3 node contract") from exc

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
