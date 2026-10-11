# local-RAG — START HERE

Status: **ACTIVE LOCAL IMAGE GENERATION APPLICATION**

This repository is the production development root for the local-RAG desktop image-generation application.

## Product split

local-RAG has two generation domains plus one shared rendering layer:

```text
local-RAG
  -> FREE
       natural language / JSON -> faithful text2img
       no MEMORIELA-specific assets
  -> MEMORIELA
       named cast -> character/reference/assets pipeline
       modular outfits / situations / backgrounds / poses / expressions
  -> SHARED RENDERING
       Matte Dimensional Anime
       used by both FREE and MEMORIELA
       prompt rules now, learned rendering LoRA when trained/activated
```

Natural-language names currently routed to MEMORIELA:
- ゆら / 久遠ゆら
- 要 / 水瀬要
- 栞
- 大和
- 美緒

Only YURA currently has a connected character runtime path. Other MEMORIELA characters must not silently fall back to FREE or YURA.

## Runtime path

```text
local-RAG.exe
  -> Local Controller / Backend
  -> Domain Router (FREE / MEMORIELA)
  -> Shared Rendering
  -> Generation Compiler
  -> ComfyUI API
  -> Local GPU
  -> Generated Image + Manifest
```

## Directory map

```text
src/                         application source code
ui/                          desktop UI resources
config/                      runtime/environment configuration
intent/                      natural-language intent dictionaries
profiles/                    generation profiles
workflows/                   ComfyUI API workflow templates
shared/rendering/            rendering shared by FREE and MEMORIELA
domains/free/                FREE-domain rules/assets
domains/memoriela/           MEMORIELA-domain rules/assets
  characters/                character identity/reference assets
  outfits/                   learned outfit assets/metadata
  situations/                reusable situation definitions
  backgrounds/               reusable background assets/metadata
learning/rendering/           shared-rendering dataset/training pipeline
cache/                       runtime cache
database/                    SQLite runtime database
outputs/                     generated outputs/manifests
logs/                        runtime logs
```

## Shared-rendering learning

The current learned-rendering implementation targets an SDXL LoRA trained locally with `sd-scripts` and injected into both FREE and MEMORIELA ComfyUI workflows through the standard `LoraLoader` node.

Training data and model weights are local runtime assets and are not committed to Git.

See `learning/rendering/README.md`.

## Source-of-truth separation

The external MEMORIELA repository remains the authority for MEMORIELA canon and approved character visual sources. FREE generation does not read MEMORIELA authority.

## Governing documents

- `SPEC.md` — production scope and architecture
- `GATE.md` — verification and promotion gates
- `START_HERE.md` — repository entry point

## Development rule

Code existence is not a runtime PASS. New routing, learning, LoRA activation, and generated-image behavior must be locally executed and verified before being treated as production-ready.
