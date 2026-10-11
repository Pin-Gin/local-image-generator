from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


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

    # Runtime directories may be created locally. The database entry is a file path,
    # so only its parent directory is created here.
    resolved["database"].parent.mkdir(parents=True, exist_ok=True)
    for key in ("profiles", "workflows", "cache", "outputs", "logs"):
        resolved[key].mkdir(parents=True, exist_ok=True)

    return resolved


def main() -> int:
    root = repository_root()

    parser = argparse.ArgumentParser(description="MEMORIELA Local Image Generator core bootstrap")
    parser.add_argument(
        "--config",
        default="config/app.example.json",
        help="Path to application config, relative to repository root unless absolute.",
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

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
