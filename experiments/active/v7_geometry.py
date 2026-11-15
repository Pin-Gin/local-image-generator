"""V7 independently compiled OpenPose/ControlNet geometry stage.

Uses the existing SDXL OpenPose ControlNet from v1-v3 ONLY as a structural
pose-canvas generator, not as the final identity/style engine.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class GeometryError(ValueError):
    pass


def request_from_text(text: str) -> dict[str, Any]:
    from free_text_pose_poc import classify_request
    try:
        request = classify_request(text)
    except Exception as ex:
        raise GeometryError(f"POSE_PARSE_FAILED: {ex}") from ex
    if request.get("interpretation", {}).get("coverage") != "COMPLETE_FOR_POC":
        raise GeometryError("POSE_PARSE_INCOMPLETE: refusing to discard modifiers")
    if request.get("deltas", {}).get("clothing") or request.get("deltas", {}).get("scene"):
        raise GeometryError("USER_DELTA_UNSUPPORTED: outfit/scene override not supported by v7")
    return request


def pose_phrase(pose_id: str) -> str:
    mapping = {
        "seated_m": "front view of a single adult woman seated on the floor, hips resting on rug, both knees bent apart outward symmetrically, feet inward, M-shaped bent-leg floor sitting pose, NOT sitting cross-legged",
        "arms_down": "front view, a single adult woman standing upright, arms naturally at the sides",
        "arms_out": "front view, a single adult woman standing upright, both arms extended horizontally",
    }
    if pose_id not in mapping:
        raise GeometryError("POSE_NOT_SUPPORTED")
    return mapping[pose_id]


def make_stage1_graph(source_graph: dict[str, Any], pose_name: str, pose_id: str,
                      *, seed: int = 975311, control_strength: float = 1.2) -> dict[str, Any]:
    if not isinstance(seed, int) or seed < 0 or not (0.2 <= control_strength <= 2):
        raise GeometryError("GEOMETRY_ARGUMENT_INVALID")
    required = ("1", "2", "3", "4", "5", "6", "7", "8", "9", "20", "22", "23")
    if any(key not in source_graph for key in required):
        raise GeometryError("POSE_TEMPLATE_MISSING_NODES")
    # Node whitelist intentionally isolates stage1 from old identity adapters.
    g = {key: json.loads(json.dumps(source_graph[key])) for key in required}
    if g["1"].get("class_type") != "CheckpointLoaderSimple" or g["23"].get("class_type") != "ControlNetApplyAdvanced":
        raise GeometryError("POSE_TEMPLATE_WRONG_NODE_TYPES")
    g["20"]["inputs"]["image"] = pose_name
    g["3"]["inputs"]["text"] = (
        pose_phrase(pose_id) + ", full body, entire figure visible, consistent anatomy, "
        "simple neutral sleeveless top and shorts, no chair or bed, soft matte anime illustration"
    )
    g["4"]["inputs"]["text"] = "anime body geometry study, anatomical limb joints, soft matte illustration"
    g["6"]["inputs"]["text"] = "wrong pose, standing when seated, cross-legged when knees apart, chair, bed, extra legs, limbs cropped, anatomy errors"
    g["7"]["inputs"].update({"model": ["1", 0], "positive": ["23", 0],
                               "negative": ["23", 1], "seed": seed, "steps": 28,
                               "cfg": 5.0, "denoise": 1.0})
    g["23"]["inputs"].update({"strength": float(control_strength),
                                "start_percent": 0.0, "end_percent": 1.0})
    g["9"]["inputs"]["filename_prefix"] = "LOCAL_RAG_V7_STAGE1_GEOMETRY"
    return g


def load_legacy_graph(path: Path) -> tuple[dict[str, Any], str, str]:
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    try:
        assert d["20"]["class_type"] == "LoadImage"
        assert d["30"]["class_type"] == "LoadImage"
        return d, d["30"]["inputs"]["image"], d["20"]["inputs"]["image"]
    except (AssertionError, KeyError, TypeError) as e:
        raise GeometryError("SOURCE_WORKFLOW_INCOMPATIBLE") from e
