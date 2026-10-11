from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from comfyui_client import fetch_system_stats, run_workflow_and_download


REQUIRED_PATH_KEYS = (
    "database",
    "profiles",
    "workflows",
    "cache",
    "outputs",
    "logs",
)


def repository_root() -> Path:
    return Path(__file__).resolve().parent.parent


def load_config(config_path: Path) -> dict:
    with config_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_workflow(workflow_path: Path) -> dict:
    with workflow_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("workflow JSON must be an object")
    return payload


def validate_and_prepare_paths(root: Path, config: dict) -> dict[str, Path]:
    paths = config.get("paths")
    if not isinstance(paths, dict):
        raise ValueError("config.paths must be an object")

    resolved: dict[str, Path] = {}
    for key in REQUIRED_PATH_KEYS:
        raw_value = paths.get(key)
        if not isinstance(raw_value, str) or not raw_value.strip():
            raise ValueError(f"config.paths.{key} must be a non-empty string")

        path = (root / raw_value).resolve()
        resolved[key] = path

    resolved["database"].parent.mkdir(parents=True, exist_ok=True)
    for key in ("profiles", "workflows", "cache", "outputs", "logs"):
        resolved[key].mkdir(parents=True, exist_ok=True)

    return resolved


def print_bootstrap_summary(root: Path, config_path: Path, config: dict, resolved_paths: dict[str, Path]) -> None:
    app = config.get("app", {})
    comfyui = config.get("comfyui", {})

    print("[BOOTSTRAP:OK]")
    print(f"app={app.get('name', 'MEMORIELA Local Image Generator')}")
    print(f"environment={app.get('environment', 'development')}")
    print(f"repository_root={root}")
    print(f"config={config_path}")
    print(f"comfyui_base_url={comfyui.get('base_url', '')}")
    for key, path in resolved_paths.items():
        print(f"path.{key}={path}")


def print_comfyui_summary(payload: dict) -> None:
    system = payload.get("system") if isinstance(payload.get("system"), dict) else {}
    devices = payload.get("devices") if isinstance(payload.get("devices"), list) else []

    print("[COMFYUI:OK]")
    if system:
        if "os" in system:
            print(f"system.os={system['os']}")
        if "python_version" in system:
            print(f"system.python_version={system['python_version']}")
        if "pytorch_version" in system:
            print(f"system.pytorch_version={system['pytorch_version']}")

    print(f"devices.count={len(devices)}")
    for index, device in enumerate(devices):
        if not isinstance(device, dict):
            continue
        if "name" in device:
            print(f"device.{index}.name={device['name']}")
        if "type" in device:
            print(f"device.{index}.type={device['type']}")
        if "vram_total" in device:
            print(f"device.{index}.vram_total={device['vram_total']}")
        if "vram_free" in device:
            print(f"device.{index}.vram_free={device['vram_free']}")


def main() -> int:
    root = repository_root()

    parser = argparse.ArgumentParser(description="MEMORIELA Local Image Generator core bootstrap")
    parser.add_argument(
        "--config",
        default="config/app.example.json",
        help="Path to application config, relative to repository root unless absolute.",
    )
    parser.add_argument(
        "--check-comfyui",
        action="store_true",
        help="After bootstrap, verify ComfyUI /system_stats connectivity.",
    )
    parser.add_argument(
        "--run-g2-smoke",
        action="store_true",
        help="Run the standard G2 smoke-test workflow, poll history, and download the generated image.",
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = root / config_path
    config_path = config_path.resolve()

    try:
        config = load_config(config_path)
        resolved_paths = validate_and_prepare_paths(root, config)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"[BOOTSTRAP:FAIL] {exc}", file=sys.stderr)
        return 1

    print_bootstrap_summary(root, config_path, config, resolved_paths)

    if not args.check_comfyui and not args.run_g2_smoke:
        return 0

    comfyui = config.get("comfyui")
    if not isinstance(comfyui, dict):
        print("[COMFYUI:FAIL] config.comfyui must be an object", file=sys.stderr)
        return 2

    base_url = comfyui.get("base_url")
    timeout_seconds = comfyui.get("timeout_seconds", 5)
    generation_timeout_seconds = comfyui.get("generation_timeout_seconds", 180)

    if not isinstance(base_url, str):
        print("[COMFYUI:FAIL] config.comfyui.base_url must be a string", file=sys.stderr)
        return 2
    if not isinstance(timeout_seconds, (int, float)) or timeout_seconds <= 0:
        print("[COMFYUI:FAIL] config.comfyui.timeout_seconds must be a positive number", file=sys.stderr)
        return 2
    if not isinstance(generation_timeout_seconds, (int, float)) or generation_timeout_seconds <= 0:
        print("[COMFYUI:FAIL] config.comfyui.generation_timeout_seconds must be a positive number", file=sys.stderr)
        return 2

    try:
        status = fetch_system_stats(base_url, float(timeout_seconds))
    except (ValueError, RuntimeError) as exc:
        print(f"[COMFYUI:FAIL] {exc}", file=sys.stderr)
        return 2

    print(f"comfyui_endpoint={status.endpoint}")
    print_comfyui_summary(status.payload)

    if not args.run_g2_smoke:
        return 0

    workflow_path = resolved_paths["workflows"] / "sdxl_smoke_api.json"
    try:
        workflow = load_workflow(workflow_path)
        print(f"workflow={workflow_path}")
        print("[G2:SUBMIT]")
        result = run_workflow_and_download(
            base_url=base_url,
            workflow=workflow,
            output_dir=resolved_paths["outputs"],
            request_timeout_seconds=float(timeout_seconds),
            generation_timeout_seconds=float(generation_timeout_seconds),
        )
    except (OSError, json.JSONDecodeError, ValueError, RuntimeError) as exc:
        print(f"[G2:FAIL] {exc}", file=sys.stderr)
        return 3

    print("[G2:OK]")
    print(f"prompt_id={result.prompt_id}")
    print(f"remote_filename={result.remote_filename}")
    print(f"remote_subfolder={result.remote_subfolder}")
    print(f"remote_type={result.remote_type}")
    print(f"output={result.output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
