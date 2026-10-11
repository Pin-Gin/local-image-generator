# local-RAG Local AI Runtime

Status: **LEARN RUNTIME / TEXT / VISION / ORACLE TOOL-CALL PATH VERIFIED; FREE GENERATION AI BYPASS IS TARGET DESIGN**

This subsystem provides the project-local language/vision-model runtime used by LEARN, MEMORIELA planning, DEV, and optional assistant features. It is intentionally separate from the ComfyUI image-generation engine.

For current continuation state and exact next work, read:

```text
docs/handoff/LOCAL_RAG_HANDOFF.md
```

For Git/Oracle/JSON-Part tool details, read:

```text
docs/local-ai/LOCAL_TOOLS_AND_ORACLE.md
```

For the generation-side AI boundary, read:

```text
docs/local-ai/GENERATION_ASSISTANT.md
```

---

## Runtime choice

The project uses a project-local standalone Ollama runtime rather than a machine-wide installer.

```text
runtime root: C:\Dev\local-image-generator\tools\ollama\
API:          http://127.0.0.1:11435
models:       tools\ollama\models\
```

Runtime/model files are Git-ignored.

Pinned runtime version:

```text
v0.34.0
```

Do not silently change this pin.

---

## Configured model roles

### `learn` — VERIFIED runtime

```text
model: qwen3-vl:8b-instruct
vision: yes
think: false
num_ctx: 16384
num_predict: 1024
max_history_messages: 6
```

Responsibilities:

- local chat;
- uploaded-image understanding;
- pose / hand-anatomy / expression / outfit / background / camera / rendering candidate analysis;
- JSON Part candidate creation;
- controlled read-only Git/Oracle retrieval;
- future dataset-registration assistance.

LEARN must distinguish analysis from persistence. A model response is not an accepted Part, dataset registration, training run, or model update.

When generating canonical reusable JSON Part candidates, the model uses `status: staging`; only an explicit user/application action may promote to accepted.

Vision output is advisory evidence, not ground truth.

### `generate` — configured legacy/assistant role, not target FREE execution path

`config/local_ai.json` still contains:

```text
model: qwen3-vl:8b-instruct
vision: yes
```

Historically this role was used for pre-generation learned-asset selection and optional generated-image discussion.

The current user-approved target design changes that boundary:

```text
FREE -> must bypass Qwen pre-generation interpretation/asset selection
MEMORIELA -> may use controlled AI planning
post-generation assistant -> may remain optional
```

Do not infer from the existence of the `generate` role that FREE should continue calling it. Code refactoring is still required to enforce the new boundary.

### `dev` — configured / runtime not verified here

```text
model: qwen2.5-coder:14b
vision: no
think: false
```

DEV is planning/code-analysis oriented. Current tools do not grant unrestricted filesystem writes, shell execution, Git writes, test execution, or build execution.

---

## Verified local evidence

The user has locally verified:

- project-local Ollama startup/API;
- `qwen3-vl:8b-instruct` text inference;
- direct vision inference;
- Oracle connectivity through Python;
- canonical staging JSON Part file + Oracle registration;
- Oracle JSON Part readback;
- `LocalAIToolbox -> Oracle` exact Part lookup;
- `Qwen LEARN -> json_part_get -> Oracle -> Qwen final answer`;
- `/api/local-tools/status` with Oracle online and configured read-only Git repositories;
- safe Oracle app-password rotation;
- narrow test-Part cleanup;
- full disposable `verify_local_stack.ps1` integration run.

The one-command verification is:

```powershell
cd C:\Dev\local-image-generator
.\verify_local_stack.ps1
```

A successful run ends with:

```text
[VERIFY:LOCAL-STACK:OK]
```

---

## Setup

From repository root:

```powershell
cd C:\Dev\local-image-generator
git pull origin main
powershell -ExecutionPolicy Bypass -File .\local_ai.ps1 -Action setup -Role learn
```

DEV can be installed later:

```powershell
powershell -ExecutionPolicy Bypass -File .\local_ai.ps1 -Action setup -Role dev
```

Start:

```powershell
powershell -ExecutionPolicy Bypass -File .\local_ai.ps1 -Action start
```

Status:

```powershell
powershell -ExecutionPolicy Bypass -File .\local_ai.ps1 -Action status
```

Verify LEARN text:

```powershell
powershell -ExecutionPolicy Bypass -File .\local_ai.ps1 -Action verify -Role learn
```

Verify LEARN vision:

```powershell
powershell -ExecutionPolicy Bypass -File .\local_ai.ps1 -Action verify -Role learn -Image "C:\path\to\image.png" -Prompt "この画像のポーズと手の状態を分けて説明してください。"
```

---

## Backend API

`src/ui_server.py` exposes local-AI/tool endpoints including:

```text
GET  /api/local-ai/status
POST /api/local-ai/chat
GET  /api/local-tools/status
POST /api/local-ai/tool-chat
POST /api/knowledge/json-part
```

Tool access is controlled by:

```text
config/local_tools.json
```

Important process rule: after editing Python modules imported by `ui_server.py`, restart the running server before testing. There is no automatic hot reload.

---

## Controlled tool boundary

Current tool design is intentionally narrow:

```text
Git      -> read-only actions
Oracle   -> knowledge / exact JSON-Part reads through the model tool loop
Writes   -> explicit application endpoints/actions, not silent model tool writes
Shell    -> no arbitrary execution
Git push -> not exposed
```

Do not expand permissions merely to simplify a test.

---

## Desktop UI state

Top-level selector:

```text
画像生成
学習
開発
```

LEARN UI foundations include image upload/preview, drag/drop, clipboard intake, local-AI chat history, copy, JSON download, and explicit JSON-Part registration/acceptance UI code.

The backend JSON-Part persistence route is VERIFIED. The latest explicit `Part採用` desktop interaction is still IMPLEMENTED / UNVERIFIED.

DEV remains a local chat/planning surface without unrestricted execution permissions.

---

## Verification boundary

Do not promote without new local evidence:

- new FREE no-Qwen generation path;
- latest desktop `Part採用` interaction;
- all Git actions through Qwen;
- DEV model runtime;
- persistent dataset -> train -> validate -> publish lifecycle;
- automated ControlNet/Inpaint/Detailer/Upscale generation pipeline.

The authoritative status matrix and implementation order live in:

```text
docs/handoff/LOCAL_RAG_HANDOFF.md
```
