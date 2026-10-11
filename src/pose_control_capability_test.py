from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
BASE_URL = "http://127.0.0.1:8188"
CONTROLNET_ROOT = ROOT / "models" / "controlnet"
CONTROLNET_EXTENSIONS = {".safetensors", ".ckpt", ".pth", ".pt"}


def _fetch_object_info() -> dict[str, Any]:
    request = urllib.request.Request(
        f"{BASE_URL}/object_info",
        headers={"Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=10.0) as response:
            raw = response.read()
    except urllib.error.URLError as exc:
        raise RuntimeError(f"ComfyUI connection failed: {exc.reason}") from exc
    except TimeoutError as exc:
        raise RuntimeError("ComfyUI /object_info timed out") from exc

    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("ComfyUI /object_info returned invalid JSON") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("ComfyUI /object_info root must be an object")
    return payload


def _list_controlnet_models() -> list[str]:
    if not CONTROLNET_ROOT.is_dir():
        return []
    names: list[str] = []
    for path in CONTROLNET_ROOT.rglob("*"):
        if path.is_file() and path.suffix.lower() in CONTROLNET_EXTENSIONS:
            names.append(path.relative_to(CONTROLNET_ROOT).as_posix())
    return sorted(names, key=str.casefold)


def _candidate_preprocessors(object_info: dict[str, Any]) -> list[str]:
    exact_candidates = {
        "DWPreprocessor",
        "DWPose_Preprocessor",
        "OpenposePreprocessor",
        "OpenPosePreprocessor",
    }
    found = [name for name in exact_candidates if name in object_info]
    if found:
        return sorted(found, key=str.casefold)

    fuzzy = [
        name
        for name in object_info
        if isinstance(name, str)
        and ("pose" in name.casefold() or "dw" in name.casefold())
        and "preprocess" in name.casefold()
    ]
    return sorted(set(fuzzy), key=str.casefold)


def _print_node_status(object_info: dict[str, Any], node_name: str, label: str) -> bool:
    if node_name in object_info:
        print(f"[POSE:{label}:OK] {node_name}")
        return True
    print(f"[POSE:{label}:MISSING] {node_name}")
    return False


def main() -> int:
    object_info = _fetch_object_info()

    loader_ok = _print_node_status(object_info, "ControlNetLoader", "CONTROLNET-LOADER")
    apply_ok = _print_node_status(object_info, "ControlNetApplyAdvanced", "CONTROLNET-APPLY")
    image_ok = _print_node_status(object_info, "LoadImage", "LOAD-IMAGE")

    preprocessors = _candidate_preprocessors(object_info)
    if preprocessors:
        print(f"[POSE:PREPROCESSOR:FOUND] {', '.join(preprocessors)}")
    else:
        print("[POSE:PREPROCESSOR:NONE]")

    models = _list_controlnet_models()
    print(f"[POSE:MODEL-CATALOG] count={len(models)}")
    for name in models:
        print(f"[POSE:MODEL] {name}")

    if loader_ok and apply_ok and image_ok and preprocessors and models:
        print("[POSE:CAPABILITY:READY]")
    else:
        print("[POSE:CAPABILITY:INCOMPLETE]")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
