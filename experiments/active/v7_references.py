"""V7 reference preparation. Creates an independent face + outfit *source* sheet.

No face segmentation, identity embedding, or garment segmentation is claimed.
This extractor explicitly supports only the current upright portrait master layout.
Original image pixels are used unchanged except cropping/resampling for the sheet.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
from PIL import Image, ImageDraw, ImageOps


class ReferenceError(ValueError):
    pass


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024*1024), b""):
            h.update(block)
    return h.hexdigest()


def _rel_box(w: int, h: int, coords: tuple[float, float, float, float]) -> tuple[int, int, int, int]:
    return tuple(round(a * z) for a, z in zip(coords, (w, h, w, h)))


def make_reference_bundle(master: Path, output: Path) -> dict[str, Any]:
    """Create a single 2-panel reference with face/hair and original outfit.

    This is a constrained fixed-frontal-master heuristic. For other characters,
    use a real detector/segmenter rather than mislabeling an arbitrary crop.
    """
    master = Path(master)
    if not master.is_file():
        raise ReferenceError("MASTER_FILE_MISSING")
    output.mkdir(parents=True, exist_ok=True)
    with Image.open(master) as src:
        im = src.convert("RGB")
    w, h = im.size
    if w < 600 or h < 900 or not 1.45 <= h / w <= 2.4:
        raise ReferenceError("REFERENCE_LAYOUT_UNSUPPORTED: only full-body portrait frontal master")
    # Explicitly *unverified* fixed-ratio crops for current full-body master.
    face_box = _rel_box(w, h, (.305, .008, .695, .194))
    outfit_box = _rel_box(w, h, (.272, .164, .734, .512))
    face = im.crop(face_box)
    outfit = im.crop(outfit_box)
    face_path = output / "face_hair_source.png"
    outfit_path = output / "outfit_source.png"
    face.save(face_path)
    outfit.save(outfit_path)

    sheet = Image.new("RGB", (1024, 672), (241, 241, 241))
    draw = ImageDraw.Draw(sheet)
    panels = [(face, (10, 36, 502, 662), "FACE / HAIR (MASTER)"),
              (outfit, (522, 36, 1014, 662), "ORIGINAL OUTFIT (MASTER)")]
    for original, bbox, label in panels:
        x1, y1, x2, y2 = bbox
        resized = ImageOps.contain(original, (x2-x1, y2-y1), Image.Resampling.LANCZOS)
        sheet.paste(resized, (x1 + ((x2-x1)-resized.width)//2,
                              y1 + ((y2-y1)-resized.height)//2))
        draw.text((x1+6, 10), label, fill=(18,18,18))
    sheet_path = output / "identity_outfit_reference.png"
    sheet.save(sheet_path)
    meta = {
        "schema_version": 1,
        "master_sha256": sha256(master), "master_dimensions": [w, h],
        "method": "fixed_frontal_portrait_crop_unverified_not_segmentation",
        "identity": {"face_hair_crop": str(face_path), "crop_box": list(face_box),
                     "sha256": sha256(face_path)},
        "outfit": {"reference_crop": str(outfit_path), "crop_box": list(outfit_box),
                   "sha256": sha256(outfit_path), "explicit_override": False},
        "reference_sheet": {"path": str(sheet_path), "sha256": sha256(sheet_path)},
        "rendering": {"reference_source": "master", "target": "matte soft anime realism",
                      "hard_lock": False},
        "identity_hard_lock": False, "outfit_hard_lock": False,
        "reference_image_training": "NONE",
    }
    (output / "reference_manifest_v7.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta
