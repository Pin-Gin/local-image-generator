# local-RAG — START HERE

Status: **ACTIVE LOCAL IMAGE GENERATION APPLICATION**

This repository is the production development root for the local-RAG desktop image-generation application.

## Continuation checkpoint

Before continuing implementation in a new chat/session, read in this order:

1. `docs/assistant-context/LOCAL_RAG_CURRENT_STATE.md`
2. `docs/local-ai/LOCAL_TOOLS_AND_ORACLE.md`
3. `docs/local-ai/README.md`

The current stopping point is recorded in `LOCAL_RAG_CURRENT_STATE.md`. As of the 2026-10-11 checkpoint, the end-to-end local-AI Oracle JSON-Part tool path is **user-verified**. Do not restart that work from first principles unless a regression appears.

The immediate continuation is cleanup/hardening of that verified environment, then closure of remaining implemented-but-unverified paths, then the persistent LEARN producer workflow.

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
       -> Oracle knowledge / JSON-part reads
       -> explicit narrow JSON-part registration writes
```

Verified local-AI/tool milestone:

```text
Qwen LEARN
  -> json_part_get
  -> LocalAIToolbox
  -> Oracle LOCALRAG_KB1 / LR_JSON_PART
  -> tool result
  -> final Qwen answer
```

LEARN runtime, text chat, vision inference, Oracle schema connectivity, JSON-Part write/read round-trip, LocalAIToolbox Oracle read, and the Qwen->Oracle tool-call answer path are user-verified locally.

DEV remains a configured model role and may require local model installation/verification.

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
tablespace: LOCALRAG_DATA
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
- 開発: local chat/planning foundation;
- local AI JSON responses: copy + JSON download; `local-rag/json-part` responses can be explicitly registered;
- local AI Git/Oracle tool layer: controlled/read-oriented tool calling; Oracle path verified;
- persistent dataset registration/training/publish lifecycle: not production-complete yet;
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
infra/oracle/                 Oracle Free local database definition/schema
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

Project-local Ollama:

```powershell
powershell -ExecutionPolicy Bypass -File .\local_ai.ps1 -Action start
powershell -ExecutionPolicy Bypass -File .\local_ai.ps1 -Action status
```

## Shared-rendering learning

The current learned-rendering implementation targets an SDXL LoRA trained locally with `sd-scripts` and injected into both FREE and MEMORIELA ComfyUI workflows through the standard `LoraLoader` node.

Training data and model weights are local runtime assets and are not committed to Git.

See `learning/rendering/README.md`.

## Source-of-truth separation

The external MEMORIELA repository remains the authority for MEMORIELA canon and approved character visual sources. FREE generation does not read MEMORIELA semantic assets. Read-only Git tools may inspect configured repositories for explicit local-AI work, but inspection does not change generation-domain ownership.

## Governing documents

- `docs/assistant-context/LOCAL_RAG_CURRENT_STATE.md` — primary continuation checkpoint, verified/unverified matrix, exact next work
- `docs/local-ai/LOCAL_TOOLS_AND_ORACLE.md` — Git/Oracle/JSON-part tool contract and verified round-trip
- `docs/local-ai/README.md` — project-local Ollama/model/runtime/UI documentation
- `learning/local-ai/JSON_PARTS.md` — reusable JSON part naming/composition contract
- `SPEC.md` — production scope and architecture
- `GATE.md` — verification and promotion gates
- `START_HERE.md` — repository entry point

## Development rules

Code existence is not a runtime PASS. Local behavior is VERIFIED only from user-supplied execution output.

Do not silently widen tool permissions, merge FREE/MEMORIELA semantics, treat Vision analysis as ground truth, auto-promote staging knowledge, or claim that an uploaded image is persistently learned before the producer lifecycle actually completes.

After editing imported Python while `ui_server.py` is running, restart that server before testing the change.
