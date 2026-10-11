# Local tools, Oracle knowledge store, Git reads, and reusable JSON parts

Status: **ORACLE / JSON-PART / LOCAL-AI TOOL ROUND-TRIP VERIFIED; HARDENING PENDING**

## Objective

The local AI can be given controlled local tools rather than relying only on chat context:

```text
local AI
  -> read-only Git tools
  -> read-only Oracle knowledge search
  -> exact reusable JSON-part lookup
```

Persistent writes remain explicit. The model cannot silently write Git, run arbitrary shell commands, commit/push, or mutate Oracle through the tool-call loop.

The verified Oracle path now reaches all the way through the local model:

```text
user/API request
  -> qwen3-vl:8b-instruct
  -> json_part_get tool call
  -> LocalAIToolbox
  -> Oracle LOCALRAG_KB1 / LR_JSON_PART
  -> tool result
  -> qwen3-vl:8b-instruct final answer
```

---

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

---

## Oracle Database

Dedicated Oracle Free container:

```text
container : local-rag-oracle
listener  : 127.0.0.1:1521
service   : FREEPDB1
schema    : LOCALRAG_KB1
tablespace: LOCALRAG_DATA
```

The schema is deliberately new. There is no migration from, dependency on, or reuse of the earlier AI-development schema.

Lifecycle:

```powershell
powershell -ExecutionPolicy Bypass -File .\oracle_local.ps1 -Action start
powershell -ExecutionPolicy Bypass -File .\oracle_local.ps1 -Action reset-schema
powershell -ExecutionPolicy Bypass -File .\oracle_local.ps1 -Action status
powershell -ExecutionPolicy Bypass -File .\oracle_local.ps1 -Action stop
```

`reset-schema` drops only the dedicated `LOCALRAG_KB1` user if it exists, then recreates schema v1 from `infra/oracle/sql/001_fresh_schema.sql`.

### Verified bootstrap

User-side Windows execution confirmed successful fresh bootstrap, including:

```text
[ORACLE:TABLESPACE:CREATED] LOCALRAG_DATA
[ORACLE:SCHEMA:OK] LOCALRAG_KB1 schema version 1 created from scratch.
[ORACLE:SCHEMA:OK] LOCALRAG_KB1
```

Python/oracledb health was also VERIFIED:

```text
configured=True
online=True
dsn=127.0.0.1:1521/FREEPDB1
schema=LOCALRAG_KB1
schema_version=1
```

---

## Schema v1

Tables:

```text
LR_KNOWLEDGE_ITEM  accepted/staging structured local-AI knowledge
LR_JSON_PART       reusable versioned JSON parts
LR_SOURCE_REF      provenance for Git/images/generations/etc.
LR_TOOL_AUDIT      reserved audit table for local tool execution records
LR_SCHEMA_META     schema identity/version
```

This is a clean schema definition, not the old project schema.

---

## Persistent file store

Canonical local file root:

```text
learning\local-ai\store\
  json-parts\
  knowledge\
  sources\
  staging\
```

Runtime contents are Git-ignored.

Accepted JSON parts belong in `json-parts`. Staging/nonaccepted documents belong in `staging` and are not normal generation-executable file-store parts.

Oracle is the searchable/indexed layer and can explicitly return a staging document when requested by exact ref.

---

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

Initial generation payload support:

```text
payload.generation.positive
payload.generation.negative
```

See:

```text
learning/local-ai/JSON_PARTS.md
learning/local-ai/schemas/json_part.schema.json
```

---

## Local-AI JSON responses and explicit persistence

When a local-AI response contains valid JSON, the UI can expose `JSON保存`.

For a valid `local-rag/json-part` document it can also expose `Part登録`.

Intended persistence boundary:

```text
assistant JSON
  -> explicit user action: Part登録
  -> local file store
  -> Oracle LR_JSON_PART when Oracle is online
```

No assistant response is persisted merely because it contains JSON.

The HTTP write path itself is VERIFIED through:

```text
POST /api/knowledge/json-part
```

using the isolated staging ref:

```text
part:test.oracle-roundtrip@1
```

The API returned:

```text
status: staging
oracle_indexed: True
oracle_error: empty
```

The UI button itself still requires explicit desktop/UI verification.

---

## Verified JSON Part round-trip

The following sequence is VERIFIED from user-provided local output:

```text
JSON document
  -> validate
  -> write staging file
  -> Oracle LR_JSON_PART upsert
  -> direct Oracle readback
  -> LocalAIToolbox json_part_get
  -> local AI tool call
  -> final local AI answer
```

The final LEARN answer correctly returned:

```text
ref: part:test.oracle-roundtrip@1
status: staging
part_id: test.oracle-roundtrip
part_type: test
payload.generation.positive: oracle roundtrip test
```

This test Part is intentionally nonproduction staging data.

---

## Oracle JSON representation fix

`python-oracledb` can return Oracle JSON as a native Python `dict`. `src/oracle_knowledge_store.py` must therefore not always call `json.loads()` on `DOCUMENT_JSON`.

Verified fix commit:

```text
fdb8cb8abaafd1931ef8d7ae20b95748f5de657d
```

A second debugging problem was also fixed: `json_part_get` previously swallowed Oracle exceptions and silently fell back to the accepted file-store path. That made an Oracle failure appear as a normal "part not found".

Fix commit:

```text
4a6880701734902b6193bdd89f56f9788ee12ae7
```

The tool now allows the real Oracle failure to surface instead of hiding it behind fallback behavior.

### Server-process caution

After modifying imported Python modules, restart `ui_server.py`. A running Python process keeps the old imported code and does not automatically hot-reload it.

---

## SHA-256 note

The local API file SHA and Oracle `CONTENT_SHA256` can differ even when the JSON content is semantically the same.

Current behavior:

```text
file SHA   -> hash of pretty JSON file bytes + newline
Oracle SHA -> hash of canonical compact/sorted JSON
```

This is expected under the current implementation and is not by itself a round-trip failure.

---

## Git access

Configured in `config/local_tools.json`.

Current actions are read-only:

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

`GET /api/local-tools/status` is VERIFIED and reports:

```text
git.read_only: true
configured_repositories:
  - local-image-generator
  - memoriela
oracle.configured: true
oracle.online: true
oracle.schema: LOCALRAG_KB1
oracle.schema_version: 1
```

Do not infer that every Git tool action has been individually exercised through Qwen merely from the status endpoint; this checkpoint's complete model-tool round-trip verification was for Oracle `json_part_get`.

---

## Local AI endpoints

Backend endpoints:

```text
GET  /api/local-tools/status
POST /api/local-ai/tool-chat
POST /api/knowledge/json-part
```

Role permissions in `config/local_tools.json` determine which tools the model can see.

Current role intent:

```text
generate -> knowledge_search, json_part_get
learn    -> knowledge_search, json_part_get, selected read-only Git tools
dev      -> read-only Git tools + Oracle knowledge/json-part reads
```

---

## Current security / hardening boundary

Still required before moving on to the persistent-learning producer workflow:

1. Remove `part:test.oracle-roundtrip@1` with a narrow cleanup mechanism that deletes only the intended staging file/row.
2. Rotate the Oracle application password that appeared in an earlier failed reset log. Never print the replacement secret.
3. Turn this verified round-trip into a one-command isolated integration smoke test that cleans up its own test data.

Do not solve these by giving the local AI unrestricted SQL or arbitrary shell access.

---

## Continuation rule

For a new chat/session:

1. Read `START_HERE.md`.
2. Read `docs/assistant-context/LOCAL_RAG_CURRENT_STATE.md` completely.
3. Do not rebuild Oracle connectivity from scratch: schema, Python health, JSON-Part write/read, LocalAIToolbox read, and Qwen->Oracle tool call are already VERIFIED.
4. Continue from cleanup/hardening unless the user changes priority.
5. Preserve read-only Git, narrow explicit DB writes, staging/accepted separation, and user-side runtime verification.
