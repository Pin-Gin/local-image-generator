from __future__ import annotations

import json
from pathlib import Path

from chat_contract import build_generation_request
from json_parts import json_part_filename, resolve_json_part_store


ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    store = resolve_json_part_store(ROOT)
    store.mkdir(parents=True, exist_ok=True)
    part_id = "test.runtime-part"
    version = 1
    target = store / json_part_filename(part_id, version)
    document = {
        "schema_version": 1,
        "document_type": "local-rag/json-part",
        "part_id": part_id,
        "version": version,
        "part_type": "test",
        "name": "Runtime JSON part test",
        "status": "accepted",
        "aliases": [],
        "tags": ["test"],
        "payload": {
            "generation": {
                "positive": "reusable positive fragment",
                "negative": "reusable negative fragment",
            }
        },
        "provenance": {"source_type": "test", "source_ref": "json_parts_test.py"},
    }

    target.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        request = build_generation_request(
            json.dumps(
                {
                    "positive": "base prompt",
                    "parts": [f"part:{part_id}@{version}"],
                },
                ensure_ascii=False,
            ),
            "free-sdxl-v1",
        )
        prompt = request["prompt_input"]
        assert "base prompt" in prompt["positive"]
        assert "reusable positive fragment" in prompt["positive"]
        assert "reusable negative fragment" in (prompt["negative"] or "")
        assert prompt["resolved_parts"][0]["ref"] == f"part:{part_id}@{version}"
        print("[JSON-PARTS:TEST:OK]")
        return 0
    finally:
        target.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
