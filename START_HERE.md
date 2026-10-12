# local-RAG — START HERE

Status: **ACTIVE LOCAL IMAGE GENERATION APPLICATION**

Repository:

```text
Pin-Gin/local-image-generator
local root: C:\Dev\local-image-generator
```

## Read this first

The authoritative continuation document is:

```text
docs/handoff/LOCAL_RAG_HANDOFF.md
```

Read it completely before architecture or implementation changes. Then inspect current `main`. Repository state overrides old chat memory.

Repository organization is documented at:

```text
docs/architecture/REPOSITORY_LAYOUT.md
```

## Current FREE direction

FREE is deterministic and must not use conversational/local AI for request interpretation.

The current accepted authority split is:

```text
MAIN REFERENCE IMAGE
  -> IP-Adapter
  -> appearance authority

POSE REFERENCE IMAGE
  -> DWPose / OpenPose ControlNet
  -> pose/spatial authority

UP TO FIVE ROLE-BOUND JSON PARTS
  1. CHARACTER / BODY
  2. OUTFIT / PROP
  3. EXPRESSION / FACE
  4. CAMERA / COMPOSITION
  5. BACKGROUND / SCENE

RENDERING PROFILE
  -> drawing/rendering authority
  -> separate from the five content slots

LINEART PROFILE
  -> contour authority
  -> separate from rendering depth

FRESH LATENT
  -> redraw/generate final image
```

Do not revert FREE to source-image img2img latent as the main appearance mechanism. The img2img authority experiment showed that source appearance and source pose become coupled too strongly.

## Current visual target

Rendering identity remains **Matte Dimensional Anime**, but the target is now explicitly:

```text
matte response
+ anime realism / modeled form
+ spatial depth
+ slight 3D-anime dimensionality
+ clear intentional linework
```

The output must remain an anime/illustration image, not photoreal and not raw CGI/PBR.

Rendering and lineart are separate authorities. Stronger rendering must not erase contour clarity.

## Reference-image storage

Local FREE references belong under:

```text
references/free/main/   # IP-Adapter appearance image
references/free/pose/   # DWPose/OpenPose pose image
```

Actual image files are ignored by Git by default.

## JSON lifecycle

Local AI remains enabled in LEARN and may create detailed JSON candidates.

```text
learning/local-ai/store/staging/
  -> structural validation / explicit acceptance
learning/local-ai/store/json-parts/
  -> deterministic FREE consumption
```

Sync/accept must preserve payload semantics. Structural validation may check schema/ref/role/hash without rewriting content.

## MEMORIELA boundary

MEMORIELA remains a separate canon-aware domain. FREE tests and generic FREE generation must not silently use MEMORIELA character assets.

## Current operational endpoints

```text
ComfyUI: http://127.0.0.1:8188
Ollama:  http://127.0.0.1:11435
Oracle:  127.0.0.1:1521/FREEPDB1
```

## Current active diagnostic

The IP-Adapter + DWPose + JSON + Rendering/Lineart authority experiment lives under:

```text
experiments/active/free_ipadapter_pose_json_experiment.py
```

Experiments are diagnostic only. Production engine code belongs in `src/`.

## Development rule

Only user-supplied local execution/visual evidence promotes a runtime path to **VERIFIED**. Git changes by themselves are **IMPLEMENTED / UNVERIFIED**.
