# local-RAG Local AI Runtime

Status: **LEARN RUNTIME / TEXT / VISION / ORACLE TOOL-CALL PATH VERIFIED; SOME DESKTOP UI PATHS STILL UNVERIFIED**

This subsystem provides the project-local language/vision-model runtime used by GENERATE, LEARN, and future DEV workflows. It is intentionally separate from ComfyUI image generation.

For the exact current continuation state and remaining work, read:

```text
docs/assistant-context/LOCAL_RAG_CURRENT_STATE.md
```

For the Git/Oracle/JSON-Part tool contract, read:

```text
docs/local-ai/LOCAL_TOOLS_AND_ORACLE.md
```

## Runtime choice

The project uses a **project-local standalone Ollama runtime** rather than a machine-wide installer.

All project-created runtime files stay below:

```text
C:\Dev\local-image-generator\tools\ollama\
```

Dedicated API endpoint:

```text
http://127.0.0.1:11435
```

Port 11435 is intentional so this project does not depend on or collide with a normal machine-wide Ollama installation on 11434.

Model storage:

```text
tools\ollama\models\
```

Runtime/model files are Git-ignored.

---

## Configured roles

### GENERATE

```text
model: qwen3-vl:8b-instruct
vision: yes
think: false
```

Purpose:

- generation-side local AI assistance;
- pre-generation learned-asset selection from exact registered IDs;
- optional generated-image analysis where supported.

The model must not invent asset IDs or silently broaden the user's generation request.

### LEARN

```text
model: qwen3-vl:8b-instruct
vision: yes
think: false
num_ctx: 16384
num_predict: 1024
max_history_messages: 6
```

Purpose:

- local chat;
- uploaded-image understanding;
- pose / hand-anatomy / expression / outfit / background / camera / rendering candidate analysis;
- controlled read-only Git/Oracle retrieval where configured;
- later dataset-registration assistance.

LEARN must distinguish one-time reference use from persistent training data. It must not silently decide what should be learned, registered, trained, saved, or rejected.

Vision output is advisory evidence, not ground truth.

### DEV

```text
model: qwen2.5-coder:14b
vision: no
think: false
```

Purpose:

- local code analysis;
- consume engineering instructions;
- later support a controlled plan -> diff -> explicit apply -> test workflow.

Current DEV remains planning/chat oriented. It does not have unrestricted filesystem writes, shell, Git writes, test, or build execution.

The DEV model runtime itself is not yet verified in the current checkpoint.

---

## Verified local evidence

### Runtime setup — VERIFIED

On 2026-10-11 the user completed LEARN setup successfully on the local Windows/RTX 5080 machine.

Project-local runtime:

```text
C:\Dev\local-image-generator\tools\ollama\ollama.exe
```

API:

```text
http://127.0.0.1:11435
```

The initial `qwen3-vl:8b` tag did not behave correctly for the intended normal vision-chat response path, so LEARN was switched to:

```text
qwen3-vl:8b-instruct
```

### Text inference — VERIFIED

Local text chat returned normal model content.

### Vision inference — VERIFIED

The user supplied an anime character image and received a normal structured `qwen3-vl:8b-instruct` vision response covering pose, arms/hands, outfit, background, and camera/composition.

The model also overclaimed some visual details, so transport/inference is VERIFIED but semantic correctness is not automatic authority.

### Oracle-backed tool call — VERIFIED

The user verified the complete LEARN tool-call route using the exact staging ref:

```text
part:test.oracle-roundtrip@1
```

The path was:

```text
POST /api/local-ai/tool-chat
  -> qwen3-vl:8b-instruct
  -> json_part_get
  -> LocalAIToolbox
  -> Oracle LOCALRAG_KB1 / LR_JSON_PART
  -> tool result
  -> final qwen3-vl:8b-instruct answer
```

Observed final model answer correctly returned:

```text
ref: part:test.oracle-roundtrip@1
status: staging
part_id: test.oracle-roundtrip
part_type: test
payload.generation.positive: oracle roundtrip test
```

Therefore the local model is not merely configured with Oracle tools; the Oracle lookup was actually called and consumed successfully.

See `LOCAL_TOOLS_AND_ORACLE.md` for the full database/tool verification boundary.

---

## Setup

From repository root:

```powershell
cd C:\Dev\local-image-generator
git pull origin main
powershell -ExecutionPolicy Bypass -File .\local_ai.ps1 -Action setup -Role learn
```

DEV can be downloaded later:

```powershell
powershell -ExecutionPolicy Bypass -File .\local_ai.ps1 -Action setup -Role dev
```

Or both roles:

```powershell
powershell -ExecutionPolicy Bypass -File .\local_ai.ps1 -Action setup -Role all
```

Pinned Ollama runtime version:

```text
v0.34.0
```

Do not silently change this pin. Reproducibility is preferred over automatically tracking `latest`.

---

## Runtime commands

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

Verify DEV after model installation:

```powershell
powershell -ExecutionPolicy Bypass -File .\local_ai.ps1 -Action verify -Role dev -Prompt "このPythonコード修正依頼を実装計画に分解してください。"
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

Plain chat body example:

```json
{
  "role": "learn",
  "message": "この画像のポーズを分析してください。",
  "history": [],
  "images": ["<base64 image bytes>"]
}
```

Tool-chat gives the model only the actions permitted for the selected role in `config/local_tools.json`.

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

The exact Git/Oracle tool configuration lives in:

```text
config/local_tools.json
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

Implemented LEARN UI foundation includes:

- mode switching;
- image upload and preview;
- drag/drop;
- screenshot clipboard intake;
- local-AI chat history;
- copy button;
- JSON download;
- explicit JSON-Part registration UI path.

The backend JSON-Part persistence route is VERIFIED. Some desktop/pywebview interaction paths above remain IMPLEMENTED / UNVERIFIED until the user explicitly runs them after rebuilding.

Implemented DEV UI foundation includes mode entry and local chat surface, but no unrestricted execution permissions.

---

## Verification boundary

Already VERIFIED in this checkpoint:

- project-local Ollama runtime/API;
- `qwen3-vl:8b-instruct` text inference;
- direct Vision inference;
- Oracle schema connectivity through Python;
- JSON-Part staging file + Oracle registration;
- Oracle JSON-Part readback;
- `LocalAIToolbox -> Oracle` exact Part lookup;
- `Qwen -> json_part_get -> Oracle -> Qwen answer` end-to-end path;
- `/api/local-tools/status` showing Oracle online and configured Git repositories.

Still do not promote without local evidence:

- all latest desktop UI interactions;
- every Git tool action through Qwen;
- pre-generation learned-asset selection runtime after the latest refactor;
- persistent dataset registration/training/publish lifecycle;
- LoRA training from UI;
- DEV model runtime;
- DEV filesystem/Git-write/shell/test/build execution.

The next exact work order is maintained in `docs/assistant-context/LOCAL_RAG_CURRENT_STATE.md`.
