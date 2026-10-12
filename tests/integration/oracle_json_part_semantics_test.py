from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from oracle_knowledge_store import prepare_json_part_for_oracle


def main() -> int:
    document = {
        "schema_version": 1,
        "document_type": "local-rag/json-part",
        "part_id": "test.oracle-semantic-preservation",
        "version": 1,
        "part_type": "background_scene",
        "name": "  preserve surrounding spaces in original values  ",
        "status": "accepted",
        "aliases": ["  alias with spaces  "],
        "tags": ["free", "  exact-value  "],
        "payload": {
            "generation": {
                "positive": "  exact positive text with surrounding spaces  ",
                "negative": "  exact negative text with surrounding spaces  ",
            },
            "structured": {
                "application": {"mode": "delta", "preserve_unspecified": True},
                "ordered": ["a", "b", "a"],
                "nested": {"text": "  do not trim this  ", "number": 7},
            },
        },
        "provenance": {
            "source_type": "integration-test",
            "source_ref": "oracle_json_part_semantics_test",
        },
    }

    validated, canonical, digest = prepare_json_part_for_oracle(document)
    stored = json.loads(canonical)

    if stored != document:
        raise AssertionError("Oracle storage preparation changed the accepted document")
    if validated["name"] == document["name"]:
        raise AssertionError("test fixture did not exercise validator normalization")
    if stored["payload"] != document["payload"]:
        raise AssertionError("payload semantics changed during Oracle storage preparation")

    expected_digest = hashlib.sha256(
        json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    if digest != expected_digest:
        raise AssertionError("Oracle content digest does not represent the original accepted document")

    print("[ORACLE-JSON-PART:VALIDATION-METADATA:OK]")
    print("[ORACLE-JSON-PART:DOCUMENT-PRESERVED:OK]")
    print("[ORACLE-JSON-PART:PAYLOAD-PRESERVED:OK]")
    print("[ORACLE-JSON-PART:DIGEST:OK]")
    print("[ORACLE-JSON-PART:SEMANTICS-TEST:OK]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
