# Local tools, Oracle knowledge store, Git reads, and reusable JSON parts

Status: **IMPLEMENTED FOUNDATION / LOCAL VERIFICATION REQUIRED**

## Objective

The local AI can now be given controlled local tools rather than relying only on chat context:

```text
local AI
  -> read-only Git tools
  -> read-only Oracle knowledge search
  -> exact reusable JSON-part lookup
```

Persistent writes remain explicit. The model cannot silently write Git, run arbitrary shell commands, commit/push, or mutate Oracle through the tool-call loop.

## Tool installation

From `C:\Dev\local-image-generator`:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup_local_tools.ps1
```

This:

- installs `python-oracledb` into the available project Python;
- creates `learning\local-ai\store\...` runtime directories;
- creates a Git-ignored `.env.local-ai` with generated local Oracle passwords if missing;
- auto-detects a sibling `C:\Dev\MEMORIELA` clone when present.

If Git or Docker Desktop is missing:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup_local_tools.ps1 -InstallSystemTools
```

Docker Desktop installation can require a restart / first-run initialization before Oracle can start.

## Oracle Database

The project uses a dedicated Oracle Free container:

```text
container: local-rag-oracle
listener : 127.0.0.1:1521
service  : FREEPDB1
schema   : LOCALRAG_KB1
```

The schema is deliberately new. There is no migration from, dependency on, or reuse of the earlier AI-development schema.

Start Oracle and create the schema:

```powershell
powershell -ExecutionPolicy Bypass -File .\oracle_local.ps1 -Action start
powershell -ExecutionPolicy Bypass -File .\oracle_local.ps1 -Action reset-schema
```

`reset-schema` drops only the dedicated `LOCALRAG_KB1` user if it already exists, then recreates the schema from `infra/oracle/sql/001_fresh_schema.sql`.

Status:

```powershell
powershell -ExecutionPolicy Bypass -File .\oracle_local.ps1 -Action status
```

Stop without deleting the Oracle named volume:

```powershell
powershell -ExecutionPolicy Bypass -File .\oracle_local.ps1 -Action stop
```

## New schema v1

Tables:

```text
LR_KNOWLEDGE_ITEM  accepted/staging structured local-AI knowledge
LR_JSON_PART       reusable versioned JSON parts
LR_SOURCE_REF      provenance for Git/images/generations/etc.
LR_TOOL_AUDIT      reserved audit table for local tool execution records
LR_SCHEMA_META     schema identity/version
```

This is a clean schema definition, not the old project schema.

## Persistent file store

Canonical local file root:

```text
learning\local-ai\store\
  json-parts\
  knowledge\
  sources\
  staging\
```

Runtime contents are Git-ignored. The file store is the durable local source for accepted JSON parts/source assets; Oracle is the searchable/indexed knowledge layer.

## Reusable JSON parts

Canonical reference:

```text
part:<part_id>@<version>
```

Example:

```text
part:pose.hair-touch@1
```

Generation input can reuse exact parts:

```json
{
  "positive": "silver-haired woman standing outdoors",
  "parts": [
    "part:pose.hair-touch@1",
    "part:camera.three-quarter@2"
  ]
}
```

The initial runtime supports `payload.generation.positive` and `payload.generation.negative`. The resolved exact version, file path, and SHA-256 are copied into the generation request for reproducibility.

See:

```text
learning/local-ai/JSON_PARTS.md
learning/local-ai/schemas/json_part.schema.json
```

## Local-AI JSON responses

When a local-AI response contains a valid JSON object/array, the UI adds:

```text
JSON保存
```

For a valid `local-rag/json-part` document it also adds:

```text
Part登録
```

`Part登録` is the explicit persistent-write action:

```text
assistant JSON
  -> user presses Part登録
  -> local file store
  -> Oracle LR_JSON_PART when Oracle is online
```

No assistant response is persisted merely because it contains JSON.

## Git access

Configured in `config/local_tools.json`.

Current tools are read-only:

```text
git_status
git_log
git_diff
git_list_files
git_read_file
git_search
```

Allowed repositories:

```text
local-image-generator : current project clone
memoriela             : LOCALRAG_MEMORIELA_ROOT from .env.local-ai
```

The tool layer does not expose Git write, checkout, reset, commit, push, or arbitrary shell execution.

## Local AI tool endpoint

The backend now exposes:

```text
GET  /api/local-tools/status
POST /api/local-ai/tool-chat
POST /api/knowledge/json-part
```

The UI routes generation-assistant, LEARN, and DEV chat through `tool-chat`. Role permissions in `config/local_tools.json` determine which tools the model can see.

## Verification

After setup:

```powershell
python .\src\local_tools_smoke.py --require-oracle
```

Expected final line:

```text
[LOCAL-TOOLS:SMOKE:OK]
```

This document must remain **LOCAL VERIFICATION REQUIRED** until the user runs the scripts successfully on Windows.
