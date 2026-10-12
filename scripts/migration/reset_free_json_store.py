from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from json_part_sync import accept_staged_json_part, stage_json_part


TEST_REF = "part:free.test.background_scene@1"


def _candidate() -> dict:
    return {
        "schema_version": 1,
        "document_type": "local-rag/json-part",
        "part_id": "free.test.background_scene",
        "version": 1,
        "part_type": "background_scene",
        "name": "FREE baseline white studio background",
        "status": "staging",
        "aliases": ["white studio", "simple white room"],
        "tags": ["free", "test", "background", "studio"],
        "payload": {
            "generation": {
                "positive": (
                    "simple bright white studio interior, matte white walls, pale neutral floor, "
                    "soft diffuse ambient light, subtle architectural depth, uncluttered empty background, "
                    "clean spatial separation, no text, no signage"
                ),
                "negative": (
                    "busy scenery, outdoor environment, dark room, dramatic colored lighting, "
                    "text, logo, watermark, clutter"
                ),
            },
            "structured": {
                "environment": "minimal white studio interior",
                "surface_finish": "matte",
                "lighting": "soft diffuse neutral light",
                "depth": "subtle but readable interior depth",
                "clutter": "none",
            },
        },
        "provenance": {
            "source_type": "local-rag-bootstrap",
            "source_ref": "scripts/migration/reset_free_json_store.py",
        },
    }


def _remove_json_files(directory: Path) -> int:
    directory.mkdir(parents=True, exist_ok=True)
    count = 0
    for path in directory.glob("*.json"):
        if path.is_file():
            path.unlink()
            count += 1
    return count


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Reset the local FREE JSON runtime stores, then bootstrap one accepted background_scene Part. "
            "This intentionally does not delete or modify Oracle rows."
        )
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Required safety switch. Without this flag, nothing is deleted or written.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help="Project root. Defaults to the repository containing this script.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    root = args.root.expanduser().resolve()
    accepted = root / "learning/local-ai/store/json-parts"
    staging = root / "learning/local-ai/store/staging"
    receipts = root / "learning/local-ai/store/receipts"

    if not args.apply:
        print("[FREE-JSON-RESET:DRY-RUN] no files changed; rerun with --apply")
        print(f"[FREE-JSON-RESET:TARGET] {accepted}")
        print(f"[FREE-JSON-RESET:TARGET] {staging}")
        print(f"[FREE-JSON-RESET:TARGET] {receipts}")
        return 0

    removed_accepted = _remove_json_files(accepted)
    removed_staging = _remove_json_files(staging)
    removed_receipts = _remove_json_files(receipts)
    print(
        "[FREE-JSON-RESET:CLEAN:OK] "
        f"accepted={removed_accepted} staging={removed_staging} receipts={removed_receipts}"
    )

    staged = stage_json_part(root, _candidate())
    print(f"[FREE-JSON-RESET:STAGE:OK] {staged.ref}")
    accepted_result = accept_staged_json_part(
        root,
        staged.ref,
        expected_sha256=staged.sha256,
    )

    if accepted_result.ref != TEST_REF:
        raise RuntimeError(f"unexpected bootstrap ref: {accepted_result.ref}")

    print(f"[FREE-JSON-RESET:ACCEPT:OK] {accepted_result.accepted_path}")
    print(f"[FREE-JSON-RESET:RECEIPT:OK] {accepted_result.receipt_path}")
    print(f"[FREE-JSON-RESET:PAYLOAD:SHA256] {accepted_result.payload_sha256}")
    print("[FREE-JSON-RESET:ORACLE:UNCHANGED] no Oracle rows were deleted or rewritten")
    print("[FREE-JSON-RESET:OK]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
