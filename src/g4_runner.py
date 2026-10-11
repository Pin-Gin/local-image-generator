from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from comfyui_client import run_workflow_and_download, upload_input_image
from compiler import compile_generation
from manifest import build_generation_manifest, write_manifest


def repository_root() -> Path:
    return Path(__file__).resolve().parent.parent


def main() -> int:
    root = repository_root()
    config_path = root / "config" / "app.example.json"
    profile_path = root / "profiles" / "yura_working_master_g3.json"

    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
        comfyui = config["comfyui"]
        base_url = comfyui["base_url"]
        request_timeout = float(comfyui.get("timeout_seconds", 5))
        generation_timeout = float(comfyui.get("generation_timeout_seconds", 180))
        cache_root = root / config["paths"]["cache"]
        outputs_root = root / config["paths"]["outputs"]

        compiled = compile_generation(root, profile_path, cache_root)
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        master_path = profile["authority"]["master_image_path"]
        master_file = compiled.authority.files[master_path]

        remote_name = master_file.local_path.name
        print(f"[G4:UPLOAD] source={master_file.local_path}")
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

        print(f"[G4:SUBMIT] generation_id={generation_id}")
        result = run_workflow_and_download(
            base_url=base_url,
            workflow=compiled.compiled_workflow,
            output_dir=run_dir,
            request_timeout_seconds=request_timeout,
            generation_timeout_seconds=generation_timeout,
        )

        manifest_payload = build_generation_manifest(compiled, result, result.output_path)
        manifest_payload["generation_id"] = generation_id
        manifest_path = run_dir / "manifest.json"
        manifest_sha256 = write_manifest(manifest_path, manifest_payload)
    except (OSError, KeyError, json.JSONDecodeError, ValueError, RuntimeError) as exc:
        print(f"[G4:FAIL] {exc}", file=sys.stderr)
        return 5

    print("[G4:OK]")
    print(f"generation_id={generation_id}")
    print(f"prompt_id={result.prompt_id}")
    print(f"output={result.output_path}")
    print(f"output_sha256={manifest_payload['output']['sha256']}")
    print(f"manifest={manifest_path}")
    print(f"manifest_sha256={manifest_sha256}")
    print(f"authority_commit={compiled.authority.commit_sha}")
    print(f"profile_sha256={compiled.profile_sha256}")
    print(f"compiled_workflow_sha256={compiled.compiled_workflow_sha256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
