from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "learning" / "rendering" / "generation_manifest.json"
DEFAULT_INCOMING = ROOT / "learning" / "rendering" / "incoming"
DEFAULT_DATASET = ROOT / "learning" / "rendering" / "dataset" / "20_mdanime"
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
ID_PATTERN = re.compile(r"^(\d{4})(?:$|[_\-\s])")


def _load_manifest(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("generation manifest root must be an object")
    if payload.get("schema_version") != 1:
        raise ValueError("generation manifest schema_version must be 1")
    trigger = payload.get("trigger_token")
    if not isinstance(trigger, str) or not trigger.strip():
        raise ValueError("generation manifest trigger_token must be a non-empty string")
    items = payload.get("items")
    if not isinstance(items, list) or not items:
        raise ValueError("generation manifest items must be a non-empty array")

    seen: set[str] = set()
    normalized: list[dict[str, str]] = []
    for raw in items:
        if not isinstance(raw, dict):
            raise ValueError("every generation manifest item must be an object")
        item_id = raw.get("id")
        caption = raw.get("caption")
        content_prompt = raw.get("content_prompt")
        if not isinstance(item_id, str) or not re.fullmatch(r"\d{4}", item_id):
            raise ValueError(f"invalid manifest item id: {item_id!r}")
        if item_id in seen:
            raise ValueError(f"duplicate manifest item id: {item_id}")
        seen.add(item_id)
        if not isinstance(caption, str) or not caption.strip():
            raise ValueError(f"manifest item {item_id} caption is missing")
        if trigger not in caption:
            raise ValueError(f"manifest item {item_id} caption does not contain trigger token {trigger!r}")
        if not isinstance(content_prompt, str) or not content_prompt.strip():
            raise ValueError(f"manifest item {item_id} content_prompt is missing")
        normalized.append(
            {
                "id": item_id,
                "caption": caption.strip(),
                "content_prompt": content_prompt.strip(),
            }
        )

    payload["items"] = normalized
    return payload


def _images_under(path: Path) -> list[Path]:
    if not path.exists():
        return []
    return sorted(
        (p for p in path.rglob("*") if p.is_file() and p.suffix.casefold() in IMAGE_EXTENSIONS),
        key=lambda p: str(p).casefold(),
    )


def _tagged_id(path: Path, valid_ids: set[str]) -> str | None:
    stem = path.stem.strip()
    if stem in valid_ids:
        return stem
    match = ID_PATTERN.match(stem)
    if match and match.group(1) in valid_ids:
        return match.group(1)
    return None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _existing_images(dataset_dir: Path, item_id: str) -> list[Path]:
    if not dataset_dir.exists():
        return []
    return sorted(
        p
        for p in dataset_dir.iterdir()
        if p.is_file() and p.stem == item_id and p.suffix.casefold() in IMAGE_EXTENSIONS
    )


def _assign_incoming(
    incoming_dir: Path,
    item_ids: list[str],
    sequential: bool,
    start_id: int,
) -> tuple[dict[str, list[Path]], list[Path]]:
    valid_ids = set(item_ids)
    assignments: dict[str, list[Path]] = defaultdict(list)
    untagged: list[Path] = []

    for image in _images_under(incoming_dir):
        item_id = _tagged_id(image, valid_ids)
        if item_id is None:
            untagged.append(image)
        else:
            assignments[item_id].append(image)

    if sequential and untagged:
        remaining = [
            item_id
            for item_id in item_ids
            if int(item_id) >= start_id and not assignments.get(item_id)
        ]
        ordered = sorted(
            untagged,
            key=lambda p: (p.stat().st_mtime_ns, str(p).casefold()),
        )
        if len(ordered) > len(remaining):
            raise ValueError(
                f"sequential import has {len(ordered)} untagged images but only {len(remaining)} manifest slots remain from {start_id:04d}"
            )
        for item_id, image in zip(remaining, ordered):
            assignments[item_id].append(image)
        untagged = ordered[len(remaining):]

    return assignments, untagged


def _write_caption(path: Path, caption: str, dry_run: bool) -> None:
    if dry_run:
        return
    path.write_text(caption.rstrip() + "\n", encoding="utf-8")


def prepare_dataset(
    manifest_path: Path,
    incoming_dir: Path,
    dataset_dir: Path,
    sequential: bool,
    start_id: int,
    replace: bool,
    dry_run: bool,
) -> int:
    manifest = _load_manifest(manifest_path)
    items: list[dict[str, str]] = manifest["items"]
    item_ids = [item["id"] for item in items]

    if start_id < 1 or start_id > 9999:
        raise ValueError("start_id must be between 1 and 9999")

    incoming_dir.mkdir(parents=True, exist_ok=True)
    dataset_dir.mkdir(parents=True, exist_ok=True)
    assignments, untagged = _assign_incoming(incoming_dir, item_ids, sequential, start_id)

    errors: list[str] = []
    missing: list[str] = []
    final_images: dict[str, Path] = {}
    copied = 0
    preserved = 0

    for item in items:
        item_id = item["id"]
        caption = item["caption"]
        incoming = assignments.get(item_id, [])
        existing = _existing_images(dataset_dir, item_id)

        if len(incoming) > 1:
            errors.append(
                f"{item_id}: multiple incoming images: " + ", ".join(str(p.name) for p in incoming)
            )
            continue
        if len(existing) > 1:
            errors.append(
                f"{item_id}: multiple dataset images already exist: " + ", ".join(str(p.name) for p in existing)
            )
            continue

        source = incoming[0] if incoming else None
        current = existing[0] if existing else None

        if source is None and current is None:
            missing.append(item_id)
            continue

        if source is not None and current is not None:
            same_file = _sha256(source) == _sha256(current)
            if same_file:
                final = current
                preserved += 1
            elif not replace:
                errors.append(
                    f"{item_id}: dataset image already exists and differs from incoming image; use --replace to overwrite"
                )
                continue
            else:
                final = dataset_dir / f"{item_id}{source.suffix.casefold()}"
                if not dry_run:
                    current.unlink(missing_ok=True)
                    shutil.copy2(source, final)
                copied += 1
        elif source is not None:
            final = dataset_dir / f"{item_id}{source.suffix.casefold()}"
            if not dry_run:
                shutil.copy2(source, final)
            copied += 1
        else:
            final = current
            preserved += 1

        _write_caption(dataset_dir / f"{item_id}.txt", caption, dry_run)
        final_images[item_id] = final

    if errors:
        print("[DATASET:ERROR]")
        for error in errors:
            print(f"  - {error}")
        return 1

    hash_to_ids: dict[str, list[str]] = defaultdict(list)
    if not dry_run:
        for item_id, image in final_images.items():
            if image.is_file():
                hash_to_ids[_sha256(image)].append(item_id)
    else:
        for item_id, image in final_images.items():
            if image.is_file():
                hash_to_ids[_sha256(image)].append(item_id)

    duplicates = [ids for ids in hash_to_ids.values() if len(ids) > 1]
    if duplicates:
        print("[DATASET:ERROR] exact duplicate image files detected:")
        for ids in duplicates:
            print("  - " + ", ".join(ids))
        return 1

    if untagged:
        print(f"[DATASET:WARN] unassigned incoming images={len(untagged)}")
        for path in untagged[:10]:
            print(f"  - {path.name}")

    print(f"[DATASET] copied={copied} preserved={preserved} ready={len(final_images)}/{len(items)}")
    print(f"[DATASET] destination={dataset_dir}")

    if missing:
        print(f"[DATASET:INCOMPLETE] missing={len(missing)} ids={','.join(missing)}")
        return 2

    print("[DATASET:PREPARE:OK]")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Import independently generated rendering reference images and create canonical LoRA captions"
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--incoming", type=Path, default=DEFAULT_INCOMING)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument(
        "--sequential",
        action="store_true",
        help="Assign untagged incoming images by file modification time to remaining manifest IDs",
    )
    parser.add_argument(
        "--start-id",
        type=int,
        default=1,
        help="First manifest numeric ID eligible for sequential assignment",
    )
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    manifest = args.manifest if args.manifest.is_absolute() else (ROOT / args.manifest)
    incoming = args.incoming if args.incoming.is_absolute() else (ROOT / args.incoming)
    dataset = args.dataset if args.dataset.is_absolute() else (ROOT / args.dataset)

    return prepare_dataset(
        manifest.resolve(),
        incoming.resolve(),
        dataset.resolve(),
        sequential=bool(args.sequential),
        start_id=args.start_id,
        replace=bool(args.replace),
        dry_run=bool(args.dry_run),
    )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[DATASET:FATAL] {exc}", file=sys.stderr)
        raise SystemExit(1)
