# local-RAG — START HERE

Status: **ACTIVE LOCAL IMAGE GENERATION APPLICATION**

This repository is the production development root for the local-RAG desktop image-generation application.

## Continuation checkpoint

Before continuing implementation in a new chat/session, read:

`docs/assistant-context/LOCAL_RAG_CURRENT_STATE.md`

and then:

`docs/local-ai/README.md`

The first file records the rendering/generation checkpoint; the second records the newer local-AI runtime, verified chat/vision state, and the current mode-switch UI implementation.

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
       learned rendering LoRA when trained/activated
```

Natural-language names currently routed to MEMORIELA:
- ゆら / 久遠ゆら
- 要 / 水瀬要
- 栞
- 大和
- 美緒

Only YURA currently has a connected character runtime path. Other MEMORIELA characters must not silently fall back to FREE or YURA.

## Runtime paths

Generation:

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

Local AI:

```text
local-RAG backend
  -> project-local Ollama API on 127.0.0.1:11435
       -> LEARN: qwen3-vl:8b-instruct
       -> DEV: qwen2.5-coder:14b
```

LEARN runtime, text chat, and vision inference are user-verified locally. DEV remains a configured but not yet locally verified role.

## Desktop mode UI

The UI now has a top-level dropdown mode selector modeled after the requested ChatGPT-style switcher:

```text
画像生成
学習
開発
```

Current implementation state:

- 画像生成: existing generation UI/path;
- 学習: image upload + preview + local vision/chat foundation;
- 開発: local chat foundation only;
- persistent dataset registration/training from UI: not implemented yet;
- DEV filesystem/Git/shell/test/build execution: not implemented yet.

The new mode-switch/image-upload UI code exists in Git but still requires local desktop build/run verification.

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
docs/local-ai/               local AI runtime/setup/API/UI documentation
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

The project-local AI runtime and its verification boundary are documented in:

`docs/local-ai/README.md`

Important: vision transport/inference is verified, but the model is not an authority. The first successful visual analysis contained at least one overconfident spatial detail. User confirmation remains required before future dataset registration/training decisions.

## Source-of-truth separation

The external MEMORIELA repository remains the authority for MEMORIELA canon and approved character visual sources. FREE generation does not read MEMORIELA authority.

## Governing documents

- `docs/assistant-context/LOCAL_RAG_CURRENT_STATE.md` — rendering/generation continuation checkpoint
- `docs/local-ai/README.md` — newer project-local AI runtime/setup/API/UI state
- `SPEC.md` — production scope and architecture
- `GATE.md` — verification and promotion gates
- `START_HERE.md` — repository entry point

## Development rule

Code existence is not a runtime PASS. New routing, learning, LoRA activation, local-AI behavior, UI behavior, and generated-image behavior must be locally executed and verified before being treated as production-ready.
