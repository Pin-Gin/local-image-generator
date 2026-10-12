from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from json_parts import validate_json_part


EXPECTED_ROLES = {
    "character_body",
    "outfit_prop",
    "expression_face",
    "camera_composition",
    "background_scene",
}


def main() -> int:
    template_dir = ROOT / "learning/local-ai/templates/free"
    discovered: set[str] = set()

    for path in sorted(template_dir.glob("*.template.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        validated = validate_json_part(document)
        role = validated["part_type"]
        if role not in EXPECTED_ROLES:
            raise AssertionError(f"unexpected FREE template role: {role} ({path})")
        structured = validated["payload"].get("structured")
        if not isinstance(structured, dict):
            raise AssertionError(f"structured payload missing: {path}")
        application = structured.get("application")
        if not isinstance(application, dict):
            raise AssertionError(f"application contract missing: {path}")
        if application.get("mode") != "delta":
            raise AssertionError(f"template must default to delta mode: {path}")
        if application.get("preserve_unspecified") is not True:
            raise AssertionError(f"template must preserve unspecified details: {path}")
        if not validated["payload"]["generation"]["positive"].strip():
            raise AssertionError(f"positive generation text missing: {path}")
        discovered.add(role)
        print(f"[FREE-TEMPLATE:ROLE:OK] {role}")

    if discovered != EXPECTED_ROLES:
        raise AssertionError(
            f"FREE role template set mismatch: expected={sorted(EXPECTED_ROLES)} actual={sorted(discovered)}"
        )
    print("[FREE-TEMPLATE:SET:OK] five bounded roles")

    rendering_path = ROOT / "shared/rendering/matte_dimensional_anime.json"
    rendering = json.loads(rendering_path.read_text(encoding="utf-8"))
    if rendering.get("schema_version") != 1:
        raise AssertionError("rendering schema_version mismatch")
    if rendering.get("rendering_id") != "matte-dimensional-anime-v1":
        raise AssertionError("rendering_id changed unexpectedly")
    if int(rendering.get("rendering_version", 0)) < 4:
        raise AssertionError("rendering authority must be version 4 or later")

    authority = rendering.get("authority_contract")
    if not isinstance(authority, dict):
        raise AssertionError("rendering authority_contract missing")
    if authority.get("role") != "drawing_method":
        raise AssertionError("rendering authority role must be drawing_method")
    if authority.get("priority") != "highest_within_rendering_domain":
        raise AssertionError("rendering priority contract mismatch")

    conditioning = rendering.get("conditioning")
    if not isinstance(conditioning, dict):
        raise AssertionError("rendering conditioning contract missing")
    default_strength = conditioning.get("default_strength")
    if not isinstance(default_strength, (int, float)) or isinstance(default_strength, bool):
        raise AssertionError("rendering default_strength must be numeric")
    if not (1.0 < float(default_strength) <= 2.0):
        raise AssertionError("rendering default_strength must express stronger-than-neutral authority")

    target = rendering.get("target_definition")
    required_targets = {
        "anime_foundation",
        "real_anime_form",
        "matte_material_response",
        "dimensional_shading",
        "depth_and_space",
        "slight_3d_anime_dimensionality",
        "edge_support",
    }
    if not isinstance(target, dict) or not required_targets.issubset(target):
        raise AssertionError("rendering target_definition is incomplete")

    prompt = rendering.get("prompt")
    if not isinstance(prompt, dict) or not str(prompt.get("positive", "")).strip():
        raise AssertionError("rendering positive prompt missing")
    if not str(prompt.get("negative", "")).strip():
        raise AssertionError("rendering negative prompt missing")

    lora = rendering.get("lora")
    if not isinstance(lora, dict) or lora.get("enabled") is not False:
        raise AssertionError("Rendering LoRA must remain disabled until explicitly revalidated")

    print("[RENDERING-AUTHORITY:CONTRACT:OK]")
    print(f"[RENDERING-AUTHORITY:DEFAULT-STRENGTH] {default_strength}")
    print("[RENDERING-AUTHORITY:LORA:OFF]")
    print("[FREE-AUTHORITY-TEMPLATES:TEST:OK]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
