from __future__ import annotations

import json
import secrets
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from intent_parser import parse_intent


def _resource_root() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


ROOT = _resource_root()
INTENT_ROOT = ROOT / "intent"
MAX_SEED = (1 << 53) - 1
SEED_MODES = {"PROFILE", "RANDOM", "FIXED"}
MEMORIELA_CHARACTER_IDS = {"YURA", "KANAME", "SHIORI", "YAMATO", "MIO"}


def list_profile_ids(profiles_root: Path) -> list[str]:
    profile_ids: list[str] = []
    for path in sorted(profiles_root.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        profile_id = payload.get("profile_id") if isinstance(payload, dict) else None
        if isinstance(profile_id, str) and profile_id:
            profile_ids.append(profile_id)
    return profile_ids


def _resolve_seed(seed_mode: str, seed: int | None) -> tuple[str, int | None]:
    mode = seed_mode.strip().upper()
    if mode not in SEED_MODES:
        raise ValueError("seed_mode must be PROFILE, RANDOM, or FIXED")

    if mode == "PROFILE":
        if seed is not None:
            raise ValueError("seed must be null when seed_mode=PROFILE")
        return mode, None

    if mode == "RANDOM":
        if seed is not None:
            raise ValueError("seed must be null when seed_mode=RANDOM")
        return mode, secrets.randbelow(MAX_SEED + 1)

    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError("seed must be an integer when seed_mode=FIXED")
    if seed < 0 or seed > MAX_SEED:
        raise ValueError(f"seed must be between 0 and {MAX_SEED}")
    return mode, seed


def _flatten_json_prompt(value: Any, prefix: str = "") -> list[str]:
    parts: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {
                "negative",
                "negative_prompt",
                "profile_id",
                "seed",
                "seed_mode",
                "target_mode",
                "generation_domain",
            }:
                continue
            label = f"{prefix} {key}".strip()
            parts.extend(_flatten_json_prompt(child, label))
    elif isinstance(value, list):
        for child in value:
            parts.extend(_flatten_json_prompt(child, prefix))
    elif value is not None and not isinstance(value, bool):
        text = str(value).strip()
        if text:
            parts.append(f"{prefix} {text}".strip())
    return parts


def _value_to_prompt_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        parts = [_value_to_prompt_text(item) for item in value]
        return ", ".join(part for part in parts if part)
    if isinstance(value, dict):
        parts = _flatten_json_prompt(value)
        return ", ".join(parts).strip()
    if value is None or isinstance(value, bool):
        return ""
    return str(value).strip()


def _find_first_key_value(value: Any, keys: set[str]) -> Any:
    if isinstance(value, dict):
        for key, child in value.items():
            if key.casefold() in keys:
                text = _value_to_prompt_text(child)
                if text:
                    return child
        for child in value.values():
            found = _find_first_key_value(child, keys)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_first_key_value(child, keys)
            if found is not None:
                return found
    return None


def _route_for_intent(intent: dict[str, Any]) -> tuple[str, str]:
    character = intent.get("character")
    if isinstance(character, str) and character in MEMORIELA_CHARACTER_IDS:
        return "memoriela", "memoriela_character"
    return "free", "free_text2img"


def _normalize_explicit_mode(value: Any) -> tuple[str, str] | None:
    if value is None:
        return None
    if value in {"free_text2img", "generic_text2img"}:
        return "free", "free_text2img"
    if value in {"memoriela_character", "yura_img2img"}:
        return "memoriela", "memoriela_character"
    raise ValueError("JSON target_mode must be free_text2img or memoriela_character")


def _build_prompt_input(text: str) -> tuple[dict[str, Any], dict[str, Any], str, str]:
    try:
        parsed_json = json.loads(text)
    except json.JSONDecodeError:
        parsed_json = None

    if not isinstance(parsed_json, dict):
        intent = parse_intent(text, INTENT_ROOT)
        generation_domain, target_mode = _route_for_intent(intent)
        return (
            intent,
            {
                "mode": "text",
                "positive": text,
                "negative": None,
                "json": None,
            },
            generation_domain,
            target_mode,
        )

    positive_value = parsed_json.get("positive")
    negative_value = parsed_json.get("negative")
    prompt_value = parsed_json.get("prompt")

    if positive_value is None and isinstance(prompt_value, dict):
        positive_value = prompt_value.get("positive")
    if negative_value is None and isinstance(prompt_value, dict):
        negative_value = prompt_value.get("negative")
    if positive_value is None and prompt_value is not None and not isinstance(prompt_value, dict):
        positive_value = prompt_value

    if positive_value is None:
        positive_value = _find_first_key_value(
            parsed_json,
            {"positive", "positive_prompt", "prompt", "text"},
        )
    if negative_value is None:
        negative_value = _find_first_key_value(
            parsed_json,
            {"negative", "negative_prompt"},
        )

    positive = _value_to_prompt_text(positive_value)
    negative = _value_to_prompt_text(negative_value)

    if not positive:
        positive = ", ".join(_flatten_json_prompt(parsed_json)).strip()
    if not positive:
        raise ValueError("JSON input does not contain usable generation content")

    intent_source = parsed_json.get("text")
    if not isinstance(intent_source, str) or not intent_source.strip():
        intent_source = positive
    intent = parse_intent(intent_source, INTENT_ROOT)

    explicit_route = _normalize_explicit_mode(parsed_json.get("target_mode"))
    if explicit_route is None:
        # JSON is FREE by default. MEMORIELA JSON must opt in explicitly.
        generation_domain, target_mode = "free", "free_text2img"
    else:
        generation_domain, target_mode = explicit_route

    return (
        intent,
        {
            "mode": "json",
            "positive": positive,
            "negative": negative or None,
            "json": parsed_json,
        },
        generation_domain,
        target_mode,
    )


def build_generation_request(
    user_text: str,
    profile_id: str,
    source: str = "chat_ui",
    dictionary_root: Path | None = None,
    seed_mode: str = "PROFILE",
    seed: int | None = None,
) -> dict[str, Any]:
    text = user_text.strip()
    profile = profile_id.strip()
    if not text:
        raise ValueError("user_text must not be empty")
    if not profile:
        raise ValueError("profile_id must not be empty")
    if source not in {"chat_ui", "cli", "api"}:
        raise ValueError("source must be chat_ui, cli, or api")

    resolved_seed_mode, resolved_seed = _resolve_seed(seed_mode, seed)
    intent, prompt_input, generation_domain, target_mode = _build_prompt_input(text)

    if dictionary_root is not None:
        if prompt_input["mode"] == "text":
            intent = parse_intent(text, dictionary_root)
            generation_domain, target_mode = _route_for_intent(intent)
        else:
            intent = parse_intent(prompt_input["positive"], dictionary_root)
            parsed_json = prompt_input.get("json")
            explicit_mode = parsed_json.get("target_mode") if isinstance(parsed_json, dict) else None
            explicit_route = _normalize_explicit_mode(explicit_mode)
            if explicit_route is None:
                generation_domain, target_mode = "free", "free_text2img"
            else:
                generation_domain, target_mode = explicit_route

    return {
        "schema_version": 1,
        "request_id": str(uuid.uuid4()),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "user_text": text,
        "profile_id": profile,
        "generation_domain": generation_domain,
        "intent": intent,
        "prompt_input": prompt_input,
        "target_mode": target_mode,
        "options": {
            "reuse_policy": "PREFER_EXISTING",
            "seed_mode": resolved_seed_mode,
            "seed": resolved_seed,
        },
    }
