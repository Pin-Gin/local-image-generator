from __future__ import annotations

from pathlib import Path


CHECKPOINT_EXTENSIONS = {".safetensors", ".ckpt"}
CHECKPOINT_ROOT = Path("models/checkpoints")


def _checkpoint_root(root: Path) -> Path:
    return (root / CHECKPOINT_ROOT).resolve()


def list_project_checkpoints(root: Path) -> list[str]:
    """Return project-owned checkpoint names in stable relative-path order."""
    model_root = _checkpoint_root(root)
    if not model_root.is_dir():
        return []

    names: list[str] = []
    for path in model_root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in CHECKPOINT_EXTENSIONS:
            continue
        names.append(path.relative_to(model_root).as_posix())
    return sorted(names, key=str.casefold)


def resolve_project_checkpoint(root: Path, requested: str) -> str:
    """Resolve an exact checkpoint from models/checkpoints without leaving that root."""
    if not isinstance(requested, str) or not requested.strip():
        raise ValueError("checkpoint selection must be a non-empty string")

    normalized = requested.strip().replace("\\", "/")
    candidate = Path(normalized)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError("checkpoint selection must be relative to models/checkpoints")

    available = list_project_checkpoints(root)
    by_casefold = {name.casefold(): name for name in available}
    resolved = by_casefold.get(normalized.casefold())
    if resolved is None:
        choices = ", ".join(available) if available else "<none>"
        raise ValueError(f"checkpoint is not installed under models/checkpoints: {normalized}; available: {choices}")
    return resolved
