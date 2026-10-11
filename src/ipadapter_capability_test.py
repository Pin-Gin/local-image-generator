from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
BASE_URL = "http://127.0.0.1:8188"
IPADAPTER_ROOT = ROOT / "models" / "ipadapter"
CLIP_VISION_ROOT = ROOT / "models" / "clip_vision"
EXPECTED_IPADAPTER = "ip-adapter-plus_sdxl_vit-h.safetensors"
EXPECTED_CLIP_VISION = "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors"


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


def _choice_values(object_info: dict[str, Any], node_name: str, field: str) -> list[str]:
    node = object_info.get(node_name)
    if not isinstance(node, dict):
        return []
    inputs = node.get("input")
    if not isinstance(inputs, dict):
        return []
    required = inputs.get("required")
    if not isinstance(required, dict):
        return []
    spec = required.get(field)
    if not isinstance(spec, list) or not spec:
        return []
    values = spec[0]
    if not isinstance(values, list):
        return []
    return sorted({str(v).replace("\\", "/") for v in values}, key=str.casefold)


def _node_ok(object_info: dict[str, Any], node_name: str) -> bool:
    if node_name in object_info:
        print(f"[IPADAPTER:NODE:OK] {node_name}")
        return True
    print(f"[IPADAPTER:NODE:MISSING] {node_name}")
    return False


def _file_ok(path: Path, label: str) -> bool:
    if path.is_file():
        print(f"[IPADAPTER:{label}:FILE:OK] {path}")
        return True
    print(f"[IPADAPTER:{label}:FILE:MISSING] {path}")
    return False


def main() -> int:
    object_info = _fetch_object_info()

    unified_ok = _node_ok(object_info, "IPAdapterUnifiedLoader")
    advanced_ok = _node_ok(object_info, "IPAdapterAdvanced")
    model_loader_ok = _node_ok(object_info, "IPAdapterModelLoader")
    clip_loader_ok = _node_ok(object_info, "CLIPVisionLoader")
    load_image_ok = _node_ok(object_info, "LoadImage")

    ip_path = IPADAPTER_ROOT / EXPECTED_IPADAPTER
    clip_path = CLIP_VISION_ROOT / EXPECTED_CLIP_VISION
    ip_file_ok = _file_ok(ip_path, "MODEL")
    clip_file_ok = _file_ok(clip_path, "CLIP-VISION")

    ip_choices = _choice_values(object_info, "IPAdapterModelLoader", "ipadapter_file")
    expected_ip = EXPECTED_IPADAPTER.casefold()
    ip_api_ok = any(value.casefold().endswith(expected_ip) for value in ip_choices)
    if ip_api_ok:
        matched = next(value for value in ip_choices if value.casefold().endswith(expected_ip))
        print(f"[IPADAPTER:MODEL:COMFYUI:OK] {matched}")
    else:
        print(f"[IPADAPTER:MODEL:COMFYUI:MISSING] {EXPECTED_IPADAPTER}")

    clip_choices = _choice_values(object_info, "CLIPVisionLoader", "clip_name")
    expected_clip = EXPECTED_CLIP_VISION.casefold()
    clip_api_ok = any(value.casefold().endswith(expected_clip) for value in clip_choices)
    if clip_api_ok:
        matched = next(value for value in clip_choices if value.casefold().endswith(expected_clip))
        print(f"[IPADAPTER:CLIP-VISION:COMFYUI:OK] {matched}")
    else:
        print(f"[IPADAPTER:CLIP-VISION:COMFYUI:MISSING] {EXPECTED_CLIP_VISION}")

    pose_nodes_ok = all(name in object_info for name in ("DWPreprocessor", "ControlNetLoader", "ControlNetApplyAdvanced"))
    if pose_nodes_ok:
        print("[IPADAPTER:POSE-STACK:OK] DWPreprocessor + ControlNet")
    else:
        print("[IPADAPTER:POSE-STACK:MISSING]")

    ready = all(
        (
            unified_ok,
            advanced_ok,
            model_loader_ok,
            clip_loader_ok,
            load_image_ok,
            ip_file_ok,
            clip_file_ok,
            ip_api_ok,
            clip_api_ok,
            pose_nodes_ok,
        )
    )
    print("[IPADAPTER:CAPABILITY:READY]" if ready else "[IPADAPTER:CAPABILITY:INCOMPLETE]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
