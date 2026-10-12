from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from json_part_sync import accept_staged_json_part, stage_json_part


def _candidate(*, part_type: str = "character_body") -> dict:
    return {
        "schema_version": 1,
        "document_type": "local-rag/json-part",
        "part_id": "test.sync-integrity",
        "version": 1,
        "part_type": part_type,
        "name": "JSON sync integrity test",
        "status": "staging",
        "aliases": ["sync test"],
        "tags": ["test", "integrity"],
        "payload": {
            "generation": {
                "positive": "precise test content",
                "negative": "unwanted test artifact",
            },
            "structured": {
                "nested": {
                    "value": "must remain byte-semantically identical after acceptance",
                    "number": 7,
                },
                "ordered": ["a", "b", "a"],
            },
        },
        "provenance": {
            "source_type": "integration-test",
            "source_ref": "json_part_sync_test",
        },
    }


def _semantic_sha(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="local-rag-json-sync-") as temp:
        resource_root = Path(temp)
        (resource_root / "learning/local-ai/store/json-parts").mkdir(parents=True)
        (resource_root / "learning/local-ai/store/staging").mkdir(parents=True)

        original = _candidate()
        original_payload = copy.deepcopy(original["payload"])
        stage = stage_json_part(resource_root, original)
        if not stage.path.is_file():
            raise AssertionError("staging file was not created")
        print(f"[JSON-SYNC:STAGE:OK] {stage.ref}")

        try:
            accept_staged_json_part(
                resource_root,
                stage.ref,
                expected_sha256="0" * 64,
            )
        except ValueError as exc:
            if "SHA256 changed" not in str(exc):
                raise
            print("[JSON-SYNC:HASH-GATE:OK]")
        else:
            raise AssertionError("acceptance should reject a mismatched expected SHA256")

        accepted = accept_staged_json_part(
            resource_root,
            stage.ref,
            expected_sha256=stage.sha256,
        )
        if stage.path.exists():
            raise AssertionError("staging file should be removed after successful acceptance")
        if not accepted.accepted_path.is_file():
            raise AssertionError("accepted file was not created")
        if not accepted.receipt_path.is_file():
            raise AssertionError("acceptance receipt was not created")

        accepted_document = json.loads(accepted.accepted_path.read_text(encoding="utf-8"))
        if accepted_document["status"] != "accepted":
            raise AssertionError("accepted status was not written")
        if accepted_document["payload"] != original_payload:
            raise AssertionError("payload changed during acceptance")
        if accepted.payload_sha256 != _semantic_sha(original_payload):
            raise AssertionError("payload semantic digest mismatch")
        print("[JSON-SYNC:PAYLOAD-PRESERVED:OK]")
        print(f"[JSON-SYNC:ACCEPT:OK] {accepted.ref}")

        invalid = _candidate(part_type="pose")
        invalid["part_id"] = "test.sync-invalid-role"
        try:
            stage_json_part(resource_root, invalid)
        except ValueError as exc:
            if "part_type must be one of" not in str(exc):
                raise
            print("[JSON-SYNC:ROLE-GATE:OK]")
        else:
            raise AssertionError("FREE staging should reject a non-slot part_type")

    print("[JSON-SYNC:TEST:OK]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
