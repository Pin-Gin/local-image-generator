# local-RAG repository layout

Status: **TARGET + ACTIVE ORGANIZATION RULES**

Root:

```text
C:\Dev\local-image-generator
```

The repository is organized by responsibility, not by temporary implementation history.

## Canonical layout

```text
local-image-generator/
├─ START_HERE.md
├─ docs/
│  ├─ handoff/
│  └─ architecture/
│
├─ src/                         # production Python runtime only
├─ ui/                          # desktop/webview frontend
│
├─ references/                  # user-supplied FREE reference images
│  └─ free/
│     ├─ main/                  # IP-Adapter appearance authority
│     └─ pose/                  # DWPose/OpenPose pose authority
│
├─ shared/                      # global drawing-method authorities
│  ├─ rendering/
│  └─ lineart/
│
├─ profiles/                    # generation/runtime profiles
├─ workflows/                   # ComfyUI API workflow templates
├─ schemas/                     # machine-readable contracts
│
├─ learning/                    # AI knowledge + training lifecycles
│  ├─ local-ai/
│  │  ├─ store/staging/
│  │  └─ store/json-parts/
│  ├─ registry/
│  └─ rendering/
│
├─ experiments/                 # diagnostic-only code
│  ├─ active/
│  └─ archive/
│
├─ tests/                       # tests/capability probes as they are migrated
│
├─ models/                      # large project-owned model assets; Git ignored
├─ database/                    # SQLite state
├─ infra/                       # Oracle/infrastructure
├─ config/
├─ tools/                       # installed project-local runtimes/tools
├─ outputs/
├─ cache/
└─ logs/
```

## Responsibility rules

### `src/`

Only production/runtime Python belongs here long term. New one-off experiments must not be added to `src/`.

Existing historical tests/capability probes may remain temporarily until migrated without breaking verified commands. Do not mass-move them merely for aesthetics.

### `references/free/main/`

Canonical local source images for IP-Adapter appearance authority.

The image may influence:

- face/overall identity appearance;
- hair appearance;
- body appearance;
- clothing appearance;
- colors and general visual character.

It must not be used as the KSampler initial latent in the target FREE architecture.

### `references/free/pose/`

Canonical local pose-reference images for:

```text
DWPose -> OpenPose ControlNet
```

This directory owns pose/spatial authority, not appearance authority.

### `shared/rendering/`

Rendering Authority. It owns **how the image is drawn**.

Current target is Matte Dimensional Anime: matte surface response, anime realism, spatial depth, volumetric form and slight 3D-anime dimensionality while remaining an illustration.

### `shared/lineart/`

Lineart Authority. It owns contour clarity independently from rendering depth/shading.

### `learning/local-ai/store/staging/`

Local-AI JSON candidates before acceptance.

### `learning/local-ai/store/json-parts/`

Accepted reusable JSON Parts. Sync/accept operations must preserve payload semantics and may validate structure/hash without rewriting prose.

### `experiments/`

Diagnostic code only. An experiment does not become production architecture just because it generated an image.

`experiments/archive/` contains superseded diagnostics whose conclusions are preserved in the handoff.

## FREE input ownership

Production FREE input is bounded rather than an unlimited bag of prompts/assets:

```text
MAIN IMAGE             -> appearance authority
POSE IMAGE             -> pose authority
JSON SLOT 1            -> CHARACTER / BODY
JSON SLOT 2            -> OUTFIT / PROP
JSON SLOT 3            -> EXPRESSION / FACE
JSON SLOT 4            -> CAMERA / COMPOSITION
JSON SLOT 5            -> BACKGROUND / SCENE
RENDERING PROFILE      -> drawing/rendering authority
LINEART PROFILE        -> contour authority
```

Unused JSON slots may be empty. Rendering and lineart do not count against the five content slots.

## Git policy for local references

Actual user reference images under `references/free/main/` and `references/free/pose/` are local runtime assets and are ignored by Git by default.

Track only README/placeholder files unless the user explicitly decides to version a specific safe reference asset.

## Cleanup policy

Preserve these during restructuring:

```text
models/
database/
learning/local-ai/store/
learning/rendering/
.env.local-ai
Oracle persistent volume
tools/ollama/
tools/python312/
tools/sd-scripts/
```

Do not delete persistent state as part of source-code cleanup.

Git history is the archive for obsolete source files. Once a diagnostic conclusion is captured in `docs/handoff/LOCAL_RAG_HANDOFF.md`, dead diagnostic source may be moved to `experiments/archive/` or removed.