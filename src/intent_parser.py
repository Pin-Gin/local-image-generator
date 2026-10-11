from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from typing import Any


CATEGORY_FILES = {
    "character": "characters.json",
    "outfit": "outfits.json",
    "background": "backgrounds.json",
    "pose": "poses.json",
    "expression": "expressions.json",
    "hair": "hair.json",
    "rendering": "rendering.json",
}


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return "".join(normalized.split())


def _load_dictionary(path: Path, expected_category: str) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"intent dictionary root must be an object: {path}")
    if payload.get("schema_version") != 1:
        raise ValueError(f"unsupported intent dictionary schema_version: {path}")
    if payload.get("category") != expected_category:
        raise ValueError(
            f"intent dictionary category mismatch: expected={expected_category} path={path}"
        )

    entries = payload.get("entries")
    if not isinstance(entries, list):
        raise ValueError(f"intent dictionary entries must be an array: {path}")

    validated: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_aliases: dict[str, str] = {}

    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError(f"intent dictionary entry must be an object: {path}")
        item_id = entry.get("id")
        aliases = entry.get("aliases")
        if not isinstance(item_id, str) or not item_id.strip():
            raise ValueError(f"intent dictionary id must be a non-empty string: {path}")
        if item_id in seen_ids:
            raise ValueError(f"duplicate intent dictionary id={item_id}: {path}")
        if not isinstance(aliases, list) or not aliases:
            raise ValueError(f"aliases must be a non-empty string array for id={item_id}: {path}")
        if not all(isinstance(alias, str) and alias.strip() for alias in aliases):
            raise ValueError(f"aliases contain an invalid value for id={item_id}: {path}")

        normalized_aliases: list[str] = []
        for alias in aliases:
            normalized_alias = _normalize_text(alias)
            previous = seen_aliases.get(normalized_alias)
            if previous is not None and previous != item_id:
                raise ValueError(
                    f"ambiguous alias={alias!r} maps to both {previous} and {item_id}: {path}"
                )
            seen_aliases[normalized_alias] = item_id
            normalized_aliases.append(normalized_alias)

        seen_ids.add(item_id)
        validated.append({"id": item_id, "aliases": normalized_aliases})

    return validated


def parse_intent(user_text: str, dictionary_root: Path) -> dict[str, Any]:
    normalized_text = _normalize_text(user_text)
    intent: dict[str, Any] = {"status": "unparsed"}
    matched_categories = 0
    ambiguous = False

    for category, filename in CATEGORY_FILES.items():
        path = dictionary_root / filename
        entries = _load_dictionary(path, category)

        matched_ids: set[str] = set()
        for entry in entries:
            if any(alias in normalized_text for alias in entry["aliases"]):
                matched_ids.add(entry["id"])

        if len(matched_ids) == 1:
            intent[category] = next(iter(matched_ids))
            matched_categories += 1
        else:
            intent[category] = None
            if len(matched_ids) > 1:
                ambiguous = True

    if ambiguous:
        intent["status"] = "needs_confirmation"
    elif matched_categories > 0:
        intent["status"] = "parsed"

    return intent
