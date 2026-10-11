from __future__ import annotations

import json
import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from intent_parser import parse_intent


ROOT = Path(__file__).resolve().parent.parent
INTENT_ROOT = ROOT / "intent"
MAX_SEED = (1 << 53) - 1
SEED_MODES = {"PROFILE", "RANDOM", "FIXED"}


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
            if key in {"negative", "profile_id", "seed", "seed_mode"}:
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


def _build_prompt_input(text: str) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        parsed_json = json.loads(text)
    except json.JSONDecodeError:
        parsed_json = None

    if not isinstance(parsed_json, dict):
        return (
            parse_intent(text, INTENT_ROOT),
            {
                "mode": "text",
                "positive": text,
                "negative": None,
                "json": None,
            },
        )

    prompt_value = parsed_json.get("prompt")
    positive = parsed_json.get("positive")
    negative = parsed_json.get("negative")

    if isinstance(prompt_value, dict):
        if positive is None:
            positive = prompt_value.get("positive")
        if negative is None:
            negative = prompt_value.get("negative")
    elif isinstance(prompt_value, str) and positive is None:
        positive = prompt_value

    if positive is not None and not isinstance(positive, str):
        raise ValueError("JSON positive/prompt must be a string when supplied")
    if negative is not None and not isinstance(negative, str):
        raise ValueError("JSON negative must be a string when supplied")

    if not isinstance(positive, str) or not positive.strip():
        positive = ", ".join(_flatten_json_prompt(parsed_json)).strip()
    if not positive:
        raise ValueError("JSON input does not contain usable generation content")

    intent_source = parsed_json.get("text")
    if not isinstance(intent_source, str) or not intent_source.strip():
        intent_source = positive

    return (
        parse_intent(intent_source, INTENT_ROOT),
        {
            "mode": "json",
            "positive": positive.strip(),
            "negative": negative.strip() if isinstance(negative, str) and negative.strip() else None,
            "json": parsed_json,
        },
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

    # Use the caller-supplied dictionary root for text mode while keeping JSON
    # handling deterministic and local.
    try:
        parsed_json = json.loads(text)
    except json.JSONDecodeError:
        parsed_json = None

    if isinstance(parsed_json, dict):
        intent, prompt_input = _build_prompt_input(text)
        if dictionary_root is not None:
            intent_source = prompt_input["positive"]
            intent = parse_intent(intent_source, dictionary_root)
    else:
        intent = parse_intent(text, dictionary_root or INTENT_ROOT)
        prompt_input = {
            "mode": "text",
            "positive": text,
            "negative": None,
            "json": None,
        }

    return {
        "schema_version": 1,
        "request_id": str(uuid.uuid4()),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "user_text": text,
        "profile_id": profile,
        "intent": intent,
        "prompt_input": prompt_input,
        "options": {
            "reuse_policy": "PREFER_EXISTING",
            "seed_mode": resolved_seed_mode,
            "seed": resolved_seed,
        },
    }
