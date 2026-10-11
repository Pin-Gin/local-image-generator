# local-RAG — START HERE

Status: **ACTIVE LOCAL IMAGE GENERATION APPLICATION**

This repository is the production development root for the local-RAG desktop image-generation application.

## Continuation checkpoint

Before continuing implementation in a new chat/session, read:

`docs/assistant-context/LOCAL_RAG_CURRENT_STATE.md`

and then:

`docs/local-ai/README.md`

For the new Git / Oracle / reusable-JSON tool layer, also read:

`docs/local-ai/LOCAL_TOOLS_AND_ORACLE.md`

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
user input
  -> request/domain routing
  -> local AI learned-asset selection
  -> Learning Registry
  -> reusable JSON parts (when explicitly referenced)
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
       -> GENERATE: qwen3-vl:8b-instruct
       -> LEARN:    qwen3-vl:8b-instruct
       -> DEV:      qwen2.5-coder:14b
  -> controlled local tools
       -> read-only Git
       -> read-only Oracle knowledge queries
       -> reusable JSON-part lookup
```

LEARN runtime, text chat, and vision inference are user-verified locally. The new Git/Oracle tool-calling layer is implemented but requires local verification. DEV remains a configured model role and may require local model installation/verification.

## Persistent local-AI knowledge

Runtime file store:

```text
learning/local-ai/store/
  json-parts/
  knowledge/
  sources/
  staging/
```

Oracle searchable/indexed store:

```text
Oracle Free / FREEPDB1
schema: LOCALRAG_KB1
```

This Oracle schema is new and does not reuse the previous AI-development schema.

Reusable JSON part reference:

```text
part:<part_id>@<version>
```

Example:

```text
part:pose.hair-touch@1
```

See `learning/local-ai/JSON_PARTS.md`.

## Desktop mode UI

The UI has a top-level dropdown mode selector:

```text
画像生成
学習
開発
```

Current implementation state:

- 画像生成: existing generation UI/path plus pre-generation learned-asset selection;
- 学習: image upload + preview + local vision/chat foundation;
- 開発: local chat foundation;
- local AI JSON responses: copy + JSON download; `local-rag/json-part` responses can be explicitly registered;
- local AI Git/Oracle tool calls: implemented as read-only tools;
- persistent dataset registration/training from UI: not production-complete yet;
- DEV file writes/Git writes/arbitrary shell/test/build execution: not enabled.

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
learning/rendering/           shared-rendering dataset/training pipeline
learning/registry/            generation-time learned asset registry
learning/local-ai/            persistent local-AI store contract / JSON parts
infra/oracle/                 new Oracle Free local database definition/schema
docs/local-ai/               local AI runtime/setup/API/UI documentation
docs/assistant-context/      continuation/handoff state for future sessions
tools/ollama/                project-local Ollama runtime/models (Git-ignored)
cache/                       runtime cache
database/                    existing generation SQLite runtime database
outputs/                     generated outputs/manifests
logs/                        runtime logs
```

## Local tool setup

```powershell
powershell -ExecutionPolicy Bypass -File .\setup_local_tools.ps1
```

If Git/Docker Desktop must be installed:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup_local_tools.ps1 -InstallSystemTools
```

Oracle lifecycle:

```powershell
powershell -ExecutionPolicy Bypass -File .\oracle_local.ps1 -Action start
powershell -ExecutionPolicy Bypass -File .\oracle_local.ps1 -Action reset-schema
powershell -ExecutionPolicy Bypass -File .\oracle_local.ps1 -Action status
```

## Shared-rendering learning

The current learned-rendering implementation targets an SDXL LoRA trained locally with `sd-scripts` and injected into both FREE and MEMORIELA ComfyUI workflows through the standard `LoraLoader` node.

Training data and model weights are local runtime assets and are not committed to Git.

See `learning/rendering/README.md`.

## Source-of-truth separation

The external MEMORIELA repository remains the authority for MEMORIELA canon and approved character visual sources. FREE generation does not read MEMORIELA semantic assets. Read-only Git tools may inspect configured repositories for explicit local-AI work, but inspection does not change generation-domain ownership.

## Governing documents

- `docs/assistant-context/LOCAL_RAG_CURRENT_STATE.md` — continuation checkpoint
- `docs/local-ai/README.md` — project-local AI runtime/setup/API/UI state
- `docs/local-ai/LOCAL_TOOLS_AND_ORACLE.md` — Git/Oracle/JSON-part tool foundation
- `learning/local-ai/JSON_PARTS.md` — reusable JSON part naming/composition contract
- `SPEC.md` — production scope and architecture
- `GATE.md` — verification and promotion gates
- `START_HERE.md` — repository entry point

## Development rule

Code existence is not a runtime PASS. New routing, learning, LoRA activation, local-AI tool behavior, Oracle behavior, UI behavior, and generated-image behavior must be locally executed and verified before being treated as production-ready.
