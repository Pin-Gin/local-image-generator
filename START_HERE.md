# local-RAG — START HERE

Status: **ACTIVE LOCAL IMAGE GENERATION APPLICATION**

This repository is the production development root for the local-RAG desktop image-generation application.

## Continuation checkpoint

Before continuing implementation in a new chat/session, read:

`docs/assistant-context/LOCAL_RAG_CURRENT_STATE.md`

It records the latest verified local state, completed implementation, unresolved defects, open specifications, and the intended continuation direction after the first successful learned-rendering LoRA training and LoRA-backed FREE generation.

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

A separate project-local AI runtime is being added for future LEARN and DEV modes:

```text
local-RAG backend
  -> project-local Ollama API on 127.0.0.1:11435
       -> LEARN: qwen3-vl:8b
       -> DEV: qwen2.5-coder:14b
```

This local-AI path is currently an implemented foundation that still requires user-side runtime verification. It does not replace ComfyUI generation.

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
docs/local-ai/               local AI runtime/setup/API documentation
docs/assistant-context/      continuation/handoff state for future sessions
tools/ollama/                project-local Ollama runtime/models (Git-ignored)
cache/                       runtime cache
database/                    SQLite runtime database
outputs/                     generated outputs/manifests
logs/                        runtime logs
```

## Shared-rendering learning

The current learned-rendering implementation targets an SDXL LoRA trained locally with `sd-scripts` and injected into both FREE and MEMORIELA ComfyUI workflows through the standard `LoraLoader` node.

Training data and model weights are local runtime assets and are not committed to Git.

See `learning/rendering/README.md`.

## Local AI

The project-local AI runtime is documented in:

`docs/local-ai/README.md`

The browser mode-switch UI and image-upload learning workflow are not yet complete. Establish and locally verify the runtime/API before promoting those features to VERIFIED.

## Source-of-truth separation

The external MEMORIELA repository remains the authority for MEMORIELA canon and approved character visual sources. FREE generation does not read MEMORIELA authority.

## Governing documents

- `docs/assistant-context/LOCAL_RAG_CURRENT_STATE.md` — latest continuation checkpoint and verification state
- `docs/local-ai/README.md` — project-local AI runtime/setup/API contract
- `SPEC.md` — production scope and architecture
- `GATE.md` — verification and promotion gates
- `START_HERE.md` — repository entry point

## Development rule

Code existence is not a runtime PASS. New routing, learning, LoRA activation, local-AI behavior, and generated-image behavior must be locally executed and verified before being treated as production-ready.
