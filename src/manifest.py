from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from comfyui_client import ComfyUIGenerationResult
from compiler import CompiledGeneration


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_generation_manifest(
    compiled: CompiledGeneration,
    result: ComfyUIGenerationResult,
    output_path: Path,
) -> dict[str, Any]:
    profile = json.loads(compiled.profile_path.read_text(encoding="utf-8"))
    workflow_cfg = profile.get("workflow", {})
    prompt_cfg = profile.get("prompt", {})

    authority_payload: dict[str, Any] = {}
    if compiled.authority is not None:
        authority_files = []
        for source_path, item in compiled.authority.files.items():
            authority_files.append(
                {
                    "path": source_path,
                    "git_blob_sha": item.git_blob_sha,
                    "sha256": item.sha256,
                    "size": item.size,
                }
            )
        authority_payload = {
            "repository": compiled.authority.repository,
            "branch": compiled.authority.branch,
            "commit_sha": compiled.authority.commit_sha,
            "expected_master_sha256": compiled.authority.expected_master_sha256,
            "files": authority_files,
        }

    manifest = {
        "schema_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "generated",
        "profile": {
            "path": str(compiled.profile_path),
            "sha256": compiled.profile_sha256,
            "profile_id": profile.get("profile_id"),
            "profile_version": profile.get("profile_version"),
            "character": profile.get("character"),
            "authority_mode": profile.get("authority_mode"),
        },
        "authority": authority_payload,
        "workflow": {
            "template_path": str(compiled.workflow_template_path),
            "template_sha256": compiled.workflow_template_sha256,
            "compiled_path": str(compiled.compiled_workflow_path),
            "compiled_sha256": compiled.compiled_workflow_sha256,
        },
        "generation": {
            "checkpoint": workflow_cfg.get("checkpoint"),
            "seed": workflow_cfg.get("seed"),
            "steps": workflow_cfg.get("steps"),
            "cfg": workflow_cfg.get("cfg"),
            "sampler_name": workflow_cfg.get("sampler_name"),
            "scheduler": workflow_cfg.get("scheduler"),
            "denoise": workflow_cfg.get("denoise"),
            "filename_prefix": workflow_cfg.get("filename_prefix"),
            "positive_prompt": prompt_cfg.get("positive"),
            "negative_prompt": prompt_cfg.get("negative"),
        },
        "comfyui": {
            "prompt_id": result.prompt_id,
            "remote_filename": result.remote_filename,
            "remote_subfolder": result.remote_subfolder,
            "remote_type": result.remote_type,
        },
        "output": {
            "path": str(output_path),
            "sha256": sha256_file(output_path),
            "size": output_path.stat().st_size,
        },
        "qa": {
            "status": "unreviewed"
        },
    }
    return manifest


def write_manifest(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()
