from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from intent_parser import parse_intent


ROOT = Path(__file__).resolve().parent.parent
INTENT_ROOT = ROOT / "intent"


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


def build_generation_request(
    user_text: str,
    profile_id: str,
    source: str = "chat_ui",
    dictionary_root: Path | None = None,
) -> dict[str, Any]:
    text = user_text.strip()
    profile = profile_id.strip()
    if not text:
        raise ValueError("user_text must not be empty")
    if not profile:
        raise ValueError("profile_id must not be empty")
    if source not in {"chat_ui", "cli", "api"}:
        raise ValueError("source must be chat_ui, cli, or api")

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
            "seed": None,
        },
    }
