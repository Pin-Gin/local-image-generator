# local-RAG — Current State / Continuation Handoff

Last checkpoint: **2026-10-11 19:10 JST**

Read `START_HERE.md` first, then this file completely before changing architecture or implementation.

This document is the primary handoff for a new chat/session. It records not only what exists, but what the user actually verified locally and the development method that must be preserved.

Status vocabulary:

- **VERIFIED** — the user supplied successful local runtime evidence;
- **IMPLEMENTED / UNVERIFIED** — code exists in Git, but the current path has not been locally confirmed;
- **NOT IMPLEMENTED** — no completed runtime path yet;
- **OPEN SPEC** — design choice is not fixed yet.

Never promote an UNVERIFIED item merely because code exists.

---

## 1. Product direction and source-of-truth boundaries

`local-RAG` is the Windows desktop application and repository/build identity.

`MEMORIELA` is an external canon / approved visual-authority repository. It must not become the generic application name or generic storage root.

Generation domains remain separated:

```text
FREE
  generic natural-language / JSON image generation
  no MEMORIELA identity/outfit/background authority

MEMORIELA
  named cast -> controlled character generation
  character / outfit / pose / expression / situation / background / camera are modular concerns

SHARED RENDERING
  Matte Dimensional Anime
  character-independent
  applied to FREE and MEMORIELA
```

Current generation objective:

```text
User input
  -> deterministic FREE / MEMORIELA routing
  -> local AI checks registered learned assets
  -> if a relevant registered asset exists, select exact asset ID(s)
  -> generation plan
  -> compiler
  -> ComfyUI
  -> image
  -> optional local-AI visual QA / learning discussion
```

The local AI must not silently rewrite the user's request, invent assets, or claim persistence/training that did not occur.

---

## 2. Development method that must be preserved

New chats/sessions must continue with the same working method:

1. Read `START_HERE.md` and this checkpoint before editing.
2. Inspect current Git `main` before assuming file state.
3. Prefer the repository implementation over chat memory when they differ.
4. Keep changes incremental and narrowly scoped.
5. After each meaningful runtime change, give the user one concrete local verification command/path.
6. Treat only the user's actual local output as runtime PASS evidence.
7. When a failure occurs, identify the failing layer first; do not restart/reinstall unrelated components by reflex.
8. Preserve controlled tool boundaries: local-AI Git access remains read-only; no arbitrary shell or implicit DB writes.
9. Persistent writes require an explicit application/user action. AI text alone does not register knowledge.
10. Prefer automated end-to-end workflows over manual ComfyUI node construction.
11. Keep project-created tooling under `C:\Dev\local-image-generator` unless an already-existing external runtime is explicitly used.
12. Do not expose or repeat local passwords/secrets in documentation or chat output.
13. After changing imported Python code while `ui_server.py` is already running, restart that server before judging the new behavior; the existing process retains the old module code.
14. Preserve the distinction between analysis, staging, acceptance, dataset registration, training, publishing, registry activation, and generation-time use.

The user's role in verification is deliberate: Git/code can be changed remotely, but Windows/GPU/runtime behavior is confirmed from the user's machine.

---

## 3. Verified local base environment

### ComfyUI — VERIFIED

```text
ComfyUI: 0.39.0
Python: 3.13.14 embedded
PyTorch: 2.14.0+cu130
GPU: NVIDIA GeForce RTX 5080
VRAM: 16275 MB
API/UI: http://127.0.0.1:8188
```

ComfyUI root:

```text
C:\Users\shift\Downloads\ComfyUI_windows_portable_nvidia\ComfyUI_windows_portable
```

SDXL Base:

```text
C:\Users\shift\Downloads\ComfyUI_windows_portable_nvidia\ComfyUI_windows_portable\ComfyUI\models\checkpoints\sd_xl_base_1.0.safetensors
```

### Rendering-LoRA training runtime — VERIFIED

Project-owned tooling:

```text
C:\Dev\local-image-generator\tools\python312
C:\Dev\local-image-generator\tools\sd-scripts
C:\Dev\local-image-generator\tools\sd-scripts\venv
C:\Dev\local-image-generator\tools\_downloads
```

Verified:

```text
Python 3.12.10
PyTorch 2.8.0+cu128
CUDA True
NVIDIA GeForce RTX 5080
```

### Project-local Ollama / Qwen — VERIFIED

```text
runtime: C:\Dev\local-image-generator\tools\ollama\ollama.exe
models : C:\Dev\local-image-generator\tools\ollama\models\
API    : http://127.0.0.1:11435
```

Verified LEARN model:

```text
qwen3-vl:8b-instruct
```

Text inference and direct Vision inference are VERIFIED. Vision output is analysis evidence, not ground truth; it has previously overclaimed spatial/finger details.

DEV is configured for `qwen2.5-coder:14b`, but current model installation/runtime has not been verified in this checkpoint.

---

## 4. Shared rendering — VERIFIED core path

Source:

```text
shared/rendering/matte_dimensional_anime.json
```

Training dataset/run:

```text
20 images
folder: learning/rendering/dataset/20_mdanime
5 epochs
2000 steps
```

Verified completion:

```text
2000/2000
avr_loss=0.142
[LEARNING:TRAIN:OK]
```

The trained Matte Dimensional Anime LoRA was used in an actual FREE generation after Windows ComfyUI `LoraLoader` selector-name normalization was fixed.

Manual evaluation of that sample:

```text
rendering / dimensionality : PASS
anime retention            : PASS
depth                       : PASS
hand/finger anatomy         : FAIL
```

The hand failure is a pose/anatomy concern, not a reason by itself to retrain the rendering LoRA.

The `.safetensors` model remains a local runtime artifact and is not committed to Git.

---

## 5. Desktop modes and local AI UI

Top-level selector:

```text
画像生成
学習
開発
```

### 画像生成

Existing FREE / MEMORIELA generation UI plus generation-side local AI assistance.

### 学習

Implemented foundation includes:

- image upload and preview;
- drag/drop intake;
- Windows screenshot clipboard intake (`Ctrl+V`);
- copy button on local-AI replies;
- image discussion using `qwen3-vl:8b-instruct`;
- JSON response download;
- explicit JSON Part registration action.

LEARN context configuration:

```text
num_ctx: 16384
num_predict: 1024
max_history_messages: 6
```

Direct CLI Vision is VERIFIED. Some latest pywebview UI interaction paths remain IMPLEMENTED / UNVERIFIED until explicitly retested.

### 開発

DEV remains planning/chat oriented. Filesystem writes, Git writes, arbitrary shell, test execution, and build execution are NOT enabled for the local AI.

---

## 6. Reusable JSON Part contract — IMPLEMENTED

Canonical ref:

```text
part:<part_id>@<version>
```

Example:

```text
part:pose.hair-touch@1
```

Contract/runtime files include:

```text
learning/local-ai/JSON_PARTS.md
learning/local-ai/schemas/json_part.schema.json
src/json_parts.py
```

Generation JSON can reference exact reusable parts rather than flattening everything into one prompt.

Accepted parts belong in:

```text
learning/local-ai/store/json-parts/
```

Staging/nonaccepted parts belong in:

```text
learning/local-ai/store/staging/
```

Important: staging parts are not normal generation-executable file-store parts. They can still exist in Oracle for explicit inspection/testing.

---

## 7. Oracle / local-tools foundation — VERIFIED through local-AI tool call

### Infrastructure — VERIFIED

Docker Desktop / WSL2 / Docker Engine are operational.

Oracle Free local container:

```text
container: local-rag-oracle
listener : 127.0.0.1:1521
service  : FREEPDB1
schema   : LOCALRAG_KB1
tablespace: LOCALRAG_DATA
```

The Oracle schema is a fresh schema and deliberately does not reuse the previous AI-development schema.

Schema v1 tables:

```text
LR_SCHEMA_META
LR_KNOWLEDGE_ITEM
LR_JSON_PART
LR_SOURCE_REF
LR_TOOL_AUDIT
```

User-verified schema bootstrap completed successfully with:

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

### JSON Part write/read round-trip — VERIFIED

A deliberately nonproduction staging test Part was used:

```text
part:test.oracle-roundtrip@1
status: staging
```

Verified path:

```text
POST /api/knowledge/json-part
  -> JSON validation
  -> staging file write
  -> Oracle LR_JSON_PART upsert
  -> oracle_indexed=True
  -> direct Oracle readback
  -> Python dict reconstruction
```

Observed local file:

```text
learning\local-ai\store\staging\test.oracle-roundtrip.v1.json
```

The endpoint returned `oracle_indexed=True` with no Oracle error.

Oracle readback returned the expected document including:

```text
part_id: test.oracle-roundtrip
part_type: test
status: staging
payload.generation.positive: oracle roundtrip test
```

### LocalAIToolbox -> Oracle — VERIFIED

Direct local toolbox execution returned:

```text
source: oracle
ref: part:test.oracle-roundtrip@1
status: staging
```

### Local AI -> tool call -> Oracle -> local AI answer — VERIFIED

The LEARN model successfully invoked `json_part_get` through `/api/local-ai/tool-chat`, consumed the Oracle result, and answered:

```text
ref: part:test.oracle-roundtrip@1
status: staging
part_id: test.oracle-roundtrip
part_type: test
payload.generation.positive: oracle roundtrip test
```

This proves the complete path:

```text
user/API request
  -> local-RAG backend
  -> qwen3-vl:8b-instruct
  -> json_part_get tool call
  -> LocalAIToolbox
  -> Oracle LOCALRAG_KB1 / LR_JSON_PART
  -> tool result
  -> qwen3-vl:8b-instruct final answer
```

### Important fixes made during verification

1. Oracle JSON readback can arrive from `python-oracledb` as a native Python `dict`, not only a JSON string. `src/oracle_knowledge_store.py` was fixed to avoid calling `json.loads()` on an already-decoded dict.
   - fix commit: `fdb8cb8abaafd1931ef8d7ae20b95748f5de657d`
2. `json_part_get` previously swallowed Oracle exceptions and silently fell back to the accepted file-store path, which made Oracle failures look like "part not found". That masking behavior was removed.
   - fix commit: `4a6880701734902b6193bdd89f56f9788ee12ae7`
3. After Python source changes, the running `ui_server.py` had to be restarted before tool-chat reflected the fix.

### Digest note

The file SHA-256 and Oracle `CONTENT_SHA256` currently differ by design because they hash different serialized representations:

- file response SHA: pretty JSON file bytes (including final newline);
- Oracle SHA: canonical compact/sorted JSON representation.

Do not treat this difference alone as corruption.

---

## 8. Git local tool boundary

Configured repositories:

```text
local-image-generator
memoriela
```

Configured Git actions remain READ ONLY:

```text
git_status
git_log
git_diff
git_list_files
git_read_file
git_search
```

`GET /api/local-tools/status` is VERIFIED and reports both repositories plus `read_only: true`.

The Git tool implementation/configuration exists. Do not broaden it to checkout/reset/commit/push/arbitrary shell without an explicit later design/approval layer.

This checkpoint specifically verified the local-AI **Oracle** tool-call round-trip. Do not infer from that alone that every Git tool action has also been individually exercised through Qwen in this checkpoint.

---

## 9. Pre-generation learned-asset selection — IMPLEMENTED / UNVERIFIED

Required behavior:

```text
input -> if AI has a relevant registered learned asset, use it for generation
```

Current flow:

```text
user input
  -> build_generation_request / FREE-MEMORIELA route
  -> LocalAIClient role=generate
  -> learning/registry/registry.json
  -> Qwen selects exact registered asset IDs
  -> validate IDs against registry/domain/state
  -> build generation plan
  -> apply learned prompt fragments and/or learned LoRAs
  -> compiler
  -> ComfyUI
```

Key files:

```text
learning/registry/registry.json
src/learning_registry.py
src/ui_server.py
src/generation_bridge.py
src/compiler.py
src/local_ai_client.py
src/learning_generation_test.py
```

Unknown/hallucinated asset IDs are rejected.

Current production registry has shared rendering as `selection_mode: always`, but no real production `selection_mode: ai` hand/pose/outfit/character/background assets. Therefore `selected_asset_ids: []` is currently an expected valid result.

The user has not yet supplied the local result of `src/learning_generation_test.py` in this checkpoint. Keep this area UNVERIFIED until they do.

---

## 10. Multiple LoRA composition — IMPLEMENTED / UNVERIFIED

Compiler supports:

```text
SDXL Base
  -> Shared Rendering LoRA
  -> selected learned LoRA #1
  -> selected learned LoRA #2
  -> ...
  -> conditioning / sampler
```

Validation rejects duplicate learned IDs/files and duplication of the shared rendering LoRA.

Actual compatibility/strength policy remains asset-specific and requires real trained assets and local generation tests.

---

## 11. Persistent learning producer lifecycle — NOT IMPLEMENTED end-to-end

This remains the largest functional gap.

Desired lifecycle:

```text
LEARN analysis
  -> explicit user acceptance
  -> dataset registration
  -> category-specific dataset
  -> train LoRA / adapter / other runtime asset
  -> validation
  -> publish to ComfyUI/runtime
  -> register asset in learning/registry/registry.json
  -> generation AI can select it later
```

Current LEARN chat/vision and structured JSON/Oracle storage do **not** mean model weights have learned the content.

The consumption side is partly implemented; the persistent producer/publish path is not complete.

---

## 12. Hand / pose responsibility split

Keep concerns separate:

```text
Rendering LoRA -> visual style / dimensional rendering
Pose / Anatomy -> arm / hand / finger / body structure
Character -> identity
Outfit -> clothing identity
```

Potential future pose/anatomy runtimes:

- dedicated LoRA;
- ControlNet / DWPose / OpenPose;
- LoRA + pose control.

Only prompt/LoRA conditional runtime consumption is implemented at this checkpoint. ControlNet/DWPose runtime injection is NOT IMPLEMENTED.

---

## 13. Known technical debt / caution

### `要` false-positive routing

`chat_contract.py` contains a stricter detector, but the regression case still requires local evidence:

```text
必要な背景を生成して
```

Expected route: FREE.

Do not claim this fixed until tested locally.

### Oracle application credential rotation

During an earlier failed schema-reset log, the local Oracle application password was printed by SQL*Plus output. Do not repeat the password. The credential should be rotated after this checkpoint through a narrow, reproducible action that updates both Oracle and `.env.local-ai` safely.

### Staging test residue

The verification Part `part:test.oracle-roundtrip@1` intentionally remains staging test data at this checkpoint. It should be removed with a narrow cleanup mechanism rather than encouraging arbitrary SQL.

### UI/build process lifetime

A running Python/UI server does not hot-reload imported modules. Restart `ui_server.py` after source changes before judging behavior.

Stop a running `local-RAG.exe` before rebuilding because Windows can lock output/DLL files.

### Shared rendering JSON encoding

There was an earlier PowerShell 5.1 UTF-8/mojibake incident. Git is the recovery source; avoid unsafe non-UTF8 rewrites.

---

## 14. Current state matrix

| Area | State | Evidence / note |
|---|---|---|
| ComfyUI / RTX 5080 | VERIFIED | localhost:8188 |
| SDXL Base | VERIFIED | existing local checkpoint |
| Shared Rendering dataset | VERIFIED | 20 images |
| Shared Rendering training | VERIFIED | 2000 steps |
| LoRA-backed FREE generation | VERIFIED at least once | image produced |
| Project-local Ollama | VERIFIED | 127.0.0.1:11435 |
| qwen3-vl:8b-instruct text | VERIFIED | local response |
| qwen3-vl:8b-instruct Vision | VERIFIED | local image analysis |
| Docker / WSL2 / Oracle Free | VERIFIED | local runtime online |
| LOCALRAG_KB1 schema v1 | VERIFIED | fresh schema bootstrap |
| Python -> Oracle health | VERIFIED | online/schema_version=1 |
| JSON Part API -> file + Oracle | VERIFIED | `oracle_indexed=True` |
| Oracle JSON Part readback | VERIFIED | native dict issue fixed |
| LocalAIToolbox -> Oracle | VERIFIED | `source=oracle` |
| Qwen tool call -> Oracle -> answer | VERIFIED | exact staging fields returned |
| Local tools status endpoint | VERIFIED | Git repos + Oracle online |
| Git read-only tool layer | IMPLEMENTED / PARTIALLY VERIFIED | configured/status visible; not every Qwen Git action exercised here |
| JSON download / Part登録 UI | IMPLEMENTED / UNVERIFIED UI | API write path itself verified |
| LEARN drag/drop / paste / copy | IMPLEMENTED / UNVERIFIED | desktop UI retest required |
| Generation post-QA AI | IMPLEMENTED / UNVERIFIED | UI retest required |
| Pre-generation learned-asset selector | IMPLEMENTED / UNVERIFIED | local test output still required |
| Conditional prompt/LoRA consumption | IMPLEMENTED / UNVERIFIED | no real AI-selectable production asset yet |
| Persistent LEARN -> train -> publish -> registry | NOT IMPLEMENTED | major next workflow |
| ControlNet/DWPose runtime | NOT IMPLEMENTED | future pose path |
| DEV model/runtime | CONFIGURED / UNVERIFIED | qwen2.5-coder:14b |
| DEV writes/Git writes/shell/test/build tools | NOT IMPLEMENTED | planning/chat only |

---

## 15. Immediate continuation order after this documentation checkpoint

Do not jump directly to new production features. Continue in this order unless the user explicitly changes priority:

### Phase A — verification-environment cleanup / hardening

1. Add a narrow cleanup path for `part:test.oracle-roundtrip@1` and remove the staging file + exact Oracle row without exposing unrestricted SQL.
2. Rotate the previously exposed Oracle application password safely; never print the new secret.
3. Convert the verified Oracle JSON-Part/tool-chat sequence into a one-command repeatable integration smoke test with automatic isolated test data cleanup.

### Phase B — close currently implemented-but-unverified paths

4. Run/verify `src/learning_generation_test.py`.
5. Rebuild/retest the relevant desktop UI paths when needed: JSON download, explicit Part registration button, drag/drop, clipboard paste, copy, generation post-QA.
6. Run the `要` false-positive FREE-routing regression test.

### Phase C — next major feature

7. Implement the first real **persistent LEARN -> dataset -> train -> validate -> publish -> registry** producer workflow, keeping style/rendering, pose/anatomy, character, and outfit responsibilities modular.

Do not create fake production learned assets merely to make AI selection non-empty. Test fixtures must remain isolated and clearly marked.

---

## 16. New-chat continuation checklist

A new chat should do this before making changes:

1. Read `START_HERE.md`.
2. Read this file completely.
3. Read `docs/local-ai/LOCAL_TOOLS_AND_ORACLE.md` for the current tool/database contract.
4. Inspect current `main` and recent commits before editing.
5. Do not redo already VERIFIED Oracle connectivity/round-trip work unless a regression requires it.
6. Preserve FREE / MEMORIELA semantic isolation and shared-rendering independence.
7. Preserve explicit-write safety: AI may inspect/read through allowed tools; persistent writes happen only through narrow application actions.
8. Treat staging as nonproduction and accepted content as the generation-eligible tier.
9. Keep local Vision judgments advisory; do not auto-promote them to dataset truth.
10. Ask the user to run only the next necessary Windows command/test and judge PASS/FAIL from the returned output.

**Current exact stopping point:** the end-to-end local-AI Oracle JSON-Part tool path is VERIFIED. The next work item is Phase A cleanup/hardening above, not rebuilding Oracle connectivity from scratch.
