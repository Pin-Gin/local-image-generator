from __future__ import annotations

import argparse
from pathlib import Path

from json_parts import parse_part_ref
from oracle_knowledge_store import OracleKnowledgeStore


ROOT = Path(__file__).resolve().parent.parent
STAGING_ROOT = (ROOT / "learning" / "local-ai" / "store" / "staging").resolve()


def _remove_staging_file(file_path: str | None, ref: str) -> bool:
    if not file_path:
        return False
    target = Path(file_path).resolve()
    try:
        target.relative_to(STAGING_ROOT)
    except ValueError as exc:
        raise RuntimeError(
            f"cleanup refuses file outside staging root: {target}"
        ) from exc

    part_id, version = parse_part_ref(ref)
    expected_name = f"{part_id}.v{version}.json"
    if target.name != expected_name:
        raise RuntimeError(
            f"cleanup file name mismatch: expected={expected_name} actual={target.name}"
        )
    if not target.exists():
        return False
    if not target.is_file():
        raise RuntimeError(f"cleanup target is not a file: {target}")
    target.unlink()
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Delete one exact test.* staging JSON part from Oracle and local staging storage"
    )
    parser.add_argument(
        "ref",
        nargs="?",
        default="part:test.oracle-roundtrip@1",
        help="canonical test part ref (default: part:test.oracle-roundtrip@1)",
    )
    args = parser.parse_args()

    part_id, _version = parse_part_ref(args.ref)
    if not part_id.startswith("test."):
        raise ValueError("cleanup only permits part_ids in the test.* namespace")

    store = OracleKnowledgeStore(ROOT)
    result = store.delete_staging_test_json_part(args.ref)
    file_deleted = _remove_staging_file(result.get("file_path"), args.ref)

    print(f"[TEST-CLEANUP:REF] {args.ref}")
    print(f"[TEST-CLEANUP:ORACLE] deleted={result.get('deleted')} reason={result.get('reason')}")
    print(f"[TEST-CLEANUP:FILE] deleted={file_deleted}")
    print("[TEST-CLEANUP:OK]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
