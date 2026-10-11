# Local tools, Oracle knowledge store, Git reads, and reusable JSON parts

Status: **ORACLE / JSON-PART / LOCAL-AI TOOL ROUND-TRIP + HARDENING VERIFIED**

For the authoritative continuation state, read:

```text
docs/handoff/LOCAL_RAG_HANDOFF.md
```

## Objective

The local AI can use controlled local tools instead of relying only on chat context:

```text
local AI
  -> read-only Git tools
  -> read-only Oracle knowledge search
  -> exact reusable JSON-Part lookup
```

Persistent writes remain explicit. The model cannot silently write Git, run arbitrary shell commands, commit/push, or mutate Oracle through the normal tool-call loop.

Verified Oracle model-tool path:

```text
user/API request
  -> qwen3-vl:8b-instruct
  -> json_part_get
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

This installs/configures the project Python Oracle dependency, local store directories, Git-ignored `.env.local-ai`, and MEMORIELA local-root detection where available.

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

The schema is deliberately separate from the earlier AI-development schema.

Lifecycle:

```powershell
powershell -ExecutionPolicy Bypass -File .\oracle_local.ps1 -Action start
powershell -ExecutionPolicy Bypass -File .\oracle_local.ps1 -Action status
powershell -ExecutionPolicy Bypass -File .\oracle_local.ps1 -Action reset-schema
powershell -ExecutionPolicy Bypass -File .\oracle_local.ps1 -Action rotate-app-password
powershell -ExecutionPolicy Bypass -File .\oracle_local.ps1 -Action stop
```

`rotate-app-password` changes only the dedicated application credential, verifies it, updates `.env.local-ai` without printing the new secret, and requires running server processes to restart afterward so they reload the environment.

### Verified health

User-side verification established:

```text
configured=True
online=True
dsn=127.0.0.1:1521/FREEPDB1
schema=LOCALRAG_KB1
schema_version=1
```

Oracle app-password rotation has also been **VERIFIED**. Never repeat an older credential that appeared in historical logs.

---

## Schema v1

```text
LR_KNOWLEDGE_ITEM  accepted/staging structured local-AI knowledge
LR_JSON_PART       reusable versioned JSON parts
LR_SOURCE_REF      provenance for Git/images/generations/etc.
LR_TOOL_AUDIT      reserved audit table
LR_SCHEMA_META     schema identity/version
```

Do not claim `LR_TOOL_AUDIT` is populated merely because the table exists.

---

## Persistent file store

```text
learning\local-ai\store\
  json-parts\
  knowledge\
  sources\
  staging\
```

Accepted generation Parts belong in `json-parts`. Staging/nonaccepted canonical documents belong in `staging`.

Manual structured JSON compatibility is documented separately in:

```text
learning/local-ai/JSON_PARTS.md
```

Manual compatibility files placed directly in accepted `json-parts` are local-file generation assets; they are not automatically written to Oracle.

---

## Canonical reusable JSON Parts

Reference:

```text
part:<part_id>@<version>
```

Canonical persistence path:

```text
assistant/app JSON candidate
  -> explicit user action
  -> validate canonical local-rag/json-part
  -> local accepted/staging file
  -> Oracle LR_JSON_PART when configured
```

No model response is persisted merely because it contains JSON.

The HTTP persistence route:

```text
POST /api/knowledge/json-part
```

is VERIFIED through an isolated staging test.

The latest explicit desktop `Part採用` interaction remains IMPLEMENTED / UNVERIFIED; backend persistence itself is VERIFIED.

---

## Verified JSON Part / Oracle round-trip

Verified sequence:

```text
JSON document
  -> validation
  -> staging file
  -> Oracle LR_JSON_PART upsert
  -> direct Oracle readback
  -> LocalAIToolbox json_part_get
  -> local AI tool call
  -> final local AI answer
```

The isolated verification ref used historically was:

```text
part:test.oracle-roundtrip@1
```

The user later ran the narrow cleanup successfully, so this historical test ref should not be treated as intentional current residue.

---

## Verified cleanup hardening

A narrow cleanup mechanism exists specifically for `test.*` staging Parts. It refuses production/nonstaging Parts.

User-verified output included:

```text
[TEST-CLEANUP:ORACLE] deleted=True reason=deleted
[TEST-CLEANUP:FILE] deleted=True
[TEST-CLEANUP:OK]
```

Relevant implementation:

```text
src/cleanup_test_json_part.py
src/oracle_knowledge_store.py::delete_staging_test_json_part
```

---

## One-command integration verification — VERIFIED

Use:

```powershell
cd C:\Dev\local-image-generator
.\verify_local_stack.ps1
```

This ensures Oracle and project-local Ollama are running, then creates a disposable staging Part and verifies:

```text
Oracle health
Oracle upsert
Oracle readback
read-only Git status
LocalAIToolbox json_part_get
Qwen tool call consuming the Oracle result
cleanup of the disposable Oracle row/file
```

User-verified successful markers included:

```text
[INTEGRATION:ORACLE:OK]
[INTEGRATION:UPSERT:OK]
[INTEGRATION:READBACK:OK]
[INTEGRATION:GIT-READ:OK]
[INTEGRATION:TOOLBOX:OK]
[INTEGRATION:LOCAL-AI-TOOL:OK]
[LOCAL-STACK:INTEGRATION:OK]
[INTEGRATION:CLEANUP:OK]
[VERIFY:LOCAL-STACK:OK]
```

Do not re-bootstrap the whole Oracle/local-AI stack from first principles unless this integration test or a narrower diagnostic actually shows a regression.

---

## Important Oracle JSON fixes

`python-oracledb` can return Oracle JSON as a native Python `dict`; the store must not blindly call `json.loads()` on an already-decoded dict.

Fix commit:

```text
fdb8cb8abaafd1931ef8d7ae20b95748f5de657d
```

`json_part_get` also used to swallow Oracle exceptions and fall back to file lookup, masking a real database error as `part not found`. That masking behavior was removed.

Fix commit:

```text
4a6880701734902b6193bdd89f56f9788ee12ae7
```

After modifying imported Python modules, restart `ui_server.py` before retesting.

---

## SHA-256 note

File SHA and Oracle `CONTENT_SHA256` can differ by design:

```text
file SHA   -> hash of pretty JSON file bytes/newline
Oracle SHA -> hash of canonical compact/sorted JSON
```

This difference alone is not corruption.

---

## Git access

Configured in:

```text
config/local_tools.json
```

Current Git actions are read-only:

```text
git_status
git_log
git_diff
git_list_files
git_read_file
git_search
```

Configured repositories include:

```text
local-image-generator
memoriela
```

Do not broaden this to checkout/reset/commit/push/arbitrary shell merely to simplify development.

`GET /api/local-tools/status` is VERIFIED and reports the controlled Git boundary plus Oracle online state.

Do not infer that every Git tool action has been individually exercised through Qwen; the fully verified model-tool round-trip is the Oracle `json_part_get` path.

---

## Local AI endpoints

```text
GET  /api/local-tools/status
POST /api/local-ai/tool-chat
POST /api/knowledge/json-part
```

Role permissions are controlled by `config/local_tools.json`.

The user-approved architecture now separates FREE generation from Qwen pre-generation selection. That generation-routing decision does not change the read-only Git/Oracle security boundary documented here.

---

## Continuation rule

For any new chat/session:

1. Read `START_HERE.md`.
2. Read `docs/handoff/LOCAL_RAG_HANDOFF.md` completely.
3. Treat this file as the subsystem reference, not a separate continuation checkpoint.
4. Preserve read-only Git, narrow explicit DB writes, staging/accepted separation, secret handling, and user-side runtime verification.
