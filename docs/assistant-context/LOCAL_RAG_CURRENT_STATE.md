# local-RAG — Current State / Continuation Handoff

Last checkpoint: **2026-10-11**

This document is the continuation state for a new ChatGPT/Codex session. Read `START_HERE.md` first, then this file before changing architecture or implementation.

## 1. Purpose of this checkpoint

This file records:

- what has actually been implemented;
- what has actually been verified on the user's Windows/RTX 5080 machine;
- what is implemented but not fully verified;
- what is not implemented;
- known defects / technical debt;
- open specification decisions;
- the intended next direction.

Do not promote an item from `UNVERIFIED`, `NOT IMPLEMENTED`, or `OPEN SPEC` to completed without local execution evidence from the user.

---

## 2. Product direction that must be preserved

`local-RAG` is a local Windows desktop image-generation application backed by ComfyUI.

The architecture is intentionally split into three concerns:

```text
FREE
  natural language / JSON -> generic text2img
  no MEMORIELA-specific identity/outfit/background assets

MEMORIELA
  named cast -> controlled character production
  character / outfit / pose / expression / situation / background / camera are modular concerns

SHARED RENDERING
  Matte Dimensional Anime
  describes how the image is rendered, not who/what is depicted
  used by both FREE and MEMORIELA
```

Important current decisions:

- `MEMORIELA` is the external canon/visual-authority repository, not the desktop application name.
- Desktop/build name is `local-RAG`.
- FREE must not silently consume MEMORIELA character assets.
- Named MEMORIELA cast routes to MEMORIELA; unregistered characters must fail rather than silently become YURA or FREE.
- Shared rendering must remain character-independent.
- The target shared style is `Matte Dimensional Anime`: anime foundation, pronounced dimensionality/depth, matte surfaces, restrained highlights, no photoreal/PBR/plastic-CGI drift.
- Rendering consistency is now learned with a LoRA; prompt-only rendering is not considered sufficient for the intended production direction.
- The user does **not** need an A/B comparison against LoRA-off rendering; rendering drift without the learned LoRA is already known. Current evaluation should use LoRA-on generation.
- A hand/anatomy failure must not be “fixed” by retraining the rendering LoRA unless evidence shows the rendering LoRA itself is the cause. Keep responsibility layers separate.

---

## 3. Verified local environment

### ComfyUI generation runtime — VERIFIED

User-verified startup environment:

```text
ComfyUI: 0.39.0
ComfyUI Python: 3.13.14
ComfyUI PyTorch: 2.14.0+cu130
GPU: NVIDIA GeForce RTX 5080
VRAM reported by ComfyUI: 16275 MB
API/UI: http://127.0.0.1:8188
```

ComfyUI local root currently used by the user:

```text
C:\Users\shift\Downloads\ComfyUI_windows_portable_nvidia\ComfyUI_windows_portable
```

Start command:

```powershell
cd C:\Users\shift\Downloads\ComfyUI_windows_portable_nvidia\ComfyUI_windows_portable
.\run_nvidia_gpu.bat
```

Existing SDXL Base checkpoint:

```text
C:\Users\shift\Downloads\ComfyUI_windows_portable_nvidia\ComfyUI_windows_portable\ComfyUI\models\checkpoints\sd_xl_base_1.0.safetensors
```

### Rendering-LoRA training runtime — VERIFIED

Project-owned tools remain under `C:\Dev\local-image-generator`:

```text
tools\python312
tools\sd-scripts
tools\sd-scripts\venv
tools\_downloads
```

Verified training runtime:

```text
Python: 3.12.10
PyTorch: 2.8.0+cu128
CUDA: True
GPU: NVIDIA GeForce RTX 5080
```

The project intentionally does not create a sibling `C:\Dev\sd-scripts` installation.

---

## 4. Desktop application / generation path

### Implemented

The repository contains the local application path:

```text
local-RAG.exe
  -> local backend/controller
  -> request / intent parsing
  -> FREE or MEMORIELA routing
  -> shared rendering injection
  -> workflow compiler
  -> ComfyUI HTTP API
  -> output image + manifest/database path
```

Relevant areas include:

```text
src/
ui/
profiles/
workflows/
intent/
shared/rendering/
domains/free/
domains/memoriela/
```

FREE uses `free-sdxl-v1` and text2img.

MEMORIELA named-character routing exists. Only YURA currently has a connected runtime character profile; other named cast members are detected but intentionally fail if no runtime character profile is registered.

### Desktop packaging

PyInstaller/pywebview desktop packaging exists and the output name is `local-RAG`.

ComfyUI is still a separately started local service. Automatic ComfyUI startup from the desktop application has **not** been agreed as production behavior and is **not implemented as a completed feature**.

---

## 5. Shared rendering implementation

Shared rendering source:

```text
shared/rendering/matte_dimensional_anime.json
```

Current LoRA integration path:

- shared config is loaded in `src/generation_bridge.py`;
- the effective generation plan receives `rendering_lora`;
- `src/compiler.py` injects the standard ComfyUI `LoraLoader` node;
- positive/negative CLIP and sampler model are rewired through the LoRA node;
- current compiler normalizes LoRA selector names for Windows ComfyUI (`/` -> `\`) before submitting the workflow.

Recent selector-path fixes:

```text
a185ff44dab545ca3d3498b425385e42e056262f
9814a366e4c7bcf3be59796f5b6c1c1f546172c5
```

The Git copy of `shared/rendering/matte_dimensional_anime.json` remains a portable source definition and currently has LoRA disabled by default. Local `publish -Activate` changes the working copy for the user's runtime.

---

## 6. Rendering dataset pipeline — IMPLEMENTED AND VERIFIED

Manifest-driven dataset preparation exists under:

```text
learning/rendering/
```

Implemented files/functions include:

```text
generation_manifest.json
GENERATION_BATCH_INSTRUCTIONS.md
incoming/
dataset/20_mdanime/
src/rendering_dataset_prepare.py
train_rendering.ps1 -Action prepare
```

The importer can:

- map incoming images by ID;
- sequentially assign untagged images when explicitly requested;
- preserve existing slots unless `-Replace` is used;
- create captions from the manifest;
- detect byte-identical duplicates by SHA-256;
- report missing/ambiguous/unassigned images.

The user generated and imported a complete 20-image dataset.

Verified preparation result:

```text
[DATASET] copied=20 preserved=0 ready=20/20
[DATASET:PREPARE:OK]
```

Verified dataset validation:

```text
[LEARNING:OK] dataset_images=20
[LEARNING:OK] trainer=C:\Dev\local-image-generator\tools\sd-scripts\sdxl_train_network.py
[LEARNING:OK] python=C:\Dev\local-image-generator\tools\sd-scripts\venv\Scripts\python.exe
[LEARNING:OK] model=C:\Users\shift\Downloads\ComfyUI_windows_portable_nvidia\ComfyUI_windows_portable\ComfyUI\models\checkpoints\sd_xl_base_1.0.safetensors
```

Training dataset/model files are local runtime assets and intentionally not committed.

---

## 7. Rendering LoRA training — VERIFIED

Training configuration was tuned to 5 epochs with the current `20_mdanime` repeat structure, resulting in 2000 training steps for the initial run.

Verified user output:

```text
steps: 100%|...| 2000/2000 [20:08<00:00, 1.65it/s, avr_loss=0.142]
[LEARNING:TRAIN:OK]
```

This confirms the training process completed successfully on the RTX 5080.

The loss value is not itself a visual-quality guarantee; visual generation is the acceptance criterion.

Expected local output name:

```text
learning/rendering/output/matte_dimensional_anime_v1.safetensors
```

Expected ComfyUI selector path after publishing:

```text
local-rag\rendering\matte_dimensional_anime_v1.safetensors
```

The `.safetensors` weight is a local runtime artifact and is not stored in Git.

---

## 8. Publish / activation / generation verification

### What is verified

The learned LoRA was published/recognized sufficiently to reach actual LoRA-backed image generation after resolving ComfyUI `LoraLoader` selector-path validation issues.

A FREE image was generated with the learned rendering active. The sample visually showed:

```text
RENDERING / dimensionality : PASS by manual inspection
DEPTH                      : PASS by manual inspection
ANIME style retention      : PASS by manual inspection
HAND / finger anatomy      : FAIL
```

The notable defect in that sample was the raised hand near the hair/head: fingers and contact geometry were ambiguous.

Interpretation at this checkpoint:

- shared rendering learning is producing the intended broad visual direction;
- the observed hand failure is an anatomy/pose-control problem, not evidence by itself that the rendering LoRA needs retraining.

### Current local-config warning

During LoRA path troubleshooting, a manual Windows PowerShell 5.1 JSON read/write attempt caused or may have caused encoding/working-copy corruption in the user's local:

```text
shared/rendering/matte_dimensional_anime.json
```

Symptoms seen locally included mojibake and JSON parsing errors after `Get-Content` / `ConvertFrom-Json` without explicit UTF-8 handling.

The Git copy is the recovery source. At the start of a new session, **do not assume the user's current working copy is healthy** until checked.

Safe recovery/verification sequence:

```powershell
cd C:\Dev\local-image-generator

git restore .\shared\rendering\matte_dimensional_anime.json

powershell -ExecutionPolicy Bypass -File .\train_rendering.ps1 -Action publish -Activate

.\tools\python312\python.exe -m json.tool `
  .\shared\rendering\matte_dimensional_anime.json > $null

if ($LASTEXITCODE -eq 0) {
    Write-Host "[JSON:OK]"
}
```

Use Python or explicit UTF-8 when validating JSON. Do not rewrite this file with Windows PowerShell 5.1 default text encoding.

After recovery/activation, rebuild the desktop package before testing:

```powershell
powershell -ExecutionPolicy Bypass -File .\build_desktop.ps1
.\dist\local-RAG\local-RAG.exe
```

ComfyUI does not need to be retrained for this recovery; the trained LoRA already exists locally unless the user deletes the runtime files.

---

## 9. Learning/UI direction discussed but NOT IMPLEMENTED

The user asked whether an image could be uploaded through the UI and then learned visually.

Two technically different concepts were distinguished:

1. **Inference-time image reference** — ControlNet / IP-Adapter / pose-reference class of behavior. This is not persistent learning.
2. **Persistent learning** — upload accepted images into a dataset and train a LoRA/adapter locally.

The user then paused implementation and requested this Git checkpoint.

Therefore the following is **direction only, not an approved finished specification**:

```text
UI image upload
  -> choose learning purpose/category
  -> preview / inspect
  -> dataset registration
  -> caption/tag metadata
  -> validate
  -> local RTX 5080 training
  -> publish/version
  -> use together with shared Rendering LoRA
```

Potential categories discussed conceptually:

```text
HAND / ANATOMY
POSE
OUTFIT
CHARACTER
RENDERING
```

No UI, schema, learning registry, or specialized hand model has been implemented for this yet.

---

## 10. High-priority NOT IMPLEMENTED items

### A. Hand / anatomy correction layer

Not implemented:

- `learning/anatomy/hands/` pipeline;
- hand-specific dataset contract;
- hand/anatomy LoRA training configuration;
- automatic application of an anatomy LoRA;
- hand-specific QA;
- ControlNet hand/pose reference workflow.

The recent generated sample makes this the most visible next quality problem.

### B. UI-driven learning

Not implemented:

- upload control for learning images;
- learning-category selector;
- dataset preview/accept/reject UI;
- caption/tag editor or automatic caption review;
- training progress UI;
- cancel/retry UI;
- publish/activate UI;
- model version/rollback UI.

### C. MEMORIELA modular asset learning

Architecture/directory ownership exists, but these are not production-complete:

- character LoRAs/adapters for the full cast;
- outfit learning from outfit-only/mannequin references;
- reusable pose assets;
- situation/background learned assets;
- multi-character composition/continuity.

Only YURA has a connected runtime character route today.

---

## 11. Open specification decisions that must be resolved before the next large implementation

These are not yet fixed requirements. Ask/decide explicitly rather than silently choosing defaults.

### 11.1 Hand/anatomy strategy

Need to decide whether the hand-quality layer should be:

- LoRA only;
- ControlNet/pose reference only;
- LoRA + ControlNet;
- another adapter architecture.

Also decide whether the goal is generic hand anatomy improvement or reproducing a specific uploaded hand/pose.

### 11.2 UI “learning” semantics

Need a clear distinction in the UI between:

- `use this image as a generation reference now`;
- `add this image to a persistent training dataset`.

These must not be presented as the same operation.

### 11.3 Dataset acceptance / QA

Need to define:

- minimum images per learning category;
- image resolution/aspect policy;
- near-duplicate detection beyond byte SHA-256;
- caption generation and manual correction policy;
- rejection reasons;
- whether accepted images are immutable or versioned.

### 11.4 Multiple learned modules at generation time

Need to define combination order and strength policy for future stacks such as:

```text
SDXL Base
 + Shared Rendering LoRA
 + Anatomy/Hand LoRA
 + Character identity LoRA
 + Outfit LoRA
 + optional pose/control adapter
```

Do not assume all LoRAs can simply use strength `1.0` or that load order is irrelevant.

### 11.5 Per-domain application

Need to decide whether a future anatomy/hand module is:

- global/shared for FREE + MEMORIELA;
- enabled only in MEMORIELA;
- selected per request.

### 11.6 Model registry/versioning

Need policy for:

- model ID/version;
- source dataset hash/version;
- publish location;
- activation state;
- rollback;
- keeping old weights;
- manifest recording of all active learned modules.

### 11.7 Tracked vs runtime activation state

Current `publish -Activate` edits `shared/rendering/matte_dimensional_anime.json`, which is a tracked source file, while the LoRA weight itself is local and ignored.

This mixes portable source configuration and machine-local activation state. Decide whether activation should move into a separate Git-ignored runtime config/registry.

### 11.8 Training reproducibility

`setup_rendering_learning.ps1` updates the external `sd-scripts` clone. Pinning a known compatible commit/version has not been finalized. A future setup may change if upstream changes.

---

## 12. Known technical debt / unresolved bugs

### MEMORIELA name routing false positive

There is a known risk around the single-character name `要`: generic substring parsing can interpret ordinary words containing `要` (for example `必要`) as KANAME.

A regression case should exist or be added for text similar to:

```text
必要な背景を生成して
```

Expected route: FREE, not KANAME/MEMORIELA.

Do not claim this is resolved until the current parser/test is inspected and locally run.

### Database migration

Runtime database naming changed from an older MEMORIELA-specific name toward:

```text
database/local_rag.db
```

Migration/preservation of any older local history has not been fully verified. Do not claim history is automatically preserved.

### UI profile selection vs automatic routing

The application has automatic effective-profile/domain routing. Any visible profile selector may be confusing if it appears to control a profile that is then overridden by routing. This UI behavior still needs review.

### GATE.md freshness

`GATE.md` predates some of the latest training/LoRA verification work and may not represent the newest checkpoint. Treat this current-state file as the continuation record until `GATE.md` is deliberately reconciled.

### Local build locking

A running `local-RAG.exe` can lock build output/DLLs. Stop the desktop process before rebuilding.

---

## 13. Current state matrix

| Area | State | Evidence / note |
|---|---|---|
| ComfyUI startup/API | VERIFIED | 0.39.0, RTX 5080, localhost:8188 |
| SDXL base generation | VERIFIED | existing local smoke/generation path |
| Desktop app path | IMPLEMENTED / previously locally exercised | local-RAG + backend + ComfyUI API |
| FREE text2img routing | IMPLEMENTED / exercised | used for LoRA visual test |
| MEMORIELA YURA route | IMPLEMENTED | current connected MEMORIELA character path |
| Other named MEMORIELA cast | DETECTION ONLY / runtime profiles missing | must fail explicitly |
| Shared prompt rendering | IMPLEMENTED | `shared/rendering/` |
| Rendering dataset importer | VERIFIED | 20/20 prepare PASS |
| Rendering dataset validation | VERIFIED | 20 images PASS |
| Training environment | VERIFIED | Python 3.12.10, torch 2.8.0+cu128, RTX 5080 |
| Rendering LoRA training | VERIFIED | 2000/2000, TRAIN:OK |
| Rendering LoRA ComfyUI selector normalization | IMPLEMENTED | commits a185ff4 / 9814a36 |
| LoRA-backed FREE generation | VERIFIED at least once | visual sample produced |
| Rendering visual direction | MANUAL PASS on sample | dimensional/matte/depth/anime retained |
| Hand anatomy on sample | FAIL | raised hand/fingers ambiguous |
| Current local shared-rendering JSON | MUST REVERIFY | manual PowerShell encoding incident |
| Hand/anatomy learning | NOT IMPLEMENTED | next candidate layer |
| UI image-to-dataset learning | NOT IMPLEMENTED | discussed only |
| ControlNet/pose reference | NOT IMPLEMENTED | open spec |
| Character LoRA system | NOT IMPLEMENTED as general pipeline | YURA still uses current reference path |
| Outfit learning | NOT IMPLEMENTED | planned modular concern |
| Model registry/rollback | NOT IMPLEMENTED | open spec |
| ComfyUI auto-start | NOT IMPLEMENTED / not agreed | manual service start |

---

## 14. Recommended next-session start sequence

A new chat/session should do this in order:

1. Read `START_HERE.md`.
2. Read this file completely.
3. Read `SPEC.md` and `learning/rendering/README.md` only as supporting implementation docs; this file contains the latest verified checkpoint.
4. Inspect the current main branch before changing code.
5. Reverify/recover the local `shared/rendering/matte_dimensional_anime.json` using the safe Python JSON check above.
6. Ensure LoRA is activated and rebuild `local-RAG` only if a generation test is needed.
7. Do **not** spend time on LoRA-off A/B testing unless the user changes that requirement.
8. Do **not** retrain shared rendering to address the hand defect by default.
9. Continue from the hand/anatomy + UI image-learning design question, first resolving the open specification choices with the user.

---

## 15. Working style / change-control rules for continuation

- Preserve the user's stated objective; do not silently broaden the product.
- Do not reinterpret a failure into a different subsystem without evidence.
- Separate `implemented`, `locally verified`, and `proposed` states.
- Do not claim local execution from Git changes alone.
- If something is unclear, ask rather than inventing a specification.
- Prefer end-to-end scripts/workflows over requiring the user to manually assemble ComfyUI nodes.
- Keep project-created dependencies under `C:\Dev\local-image-generator` unless an existing external runtime such as ComfyUI/SDXL is intentionally referenced.
- Keep FREE and MEMORIELA semantic assets isolated.
- Keep shared rendering limited to rendering/style behavior.

This file is the authoritative continuation checkpoint for work after the first successful learned-rendering LoRA training and LoRA-backed FREE image generation.