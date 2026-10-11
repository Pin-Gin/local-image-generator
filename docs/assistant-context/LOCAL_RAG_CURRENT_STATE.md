# local-RAG — Current State / Continuation Handoff

Last checkpoint: **2026-10-11**

Read `START_HERE.md` first, then this file before changing architecture or implementation.

This document distinguishes:

- **VERIFIED** — user supplied successful local runtime evidence;
- **IMPLEMENTED / UNVERIFIED** — code exists in Git but the user has not yet locally confirmed the latest path;
- **NOT IMPLEMENTED** — no completed runtime path yet;
- **OPEN SPEC** — design choice still not fixed.

Do not promote UNVERIFIED items without user-side execution evidence.

---

## 1. Product direction

`local-RAG` is the Windows desktop application. `MEMORIELA` remains the external canon / approved visual-authority repository and must not become the generic app/build name.

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

Current architectural objective for generation is now:

```text
User input
  -> deterministic FREE / MEMORIELA routing
  -> local AI checks registered learned assets
  -> if a relevant learned asset exists, select and apply it
  -> generation plan
  -> compiler
  -> ComfyUI
  -> image
  -> optional local-AI visual QA / learning discussion
```

The local AI must not silently rewrite the user's request or invent assets. It may only select exact registered asset IDs.

---

## 2. Verified local environment

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

Project-owned tools remain below:

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

Standalone Ollama was installed below the repository rather than machine-wide:

```text
C:\Dev\local-image-generator\tools\ollama\ollama.exe
C:\Dev\local-image-generator\tools\ollama\models\
```

Dedicated API:

```text
http://127.0.0.1:11435
```

Verified model:

```text
qwen3-vl:8b-instruct
```

User-verified LEARN text inference:

```text
[LOCAL-AI:CHAT:OK]
model=qwen3-vl:8b-instruct
```

User-verified direct image/Vision inference also succeeded. The model correctly described broad pose/outfit/background/camera structure, though it overclaimed some details (for example stance width / finger certainty). Therefore local Vision output is **analysis evidence, not automatic ground truth**.

---

## 3. Shared rendering — VERIFIED core path

Source:

```text
shared/rendering/matte_dimensional_anime.json
```

Initial dataset:

```text
20 images
folder: learning/rendering/dataset/20_mdanime
5 epochs
2000 steps
```

Verified training completion:

```text
steps: 100% ... 2000/2000 ... avr_loss=0.142
[LEARNING:TRAIN:OK]
```

The trained Matte Dimensional Anime LoRA was published and used in at least one actual FREE generation after fixing Windows ComfyUI `LoraLoader` selector-name normalization.

Manual visual evaluation of that generated sample:

```text
rendering / dimensionality : PASS
anime retention            : PASS
depth                       : PASS
hand/finger anatomy         : FAIL
```

The hand failure remains categorized as pose/anatomy quality, not evidence that shared rendering must be retrained.

The trained `.safetensors` file remains a local runtime artifact and is not stored in Git.

---

## 4. Existing desktop modes

Requested mode switch UI is implemented as a ChatGPT-like dropdown rather than permanent tabs:

```text
画像生成
学習
開発
```

### 画像生成

Existing FREE / MEMORIELA generation UI plus local generation AI assistance.

### 学習

Local Qwen Vision chat exists. Implemented UI capabilities include:

- file image upload;
- image preview;
- drag-and-drop image intake;
- Windows screenshot clipboard image intake (`Ctrl+V` path);
- copy button on local-AI replies;
- image discussion with `qwen3-vl:8b-instruct`.

The original UI image request exceeded Ollama's default 4096-token context. LEARN is now configured with:

```text
num_ctx: 16384
num_predict: 1024
max_history_messages: 6
```

The direct CLI Vision path is VERIFIED. The latest pywebview UI paths for context fix / drag-drop / clipboard / copy are **IMPLEMENTED / UNVERIFIED** until the user tests them after rebuilding.

### 開発

The DEV role is configured for future local code work with:

```text
qwen2.5-coder:14b
```

But the model is not yet confirmed downloaded/run in the current checkpoint, and filesystem/Git/shell/write tools are **NOT IMPLEMENTED**. Current DEV mode remains planning/chat only.

---

## 5. Pre-generation learned-asset selection — IMPLEMENTED / UNVERIFIED

The user clarified the required behavior as:

> input -> if AI has a relevant learned asset, use it for generation

The generation architecture was therefore changed from post-generation-only AI analysis to a pre-generation learned-asset selection path.

Current code flow:

```text
user input
  -> build_generation_request / FREE-MEMORIELA route
  -> LocalAIClient role=generate
  -> learning/registry/registry.json
  -> Qwen selects exact registered asset IDs
  -> validate selected IDs against registry/domain/state
  -> build_generation_plan
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

The selector uses Ollama JSON mode. Unknown / hallucinated asset IDs are rejected; they are not silently converted into prompts.

Generation request traceability now includes:

```text
learning.registry_version
learning.selector = local-ai
learning.selector_role = generate
learning.selector_model
learning.selected_asset_ids
learning.reason
```

Generation result metadata includes:

```text
learned_asset_ids
```

Manifest data records the learned assets that were actually resolved/applied.

---

## 6. Learning registry state

Mutable registry source:

```text
learning/registry/registry.json
```

The desktop package also bundles a fallback copy, but `src/learning_registry.py` prefers the repository copy when local-RAG is run from the repository/build tree so future published assets can update a mutable registry.

Supported conditional runtime types at this checkpoint:

```text
prompt
lora
```

The registry also records `shared_rendering` as inventory / always-applied state, but that runtime type is not eligible for conditional AI selection.

### Current production contents

The registry currently records the already-trained Matte Dimensional Anime shared rendering asset as:

```text
selection_mode: always
runtime.type: shared_rendering
```

There are currently **no real production `selection_mode: ai` hand / pose / outfit / character / background assets**.

Therefore after this refactor, with today's registry, pre-generation Qwen should run but normally select:

```text
selected_asset_ids: []
```

This is expected. Shared rendering continues through the separate shared-rendering path.

A future trained/published pose/hand/etc asset must be added to the registry before the generation AI can select it.

---

## 7. Multiple LoRA composition — IMPLEMENTED / UNVERIFIED

`src/compiler.py` now supports a chained sequence:

```text
SDXL Base
  -> Shared Rendering LoRA (if active)
  -> selected learned LoRA #1
  -> selected learned LoRA #2
  -> ...
  -> conditioning / sampler
```

Validation rejects:

- duplicate learned asset IDs;
- duplicate learned LoRA files;
- learned LoRA duplication of the shared Rendering LoRA.

Strengths remain asset-specific registry values; the compiler does not assume `1.0`.

This supports future combinations such as rendering + hand/anatomy + pose + character/outfit LoRAs, but actual compatibility/strength policy must still be evaluated per trained asset.

---

## 8. Generation-side post-generation AI assistant

The prior post-generation `生成AIアシスト` remains separate from the new selector.

It can:

- receive the original generation instruction;
- inspect the current generated image;
- discuss pose / hands / expression / outfit / background / camera / rendering;
- optionally auto-analyze after generation;
- send the current generated image into LEARN mode.

This path is **post-generation QA / discussion**.

The new registry selector is **pre-generation asset selection**.

Do not conflate the two.

---

## 9. Persistent learning lifecycle — NOT IMPLEMENTED end-to-end

This is the largest remaining gap relative to the user's final desired workflow.

Current LEARN mode can visually analyze an image, but it does not yet complete:

```text
explicit acceptance
  -> dataset registration
  -> category-specific training dataset
  -> train LoRA / adapter
  -> validation
  -> publish to ComfyUI
  -> register asset in learning/registry/registry.json
  -> available to pre-generation AI selector
```

Therefore do **not** tell the user that simply chatting about or uploading an image has already taught a persistent generation asset.

The pre-generation consumption path now exists; the producer/publish path still needs implementation.

---

## 10. Hand / pose direction

The original motivation for general learned assets is the ambiguous-hand failure seen in the LoRA-on image.

Rendering responsibility remains separate:

```text
Rendering LoRA -> visual style / dimensional rendering
Pose / Anatomy -> arm / hand / finger / body structure
Character -> identity
Outfit -> clothing identity
```

Potential future pose/anatomy runtimes include:

- dedicated LoRA;
- ControlNet / DWPose / OpenPose reference;
- LoRA + pose control.

Only `prompt` and `lora` conditional runtime assets are implemented in the new registry/compiler at this checkpoint. ControlNet runtime injection remains **NOT IMPLEMENTED**.

---

## 11. Known routing / technical debt

### `要` false positives

Current `chat_contract.py` includes a more constrained named-character detector, but the expected regression case must still be locally run:

```text
必要な背景を生成して
```

Expected: FREE.

Do not claim fixed until test evidence is supplied.

### DB migration

Older DB naming/history preservation is not fully verified.

### Profile selector vs automatic routing

Visible profile selection can still be conceptually confusing because effective routing can override the requested profile.

### Build locking

Stop a running `local-RAG.exe` before rebuilding; Windows may lock build output/DLLs.

### Shared rendering local JSON

There was an earlier PowerShell 5.1 UTF-8/mojibake incident while manually editing the shared rendering JSON. Git is the recovery source. Avoid non-UTF8 PowerShell rewrites.

---

## 12. Local verification still required for the latest learned-generation refactor

After pulling current main, first run:

```powershell
cd C:\Dev\local-image-generator
python .\src\learning_generation_test.py
```

Expected:

```text
[LEARNED-GENERATION:TEST:OK]
```

Then rebuild:

```powershell
powershell -ExecutionPolicy Bypass -File .\build_desktop.ps1
.\dist\local-RAG\local-RAG.exe
```

With the current production registry, perform a normal generation and confirm:

```text
local AI is reachable
request.learning exists
learned_asset_ids = []
image still generates successfully
shared Rendering LoRA remains active according to local shared-rendering config
```

The empty list is correct until a real conditional learned asset is published.

Do not create a fake production hand/pose asset merely to make the list non-empty. Use a real trained/published asset or a deliberately isolated test fixture.

---

## 13. Current state matrix

| Area | State | Note |
|---|---|---|
| ComfyUI / RTX 5080 | VERIFIED | localhost:8188 |
| SDXL Base | VERIFIED | existing local checkpoint |
| Shared Rendering dataset | VERIFIED | 20/20 |
| Shared Rendering training | VERIFIED | 2000 steps completed |
| LoRA-backed FREE generation | VERIFIED at least once | visual result produced |
| Rendering visual direction | MANUAL PASS on sample | hand still failed |
| Project-local Ollama | VERIFIED | 127.0.0.1:11435 |
| qwen3-vl:8b-instruct text chat | VERIFIED | local response returned |
| qwen3-vl:8b-instruct direct Vision | VERIFIED | image analysis returned |
| LEARN UI file upload/chat | IMPLEMENTED | latest UI needs reverify after context fix |
| Drag/drop / screenshot paste / copy | IMPLEMENTED / UNVERIFIED | desktop re-test required |
| Generation post-QA AI | IMPLEMENTED / UNVERIFIED | UI re-test required |
| Pre-generation learned-asset AI selector | IMPLEMENTED / UNVERIFIED | new refactor |
| Learning registry | IMPLEMENTED | only shared rendering inventory currently |
| Conditional prompt asset consumption | IMPLEMENTED / UNVERIFIED | no real production asset yet |
| Conditional LoRA asset consumption | IMPLEMENTED / UNVERIFIED | multi-LoRA chain added |
| Persistent LEARN -> train -> publish -> registry | NOT IMPLEMENTED | next major workflow |
| ControlNet/DWPose generation runtime | NOT IMPLEMENTED | future pose path |
| DEV code-write/Git/shell tools | NOT IMPLEMENTED | chat/planning only |

---

## 14. Continuation rule

On a new chat:

1. Read `START_HERE.md`.
2. Read this file completely.
3. Inspect current main branch before editing.
4. Preserve the distinction between analysis, dataset registration, training, publishing, registry activation, and generation-time application.
5. Never claim that an uploaded image is persistently learned until the producer lifecycle actually completed.
6. Never let Qwen invent an unregistered generation asset.
7. Preserve FREE / MEMORIELA semantic isolation and shared-rendering independence.
8. Prefer automated end-to-end local workflows over manual ComfyUI node construction.
9. Keep project-created tooling under `C:\Dev\local-image-generator`.
10. Treat local execution as unverified until the user supplies actual output.

The immediate engineering continuation after this checkpoint is to locally verify the new pre-generation selector, then implement the **persistent LEARN -> dataset -> train -> publish -> registry** producer path for the first real reusable pose/hand asset.
