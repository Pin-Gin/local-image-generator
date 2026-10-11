from __future__ import annotations

import argparse
import sys
from pathlib import Path

from database import import_manifest, initialize_database, list_generations, update_qa_status


def repository_root() -> Path:
    return Path(__file__).resolve().parent.parent


def find_latest_manifest(outputs_root: Path) -> Path:
    candidates = sorted(
        outputs_root.glob("*/manifest.json"),
        key=lambda path: path.parent.name,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError(f"No generation manifest found under: {outputs_root}")
    return candidates[0]


def main() -> int:
    root = repository_root()
    parser = argparse.ArgumentParser(description="G5 SQLite history / lookup verification")
    parser.add_argument(
        "--database",
        default="database/memoriela_local.db",
        help="SQLite database path relative to repository root unless absolute.",
    )
    parser.add_argument(
        "--manifest",
        default=None,
        help="Manifest path to import. Defaults to the latest outputs/*/manifest.json.",
    )
    parser.add_argument(
        "--set-status",
        choices=("unreviewed", "accepted", "rejected"),
        default=None,
        help="Optionally persist a QA status for the imported generation.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum history rows to print.",
    )
    args = parser.parse_args()

    database_path = Path(args.database)
    if not database_path.is_absolute():
        database_path = (root / database_path).resolve()

    try:
        initialize_database(database_path)
        print(f"[G5:DB:OK] database={database_path}")

        if args.manifest:
            manifest_path = Path(args.manifest)
            if not manifest_path.is_absolute():
                manifest_path = (root / manifest_path).resolve()
        else:
            manifest_path = find_latest_manifest(root / "outputs")

        record = import_manifest(database_path, manifest_path)
        print("[G5:IMPORT:OK]")
        print(f"generation_id={record.generation_id}")
        print(f"manifest={record.manifest_path}")
        print(f"manifest_sha256={record.manifest_sha256}")
        print(f"output={record.output_path}")
        print(f"output_sha256={record.output_sha256}")
        print(f"qa_status={record.qa_status}")

        if args.set_status is not None:
            record = update_qa_status(database_path, record.generation_id, args.set_status)
            print("[G5:STATUS:OK]")
            print(f"generation_id={record.generation_id}")
            print(f"qa_status={record.qa_status}")

        history = list_generations(database_path, args.limit)
        print(f"[G5:HISTORY:OK] count={len(history)}")
        for item in history:
            print(
                "history="
                f"{item.generation_id}|{item.qa_status}|{item.character or ''}|"
                f"{item.profile_id or ''}|{item.output_path}"
            )

        print("[G5:OK]")
        return 0
    except (OSError, ValueError, RuntimeError, KeyError) as exc:
        print(f"[G5:FAIL] {exc}", file=sys.stderr)
        return 5


if __name__ == "__main__":
    raise SystemExit(main())
