from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from local_ai_client import LocalAIClient


REGISTRY_RELATIVE_PATH = Path("learning/registry/registry.json")
SUPPORTED_DOMAINS = {"free", "memoriela"}
SUPPORTED_SELECTION_MODES = {"always", "ai", "disabled"}
SUPPORTED_RUNTIME_TYPES = {"shared_rendering", "prompt", "lora"}


@dataclass(frozen=True)
class LearnedAssetSelection:
    registry_version: int
    selected_asset_ids: tuple[str, ...]
    selector_model: str
    reason: str
    selector_role: str = "generate"

    def to_request_payload(self) -> dict[str, Any]:
        return {
            "registry_version": self.registry_version,
            "selector": "local-ai",
            "selector_role": self.selector_role,
            "selector_model": self.selector_model,
            "selected_asset_ids": list(self.selected_asset_ids),
            "reason": self.reason,
        }


def resolve_registry_path(resource_root: Path) -> Path:
    """Prefer the mutable repository registry; fall back to bundled data."""
    candidates: list[Path] = []

    cwd = Path.cwd().resolve()
    candidates.append(cwd / REGISTRY_RELATIVE_PATH)

    if getattr(sys, "frozen", False):
        executable = Path(sys.executable).resolve()
        for ancestor in executable.parents:
            candidates.append(ancestor / REGISTRY_RELATIVE_PATH)

    candidates.append(resource_root.resolve() / REGISTRY_RELATIVE_PATH)

    seen: set[Path] = set()
    for candidate in candidates:
        candidate = candidate.resolve()
        if candidate in seen:
            continue
        seen.add(candidate)
        if candidate.is_file():
            return candidate

    searched = ", ".join(str(path) for path in seen)
    raise FileNotFoundError(f"learning registry not found; searched: {searched}")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"failed to load learning registry: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("learning registry root must be an object")
    return payload


def _validate_string_list(value: Any, field_name: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{field_name} must be a non-empty array")
    result: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{field_name}[{index}] must be a non-empty string")
        result.append(item.strip())
    return result


def validate_registry(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("schema_version") != 1:
        raise ValueError("learning registry schema_version must be 1")

    registry_version = payload.get("registry_version")
    if not isinstance(registry_version, int) or isinstance(registry_version, bool) or registry_version < 1:
        raise ValueError("learning registry registry_version must be an integer >= 1")

    assets = payload.get("assets")
    if not isinstance(assets, list):
        raise ValueError("learning registry assets must be an array")

    normalized_assets: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, raw_asset in enumerate(assets):
        if not isinstance(raw_asset, dict):
            raise ValueError(f"learning registry assets[{index}] must be an object")

        asset_id = raw_asset.get("asset_id")
        enabled = raw_asset.get("enabled")
        selection_mode = raw_asset.get("selection_mode")
        domains = raw_asset.get("domains")
        category = raw_asset.get("category")
        description = raw_asset.get("description")
        concepts = raw_asset.get("concepts")
        runtime = raw_asset.get("runtime")

        if not isinstance(asset_id, str) or not asset_id.strip():
            raise ValueError(f"learning registry assets[{index}].asset_id must be a non-empty string")
        asset_id = asset_id.strip()
        if asset_id in seen_ids:
            raise ValueError(f"duplicate learning registry asset_id: {asset_id}")
        seen_ids.add(asset_id)

        if not isinstance(enabled, bool):
            raise ValueError(f"learning registry asset {asset_id}.enabled must be boolean")
        if selection_mode not in SUPPORTED_SELECTION_MODES:
            raise ValueError(
                f"learning registry asset {asset_id}.selection_mode must be one of "
                f"{sorted(SUPPORTED_SELECTION_MODES)}"
            )

        normalized_domains = _validate_string_list(domains, f"asset {asset_id}.domains")
        invalid_domains = [domain for domain in normalized_domains if domain not in SUPPORTED_DOMAINS]
        if invalid_domains:
            raise ValueError(f"learning registry asset {asset_id} has invalid domains: {invalid_domains}")

        if not isinstance(category, str) or not category.strip():
            raise ValueError(f"learning registry asset {asset_id}.category must be a non-empty string")
        if not isinstance(description, str) or not description.strip():
            raise ValueError(f"learning registry asset {asset_id}.description must be a non-empty string")
        normalized_concepts = _validate_string_list(concepts, f"asset {asset_id}.concepts")

        if not isinstance(runtime, dict):
            raise ValueError(f"learning registry asset {asset_id}.runtime must be an object")
        runtime_type = runtime.get("type")
        if runtime_type not in SUPPORTED_RUNTIME_TYPES:
            raise ValueError(
                f"learning registry asset {asset_id}.runtime.type must be one of "
                f"{sorted(SUPPORTED_RUNTIME_TYPES)}"
            )

        normalized_runtime: dict[str, Any] = {"type": runtime_type}
        if runtime_type == "prompt":
            positive = runtime.get("positive", "")
            negative = runtime.get("negative", "")
            if not isinstance(positive, str) or not isinstance(negative, str):
                raise ValueError(f"learning registry prompt asset {asset_id} prompt values must be strings")
            if not positive.strip() and not negative.strip():
                raise ValueError(f"learning registry prompt asset {asset_id} must provide positive or negative")
            normalized_runtime["positive"] = positive.strip()
            normalized_runtime["negative"] = negative.strip()
        elif runtime_type == "lora":
            lora_name = runtime.get("lora_name")
            strength_model = runtime.get("strength_model")
            strength_clip = runtime.get("strength_clip")
            trigger = runtime.get("trigger", "")
            if not isinstance(lora_name, str) or not lora_name.strip():
                raise ValueError(f"learning registry lora asset {asset_id}.lora_name must be non-empty")
            if not isinstance(strength_model, (int, float)) or isinstance(strength_model, bool):
                raise ValueError(f"learning registry lora asset {asset_id}.strength_model must be numeric")
            if not isinstance(strength_clip, (int, float)) or isinstance(strength_clip, bool):
                raise ValueError(f"learning registry lora asset {asset_id}.strength_clip must be numeric")
            if not isinstance(trigger, str):
                raise ValueError(f"learning registry lora asset {asset_id}.trigger must be a string")
            normalized_runtime.update(
                {
                    "lora_name": lora_name.strip(),
                    "strength_model": float(strength_model),
                    "strength_clip": float(strength_clip),
                    "trigger": trigger.strip(),
                }
            )

        normalized_assets.append(
            {
                "asset_id": asset_id,
                "enabled": enabled,
                "selection_mode": selection_mode,
                "domains": normalized_domains,
                "category": category.strip(),
                "description": description.strip(),
                "concepts": normalized_concepts,
                "runtime": normalized_runtime,
            }
        )

    return {
        "schema_version": 1,
        "registry_version": registry_version,
        "assets": normalized_assets,
    }


def load_registry(path: Path) -> dict[str, Any]:
    return validate_registry(_read_json(path))


def registry_asset_map(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {asset["asset_id"]: asset for asset in registry["assets"]}


def eligible_ai_assets(registry: dict[str, Any], generation_domain: str) -> list[dict[str, Any]]:
    if generation_domain not in SUPPORTED_DOMAINS:
        raise ValueError(f"unsupported generation domain for learning registry: {generation_domain}")
    return [
        asset
        for asset in registry["assets"]
        if asset["enabled"]
        and asset["selection_mode"] == "ai"
        and generation_domain in asset["domains"]
    ]


def _extract_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()

    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("local AI asset selector did not return a JSON object")
        try:
            payload = json.loads(stripped[start : end + 1])
        except json.JSONDecodeError as exc:
            raise ValueError("local AI asset selector returned invalid JSON") from exc

    if not isinstance(payload, dict):
        raise ValueError("local AI asset selector JSON root must be an object")
    return payload


def _build_selector_prompt(
    user_text: str,
    generation_domain: str,
    assets: list[dict[str, Any]],
) -> str:
    compact_assets = [
        {
            "asset_id": asset["asset_id"],
            "category": asset["category"],
            "description": asset["description"],
            "concepts": asset["concepts"],
        }
        for asset in assets
    ]
    return (
        "This is a PRE-GENERATION learned-asset selection task. "
        "Do not rewrite, expand, or reinterpret the user's generation request. "
        "Choose only asset IDs whose learned concept is explicitly relevant to the request. "
        "Never invent an asset ID. If nothing applies, select none. "
        "Return JSON only, exactly in this shape: "
        '{"selected_asset_ids":["asset-id"],"reason":"short explanation"}.\n\n'
        f"generation_domain: {generation_domain}\n"
        f"user_request: {user_text}\n"
        "available_learned_assets:\n"
        f"{json.dumps(compact_assets, ensure_ascii=False, separators=(',', ':'))}"
    )


def select_assets_with_local_ai(
    client: LocalAIClient,
    registry: dict[str, Any],
    *,
    user_text: str,
    generation_domain: str,
) -> LearnedAssetSelection:
    if not isinstance(user_text, str) or not user_text.strip():
        raise ValueError("user_text must be a non-empty string for learned asset selection")

    assets = eligible_ai_assets(registry, generation_domain)
    prompt = _build_selector_prompt(user_text.strip(), generation_domain, assets)
    result = client.chat("generate", prompt, history=[], json_mode=True)
    payload = _extract_json_object(result.content)

    selected = payload.get("selected_asset_ids")
    if not isinstance(selected, list):
        raise ValueError("local AI asset selector selected_asset_ids must be an array")
    reason = payload.get("reason", "")
    if not isinstance(reason, str):
        raise ValueError("local AI asset selector reason must be a string")

    eligible_ids = {asset["asset_id"] for asset in assets}
    normalized: list[str] = []
    for index, asset_id in enumerate(selected):
        if not isinstance(asset_id, str) or not asset_id.strip():
            raise ValueError(f"local AI asset selector selected_asset_ids[{index}] must be a string")
        asset_id = asset_id.strip()
        if asset_id not in eligible_ids:
            raise ValueError(f"local AI asset selector returned unknown/ineligible asset_id: {asset_id}")
        if asset_id not in normalized:
            normalized.append(asset_id)

    return LearnedAssetSelection(
        registry_version=registry["registry_version"],
        selected_asset_ids=tuple(normalized),
        selector_model=result.model,
        reason=reason.strip(),
    )


def resolve_selected_assets(
    registry: dict[str, Any],
    *,
    selected_asset_ids: list[str],
    generation_domain: str,
) -> list[dict[str, Any]]:
    if generation_domain not in SUPPORTED_DOMAINS:
        raise ValueError(f"unsupported generation domain for learned assets: {generation_domain}")
    asset_map = registry_asset_map(registry)
    resolved: list[dict[str, Any]] = []
    for asset_id in selected_asset_ids:
        if not isinstance(asset_id, str) or not asset_id:
            raise ValueError("selected learned asset IDs must be non-empty strings")
        asset = asset_map.get(asset_id)
        if asset is None:
            raise ValueError(f"selected learned asset is not registered: {asset_id}")
        if not asset["enabled"] or asset["selection_mode"] != "ai":
            raise ValueError(f"selected learned asset is not active for AI selection: {asset_id}")
        if generation_domain not in asset["domains"]:
            raise ValueError(f"selected learned asset is not valid for {generation_domain}: {asset_id}")
        resolved.append(asset)
    return resolved
