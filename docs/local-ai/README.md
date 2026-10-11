# local-RAG Local AI Runtime

Status: **LEARN RUNTIME / TEXT CHAT / VISION VERIFIED; UI IMPLEMENTED BUT NOT YET LOCALLY VERIFIED**

This subsystem provides the local language/vision-model runtime used by LEARN and future DEV modes. It is intentionally separate from ComfyUI image generation.

## Runtime choice

The project uses a **project-local standalone Ollama runtime** rather than a machine-wide installer.

All project-created runtime files stay below:

```text
C:\Dev\local-image-generator\tools\ollama\
```

The dedicated API endpoint is:

```text
http://127.0.0.1:11435
```

Port 11435 is used so the project runtime does not depend on or collide with a normal machine-wide Ollama installation on the default port 11434.

Model storage is also project-local:

```text
tools\ollama\models\
```

The runtime and model files are ignored by Git.

## Configured roles

### LEARN

```text
model: qwen3-vl:8b-instruct
vision: yes
think: false
```

Purpose:

- local chat;
- uploaded-image understanding;
- pose / hand-anatomy / expression / outfit / background / camera / rendering candidate analysis;
- later dataset-registration assistance.

LEARN must distinguish between using an image as a one-time generation reference and adding it to a persistent training dataset. It must not silently choose what should be learned.

The system prompt explicitly requires the model to:

- reply in the user's language;
- describe only what is visibly supported;
- not infer hidden fingers or unseen anatomy;
- state uncertainty/ambiguity;
- avoid claiming RAG/external retrieval/persistent learning when those actions did not occur.

### DEV

```text
model: qwen2.5-coder:14b
vision: no
think: false
```

Purpose:

- local code analysis;
- consume engineering instructions prepared externally;
- later plan -> diff -> apply -> test workflows.

The current DEV implementation is **chat/analysis only**. It does not yet grant the model filesystem write, shell, Git, test, or build tools. Those capabilities require an explicit approval/execution layer and are not to be inferred from the presence of the DEV role.

## Verified local evidence

### Runtime setup — VERIFIED

On 2026-10-11 the user completed the LEARN setup successfully on the local Windows/RTX 5080 machine.

Observed successful setup output included:

```text
[LOCAL-AI] Downloading Ollama v0.34.0 ...
[LOCAL-AI] Extracting into tools\ollama ...
[LOCAL-AI] Starting project-local Ollama on 127.0.0.1:11435 ...
[LOCAL-AI] Pulling model: qwen3-vl:8b
...
[LOCAL-AI:SETUP:OK] runtime=C:\Dev\local-image-generator\tools\ollama\ollama.exe
[LOCAL-AI:SETUP:OK] models=C:\Dev\local-image-generator\tools\ollama\models
[LOCAL-AI:SETUP:OK] api=http://127.0.0.1:11435
```

The initial `qwen3-vl:8b` tag behaved as a thinking-oriented variant for this API use and returned an empty normal `content` field for vision requests. LEARN was therefore changed to the explicit instruct tag:

```text
qwen3-vl:8b-instruct
```

### Text chat — VERIFIED

User-observed output:

```text
[LOCAL-AI:CHAT:OK]
model=qwen3-vl:8b
content=I'm your local-RAG learning assistant...
prompt_eval_count=108
eval_count=442
```

This proves local text inference worked before the later switch to the instruct tag.

### Vision chat — VERIFIED

After switching LEARN to `qwen3-vl:8b-instruct`, the user supplied a full-body anime character image and received a normal `content` response.

Observed output included:

```text
[LOCAL-AI:CHAT:OK]
model=qwen3-vl:8b-instruct
content=Pose:
- Standing upright, facing forward with a neutral stance.
...
Left Arm and Hand:
...
Right Arm and Hand:
...
Finger Anatomy:
...
Outfit:
...
Background:
...
Camera/Composition:
...
prompt_eval_count=3754
eval_count=342
```

Therefore these are VERIFIED:

- project-local Ollama runtime;
- project-local service on `127.0.0.1:11435`;
- LEARN model installation;
- local text chat inference;
- image input transmission;
- local vision inference;
- normal textual vision response from `qwen3-vl:8b-instruct`.

### Vision-quality caution

The first successful vision description was broadly structured correctly but contained at least one overconfident detail: it described the feet as shoulder-width apart even though the supplied image visually showed the feet much closer together. It also asserted exact finger visibility/count too confidently for stylized hands.

Therefore **vision transport/inference is VERIFIED, but semantic accuracy must not be treated as ground truth**. The local vision model is an analysis assistant, not an authority. User confirmation remains required before dataset registration or training decisions.

## Setup

From the repository root:

```powershell
cd C:\Dev\local-image-generator
git pull origin main
powershell -ExecutionPolicy Bypass -File .\local_ai.ps1 -Action setup -Role learn
```

The current LEARN setup targets:

```text
qwen3-vl:8b-instruct
```

DEV can be downloaded later:

```powershell
powershell -ExecutionPolicy Bypass -File .\local_ai.ps1 -Action setup -Role dev
```

Or both roles can be requested:

```powershell
powershell -ExecutionPolicy Bypass -File .\local_ai.ps1 -Action setup -Role all
```

Current pinned Ollama runtime version:

```text
v0.34.0
```

Do not silently change this pin. Reproducibility is preferred over tracking `latest` automatically.

## Runtime commands

Start the project-local Ollama service:

```powershell
powershell -ExecutionPolicy Bypass -File .\local_ai.ps1 -Action start
```

Show runtime/model status:

```powershell
powershell -ExecutionPolicy Bypass -File .\local_ai.ps1 -Action status
```

Verify LEARN chat:

```powershell
powershell -ExecutionPolicy Bypass -File .\local_ai.ps1 -Action verify -Role learn
```

Verify LEARN with an image:

```powershell
powershell -ExecutionPolicy Bypass -File .\local_ai.ps1 -Action verify -Role learn -Image "C:\path\to\image.png" -Prompt "この画像のポーズと手の状態を分けて説明してください。"
```

Verify DEV after its model has been pulled:

```powershell
powershell -ExecutionPolicy Bypass -File .\local_ai.ps1 -Action verify -Role dev -Prompt "このPythonコード修正依頼を実装計画に分解してください。"
```

## Backend API

`src/ui_server.py` exposes:

```text
GET  /api/local-ai/status
POST /api/local-ai/chat
```

Example chat body:

```json
{
  "role": "learn",
  "message": "この画像のポーズを分析してください。",
  "history": [],
  "images": ["<base64 image bytes>"]
}
```

## Desktop UI state

A ChatGPT-like mode selector is now implemented in the browser/desktop UI:

```text
画像生成
学習
開発
```

Implemented LEARN UI foundation:

- top-level dropdown mode switching;
- image upload (PNG/JPEG/WebP, max 20 MB);
- image preview/remove;
- local-AI status display;
- LEARN chat history;
- uploaded image sent as base64 to `/api/local-ai/chat`;
- no automatic dataset registration or training.

Implemented DEV UI foundation:

- mode entry;
- local model status;
- local chat surface;
- no filesystem/Git/shell execution yet.

These UI changes are **IMPLEMENTED BUT NOT YET LOCALLY VERIFIED** until the user pulls/builds/runs the desktop application and confirms behavior.

## Verification boundary

Do not promote the following to VERIFIED without local evidence:

- new dropdown/UI rendering;
- UI image upload -> backend -> vision response path;
- persistent dataset registration;
- LoRA training from UI;
- DEV model runtime;
- DEV filesystem/Git/shell/test/build execution.
