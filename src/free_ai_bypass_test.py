from __future__ import annotations

import json
from pathlib import Path

from chat_contract import build_generation_request
from learning_registry import select_assets_with_local_ai, validate_registry


ROOT = Path(__file__).resolve().parent.parent
STORE = ROOT / "learning" / "local-ai" / "store" / "json-parts"
PART_ID = "test.free-ai-bypass"
PART_REF = f"part:{PART_ID}@1"
PART_PATH = STORE / f"{PART_ID}.v1.json"


class FailIfCalledClient:
    def chat(self, *args, **kwargs):
        raise AssertionError("FREE generation must not call local AI")


def _registry() -> dict:
    return validate_registry(
        {
            "schema_version": 1,
            "registry_version": 1,
            "assets": [
                {
                    "asset_id": "test-free-ai-asset",
                    "enabled": True,
                    "selection_mode": "ai",
                    "domains": ["free"],
                    "category": "test",
                    "description": "Asset that must never trigger a FREE Qwen call.",
                    "concepts": ["free bypass test"],
                    "runtime": {
                        "type": "prompt",
                        "positive": "must not be selected",
                        "negative": "",
                    },
                }
            ],
        }
    )


def main() -> int:
    STORE.mkdir(parents=True, exist_ok=True)
    if PART_PATH.exists():
        raise RuntimeError(f"test refuses to overwrite existing file: {PART_PATH}")

    manual_part = {
        "file_name": PART_PATH.name,
        "description": "FREE AI bypass test part",
        "pose": {
            "body": {
                "state": "standing",
            },
            "camera": "full body",
        },
    }

    try:
        PART_PATH.write_text(
            json.dumps(manual_part, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        user_json = json.dumps(
            {
                "positive": "test subject",
                "parts": [PART_REF],
            },
            ensure_ascii=False,
        )
        request = build_generation_request(
            user_json,
            "free-sdxl-v1",
            source="cli",
        )

        if request.get("generation_domain") != "free":
            raise AssertionError(f"expected FREE route: {request.get('generation_domain')}")

        prompt_input = request.get("prompt_input", {})
        resolved_parts = prompt_input.get("resolved_parts", [])
        if len(resolved_parts) != 1 or resolved_parts[0].get("ref") != PART_REF:
            raise AssertionError(f"JSON Part was not resolved exactly: {resolved_parts}")

        positive = prompt_input.get("positive", "")
        expected_fragments = (
            "test subject",
            "pose.body.state: standing",
            "pose.camera: full body",
        )
        for fragment in expected_fragments:
            if fragment not in positive:
                raise AssertionError(f"missing prompt fragment {fragment!r}: {positive!r}")

        selection = select_assets_with_local_ai(
            FailIfCalledClient(),
            _registry(),
            user_text=user_json,
            generation_domain="free",
        )
        if selection.selected_asset_ids:
            raise AssertionError(f"FREE unexpectedly selected AI assets: {selection.selected_asset_ids}")
        if selection.selector != "deterministic-free":
            raise AssertionError(f"unexpected FREE selector trace: {selection.selector}")

        print(f"[FREE:JSON-PART:OK] {PART_REF}")
        print("[FREE:AI-BYPASS:OK]")
        return 0
    finally:
        if PART_PATH.exists():
            PART_PATH.unlink()
            print(f"[FREE:TEST-CLEANUP:OK] {PART_PATH.name}")


if __name__ == "__main__":
    raise SystemExit(main())
