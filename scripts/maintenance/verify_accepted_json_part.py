from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from json_part_sync import resolve_accepted_store, resolve_receipt_store
from json_parts import json_part_filename, parse_part_ref, validate_json_part
from oracle_knowledge_store import OracleKnowledgeStore, prepare_json_part_for_oracle


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Verify one accepted JSON Part across the local accepted file, acceptance receipt, "
            "and Oracle index without printing semantic payload content."
        )
    )
    parser.add_argument("--ref", required=True, help="Canonical ref such as part:free.demo.background.soft-room@1")
    return parser.parse_args()


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    args = _parse_args()
    ref = args.ref.strip()
    part_id, version = parse_part_ref(ref)

    accepted_path = resolve_accepted_store(ROOT) / json_part_filename(part_id, version)
    receipt_path = resolve_receipt_store(ROOT) / f"{part_id}.v{version}.acceptance.json"
    if not accepted_path.is_file():
        raise FileNotFoundError(f"accepted JSON Part not found: {accepted_path}")
    if not receipt_path.is_file():
        raise FileNotFoundError(f"acceptance receipt not found: {receipt_path}")

    document = json.loads(accepted_path.read_text(encoding="utf-8"))
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or not isinstance(receipt, dict):
        raise ValueError("accepted document and receipt must both be JSON objects")

    validated = validate_json_part(document)
    if validated["part_id"] != part_id or validated["version"] != version:
        raise ValueError("accepted file identity does not match requested ref")
    if document.get("status") != "accepted":
        raise ValueError("accepted file status is not accepted")
    if receipt.get("ref") != ref:
        raise ValueError("receipt ref does not match requested ref")

    accepted_sha = _file_sha256(accepted_path)
    if receipt.get("accepted_sha256") != accepted_sha:
        raise ValueError("receipt accepted_sha256 does not match accepted file")
    print(f"[JSON-PART-VERIFY:FILE:OK] {ref}")
    print("[JSON-PART-VERIFY:RECEIPT:OK]")

    oracle = OracleKnowledgeStore(ROOT)
    if not oracle.configured():
        raise RuntimeError("Oracle is not configured")
    indexed = oracle.get_json_part(ref)
    if indexed is None:
        raise RuntimeError(f"Oracle JSON Part row not found: {ref}")
    if indexed.get("status") != "accepted":
        raise ValueError("Oracle JSON Part status is not accepted")
    if indexed.get("document") != document:
        raise ValueError("Oracle DOCUMENT_JSON differs from the accepted local document")

    _validated, _canonical, expected_oracle_sha = prepare_json_part_for_oracle(document)
    if indexed.get("sha256") != expected_oracle_sha:
        raise ValueError("Oracle CONTENT_SHA256 does not match the accepted document semantics")

    print("[JSON-PART-VERIFY:ORACLE:FOUND]")
    print("[JSON-PART-VERIFY:ORACLE-DOCUMENT-PRESERVED:OK]")
    print("[JSON-PART-VERIFY:ORACLE-DIGEST:OK]")
    print("[JSON-PART-VERIFY:OK]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
