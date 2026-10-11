# local-RAG — START HERE

Status: **ACTIVE LOCAL IMAGE GENERATION APPLICATION**

This repository is the production development root for the Windows desktop application `local-RAG`.

## New chat / continuation entry point

Before changing architecture or implementation, read exactly this continuation document first:

```text
docs/handoff/LOCAL_RAG_HANDOFF.md
```

That file is the **single authoritative handoff** for:

- current architecture direction;
- VERIFIED / UNVERIFIED runtime state;
- exact next implementation order;
- FREE / MEMORIELA / LEARN responsibility split;
- JSON Part state;
- ComfyUI diagnostic findings;
- Oracle/local-AI verification state;
- anti-drift development rules.

After reading it, inspect the current Git `main` before editing. Repository state overrides old chat memory.

## Current top-level direction

The desktop application keeps the local AI subsystem, but generation responsibilities are being separated:

```text
FREE
  -> deterministic generation
  -> no Qwen prompt rewrite / no Qwen pre-generation asset selection
  -> exact prompt + explicitly referenced JSON Parts

MEMORIELA
  -> local AI remains for canon/request interpretation and controlled planning
  -> resolved plan executes through the common deterministic generation engine

LEARN
  -> local AI remains for image/text analysis and JSON Part candidate creation
  -> explicit user acceptance before persistent reuse
```

This split is the current **target design**. The existing code still contains generation-side AI selection that must be bypassed/refactored for FREE; do not claim the new split is already complete.

## Core identities

```text
application/repo: local-RAG / Pin-Gin/local-image-generator
local root:       C:\Dev\local-image-generator
canon authority:  Pin-Gin/MEMORIELA
local canon clone: C:\Dev\MEMORIELA
```

`MEMORIELA` is not the generic application/build/storage name.

## Current configured runtime endpoints

```text
ComfyUI: http://127.0.0.1:8188
Ollama:  http://127.0.0.1:11435
Oracle:  127.0.0.1:1521/FREEPDB1
```

Current app database path:

```text
database/local_rag.db
```

Current application output root:

```text
outputs/
```

## Governing/reference documents

Primary continuation source:

```text
docs/handoff/LOCAL_RAG_HANDOFF.md
```

Specialized references:

```text
SPEC.md
GATE.md
learning/local-ai/JSON_PARTS.md
docs/local-ai/README.md
docs/local-ai/LOCAL_TOOLS_AND_ORACLE.md
docs/local-ai/GENERATION_ASSISTANT.md
learning/rendering/README.md
```

Specialized documents do not override a newer user-approved architecture decision recorded in the consolidated handoff. If they conflict, update them rather than silently reverting direction.

## Development rule

Code existence is not runtime PASS. A behavior is VERIFIED only from user-supplied local execution evidence.

After modifying Python imported by a running `ui_server.py`, restart that process before testing the new code.
