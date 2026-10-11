# MEMORIELA generation domain

MEMORIELA is the controlled generation path for the named cast and reusable production assets.

Routing names:
- ゆら / 久遠ゆら
- 要 / 水瀬要
- 栞
- 大和
- 美緒

Rules:
- named MEMORIELA characters route here instead of FREE;
- character identity, outfit, situation, background, pose, expression, and camera assets are modular;
- character-specific assets must never silently fall back to another character;
- outfits are intended to be learned independently from mannequin/reference datasets and applied as replaceable assets;
- situation/background assets can be added independently for standing art, illustrations, and manga generation;
- all outputs use the same shared rendering layer under `shared/rendering/`.

Subdomains:
- `characters/` character identity/reference definitions
- `outfits/` learned outfit assets and metadata
- `situations/` reusable scene/situation definitions
- `backgrounds/` reusable background assets and metadata
