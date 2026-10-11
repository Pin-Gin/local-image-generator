# local-RAG Local AI Runtime

Status: **IMPLEMENTED FOUNDATION / LOCAL VERIFICATION REQUIRED**

This subsystem provides the local language/vision-model runtime used by future LEARN and DEV modes. It is intentionally separate from ComfyUI image generation.

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
model: qwen3-vl:8b
vision: yes
```

Purpose:

- local chat;
- uploaded-image understanding;
- later pose / hand-anatomy / expression / outfit / background / rendering candidate analysis;
- later dataset-registration assistance.

LEARN must distinguish between using an image as a one-time generation reference and adding it to a persistent training dataset. It must not silently choose what should be learned.

### DEV

```text
model: qwen2.5-coder:14b
vision: no
```

Purpose:

- local code analysis;
- consume engineering instructions prepared externally;
- later plan -> diff -> apply -> test workflows.

The current implementation is **chat/analysis only**. It does not yet grant the model filesystem write, shell, Git, test, or build tools. Those capabilities require an explicit approval/execution layer and are not to be inferred from the presence of the DEV role.

## Setup

From the repository root:

```powershell
cd C:\Dev\local-image-generator
git pull origin main
powershell -ExecutionPolicy Bypass -File .\local_ai.ps1 -Action setup -Role learn
```

The default first setup downloads:

1. the pinned standalone Ollama Windows x64 runtime into `tools\ollama`;
2. `qwen3-vl:8b` into the project-local Ollama model store.

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

`src/ui_server.py` now exposes:

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

The browser UI has **not yet been switched to the requested ChatGPT-like mode dropdown**. The backend contract is being established and locally verified first.

## Verification boundary

The files in this directory/repository prove only that the integration code exists.

Do not mark the local AI runtime/model/API as VERIFIED until the user has run the setup and smoke commands on the RTX 5080 machine and supplied successful output.
