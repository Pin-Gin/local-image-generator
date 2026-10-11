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
    intent = parse_intent(text, dictionary_root or INTENT_ROOT)

    return {
        "schema_version": 1,
        "request_id": str(uuid.uuid4()),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "user_text": text,
        "profile_id": profile,
        "intent": intent,
        "options": {
            "reuse_policy": "PREFER_EXISTING",
            "seed_mode": resolved_seed_mode,
            "seed": resolved_seed,
        },
    }
