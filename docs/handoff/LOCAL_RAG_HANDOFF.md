# local-RAG — Consolidated Handoff

Last consolidated checkpoint: **2026-10-12 JST**

This is the **single authoritative continuation document** for `Pin-Gin/local-image-generator`.

A new chat must read `START_HERE.md`, then this file, then inspect current `main` before changing architecture or implementation. Repository state overrides old chat memory. Specialized documents are references only when consistent with this handoff.

---

## 1. Status vocabulary

Use these labels exactly:

- **VERIFIED** — the user supplied successful local runtime/log/visual evidence.
- **IMPLEMENTED / UNVERIFIED** — code exists in Git but the current path has not been locally confirmed after the change.
- **NOT IMPLEMENTED** — no complete path exists yet.
- **TARGET DESIGN** — architecture is chosen but not fully implemented.
- **OPEN** — intentionally undecided/tunable.

Never promote code existence to VERIFIED.

---

## 2. Working rules / anti-drift

1. Read `START_HERE.md` and this handoff first.
2. Inspect current `main`; Git state overrides chat memory.
3. Keep changes incremental and isolate the failing layer before touching unrelated components.
4. The user runs/verifies Windows/GPU behavior locally. Remote Git edits remain IMPLEMENTED / UNVERIFIED until user evidence arrives.
5. FREE generation must not silently reintroduce Qwen/local conversational AI.
6. MEMORIELA assets/canon must remain isolated from generic FREE.
7. Do not silently rewrite user-authored or local-AI-authored JSON Part semantics.
8. Rendering, lineart, pose, appearance, content and postprocess are separate responsibilities.
9. Manual ComfyUI node work is diagnostic only; production UX must be automated.
10. Preserve durable state during cleanup: `models/`, `database/`, `.env.local-ai`, accepted JSON Parts, Oracle data/volume, Ollama/local-AI models, LoRA training data/weights.
11. Never use `docker compose down -v` as cleanup.
12. Project-created tools belong under `C:\Dev\local-image-generator`; existing external ComfyUI remains under Downloads.
13. Never expose local credentials/secrets.
14. If imported Python changes while the app is running, restart it before judging behavior.

---

## 3. Product identity / boundaries

Application:

```text
local-RAG
repo: Pin-Gin/local-image-generator
local root: C:\Dev\local-image-generator
```

External canon authority:

```text
MEMORIELA
repo: Pin-Gin/MEMORIELA
expected local clone: C:\Dev\MEMORIELA
```

MEMORIELA is not the generic app/build/storage name.

Persistent/state paths to preserve:

```text
models/
database/local_rag.db
learning/local-ai/store/
learning/rendering/
infra/oracle/ + Oracle persistent volume
tools/ollama/
tools/python312/
tools/sd-scripts/
```

---

## 4. Verified local environment

### ComfyUI — VERIFIED

```text
root: C:\Users\shift\Downloads\ComfyUI_windows_portable_nvidia\ComfyUI_windows_portable
API/UI: http://127.0.0.1:8188
ComfyUI: 0.39.0
Python: 3.13.14 embedded
PyTorch: 2.14.0+cu130
GPU: NVIDIA GeForce RTX 5080
VRAM: 16275 MB
```

Project base checkpoint — VERIFIED:

```text
models/checkpoints/sd_xl_base_1.0.safetensors
SHA256: 31E35C80FC4829D14F90153F4C74CD59C90B779F6AFE05A74CD6120B893F7E5B
```

`configure_comfyui_models.ps1` exposes project-owned model directories via ComfyUI `extra_model_paths.yaml`.

### Rendering training — VERIFIED

```text
tools/python312
Python 3.12.10
PyTorch 2.8.0+cu128
CUDA: True
GPU: RTX 5080

tools/sd-scripts
20-image dataset
5 epochs
2000 steps
avr_loss=0.142
[LEARNING:TRAIN:OK]
```

### Local AI / Oracle — VERIFIED foundation

```text
Ollama API: 127.0.0.1:11435
LEARN model: qwen3-vl:8b-instruct
Oracle: 127.0.0.1:1521/FREEPDB1
schema: LOCALRAG_KB1
```

LEARN text/vision inference, Oracle JSON Part lookup, LocalAIToolbox and `verify_local_stack.ps1` have verified foundations.

---

## 5. Fixed responsibility split

### FREE

FREE is deterministic image generation. **No conversational/local-AI interpretation is allowed in the generation path.**

```text
explicit inputs
-> mechanical JSON Part resolution
-> deterministic GenerationPlan
-> deterministic compiler
-> ComfyUI
```

Qwen must not rewrite, sanitize, summarize, select or reinterpret FREE generation content.

### MEMORIELA

MEMORIELA retains AI at planning/canon resolution only.

```text
user request
-> MEMORIELA AI / canon resolution
-> validated structured GenerationPlan
-> common deterministic generation engine
```

### LEARN

LEARN retains local AI for reusable knowledge creation.

```text
text/image/discussion
-> local AI
-> JSON candidate
-> staging
-> explicit acceptance/sync
-> accepted reusable JSON
```

JSON persistence is not model-weight learning. LoRA/dataset training is separate.

---

## 6. FREE deterministic engine — VERIFIED milestones

### Step A — no-Qwen FREE path — VERIFIED

User evidence included:

```text
[FREE:JSON-PART:OK]
[FREE:AI-BYPASS:OK]
[FREE:TEST-CLEANUP:OK]
```

### Step B — deterministic GenerationPlan — VERIFIED

Separate fields exist for content, rendering, lineart, LoRA, pose and postprocess placeholders.

### Step C — content/rendering conditioning + real runtime — VERIFIED

```text
Content CLIP -------\
                     -> ConditioningCombine -> sampler
Rendering CLIP ----/
```

Real ComfyUI output + manifest + SQLite recording was user-verified.

### Step D — checkpoint + lineart channel — VERIFIED technically

Project checkpoint selection works and lineart has a separate conditioning channel. Preferred visual line strength is still tunable.

### Step E — DWPose/OpenPose ControlNet — VERIFIED E2E

Installed/verified stack:

```text
comfyui_controlnet_aux
DWPreprocessor
ControlNetLoader
ControlNetApplyAdvanced
models/controlnet/SDXL/controlnet-openpose-sdxl-1.0/diffusion_pytorch_model.safetensors
```

User verified pose image upload -> DWPose -> OpenPose ControlNet -> sampler -> image -> manifest/SQLite.

Technical execution is VERIFIED; exact pose fidelity is still tunable.

License caveat: the chosen DWPose/OpenPose preprocessor source contains a non-commercial notice. Do not make commercial/redistribution claims without dedicated review.

---

## 7. Rejected appearance approach: img2img source latent

Historical experiment:

```text
source image -> VAEEncode -> sampler latent
pose image -> DWPose / ControlNet
```

User observations:

- low denoise: appearance remained, but original source pose also remained too strongly;
- high denoise: pose had more room, but identity/appearance collapsed into a substantially different image.

Conclusion: source-image latent couples appearance and spatial pose too strongly for the intended FREE system.

The superseded script was removed from current source layout. Git history is the archive. Do not restore this as the primary architecture unless a future explicit experiment proves a new reason.

---

## 8. Current successful direction: IP-Adapter appearance + DWPose pose + fresh latent

IP-Adapter capability — VERIFIED:

```text
[IPADAPTER:NODE:OK] IPAdapterUnifiedLoader
[IPADAPTER:NODE:OK] IPAdapterAdvanced
[IPADAPTER:NODE:OK] IPAdapterModelLoader
[IPADAPTER:NODE:OK] CLIPVisionLoader
[IPADAPTER:MODEL:FILE:OK]
[IPADAPTER:CLIP-VISION:FILE:OK]
[IPADAPTER:MODEL:COMFYUI:OK]
[IPADAPTER:CLIP-VISION:COMFYUI:OK]
[IPADAPTER:POSE-STACK:OK]
[IPADAPTER:CAPABILITY:READY]
```

Project-owned assets:

```text
models/ipadapter/ip-adapter-plus_sdxl_vit-h.safetensors
models/clip_vision/CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors
```

Current authority experiment:

```text
MAIN IMAGE
-> IP-Adapter Plus
-> appearance influence

POSE IMAGE
-> DWPose
-> OpenPose ControlNet
-> spatial pose influence

JSON Part
-> content/delta influence

Rendering Conditioning
Lineart Conditioning
-> drawing/rendering influence

FRESH LATENT
-> SDXL generation
```

User qualitative verification after strengthened settings:

- same fixed conditions are not behaving randomly across repeats;
- main-image appearance remains recognizable;
- output appears to be redrawn/generated anew rather than source-pixel copying;
- pose influence is stronger than the rejected img2img-latent experiment, though not absolute;
- rendering became noticeably stronger.

Current diagnostic defaults that produced this observation:

```text
IP-Adapter weight: 0.75
IP-Adapter start: 0.30
Pose strength: 1.20
Rendering strength: 1.25
Lineart strength: 1.65
Steps: 28
Seed: 975311
Fresh latent / denoise: 1.0
```

These are useful tuning baselines, not immutable production constants.

---

## 9. Fixed FREE input model — TARGET DESIGN

### Two reference-image roles

```text
1. MAIN REFERENCE IMAGE
   mechanism: IP-Adapter
   ownership: face/hair/body/clothing appearance, color, general look

2. POSE REFERENCE IMAGE
   mechanism: DWPose -> OpenPose ControlNet
   ownership: skeleton, posture, limb direction, body placement
```

Do not casually add more reference-image roles; that makes authority ownership ambiguous.

Canonical local stores:

```text
references/free/main/
references/free/pose/
```

Actual user images are ignored by Git by default.

### Five bounded JSON content slots

```text
1. CHARACTER / BODY
2. OUTFIT / PROP
3. EXPRESSION / FACE
4. CAMERA / COMPOSITION
5. BACKGROUND / SCENE
```

Each production slot should hold zero or one explicit Part ref. Unused slots may be null.

Rendering and lineart are **not** part of these five slots.

Machine-readable target contract:

```text
schemas/free_generation_input.schema.json
```

The lower-level existing Parts array can remain for compatibility/internal mechanics, but production UI/contract should enforce role ownership rather than an unlimited unordered list.

FREE does not use AI to resolve contradictory Parts. Reject/surface conflicts where structurally detectable; never silently choose a semantic winner.

---

## 10. Rendering Authority — fixed artistic direction

Working identity:

```text
Matte Dimensional Anime
```

Rendering must become the strongest persistent **drawing-method** authority.

Required characteristics:

```text
ANIME FOUNDATION
- clearly anime / illustration based
- not live action
- not photoreal human texture

REAL-ANIME FORM
- face/body/hair/clothing retain readable form/mass
- cheeks, nose, jaw, neck, limbs and torso read as volumes
- avoid flat featureless cel planes

MATTE MATERIAL RESPONSE
- low gloss / restrained highlights
- no plastic CGI look
- no PBR material dominance
- stylized anime skin

DEPTH / SPACE
- foreground, subject, midground, background separation
- readable perspective and spatial layering
- visible depth rather than flat poster-like composition

SLIGHT 3D-ANIME DIMENSIONALITY
- mild modeled 3D-anime feeling
- still unmistakably illustration/anime, not raw 3D render

LINE CLARITY
- contours remain visible and intentional
- face/body/hair/clothing boundaries do not dissolve into shading
- stronger line presence than the old medium-fine/subordinate setting
```

Responsibility rule:

```text
what is drawn              -> five JSON content slots
who/how they look          -> MAIN IMAGE / IP-Adapter
how they move              -> POSE IMAGE / DWPose-ControlNet
how the image is drawn     -> Rendering Authority
how clear/strong contours  -> Lineart Authority
```

Rendering and lineart remain separate channels.

Current `shared/rendering/matte_dimensional_anime.json` still has Rendering LoRA `enabled: false`; do not silently enable it. The trained LoRA previously worked, but it must be reintroduced explicitly into the new authority stack when chosen.

---

## 11. JSON generation / sync policy

The user intends local AI to create detailed JSON, including content the remote assistant does not need to semantically inspect.

Desired flow:

```text
local AI produces JSON
-> learning/local-ai/store/staging/
-> structural validation
-> explicit acceptance/sync
-> learning/local-ai/store/json-parts/
-> FREE mechanically references exact Part IDs
```

Sync/accept must preserve payload semantics. It may mechanically validate:

```text
valid JSON
schema/version
part_id/version
role / part_type
filename/ref consistency
status
SHA256
```

Do not weaken, summarize, normalize or rewrite payload prose merely to synchronize it.

Canonical Part ref remains:

```text
part:<part_id>@<version>
```

The structural sync/accept utility for the new bounded-slot workflow is **NOT IMPLEMENTED yet**.

---

## 12. Repository reorganization — PHASE 1 IMPLEMENTED / UNVERIFIED locally

The repository was reorganized in Git after the user requested a cleanup. The layout changes themselves are not locally verified until the user pulls them.

Canonical layout document:

```text
docs/architecture/REPOSITORY_LAYOUT.md
```

Current responsibility map:

```text
src/          production Python runtime/app engine
ui/           desktop/webview frontend
references/   FREE reference images
shared/       Rendering + Lineart authorities
profiles/     generation profiles
workflows/    ComfyUI API workflow templates
schemas/      machine contracts
learning/     local-AI JSON lifecycle + rendering training
models/       project-owned large model assets
config/       app/local-AI/tool configuration
infra/        Oracle/infrastructure
experiments/  diagnostic code only
tests/        repeatable validation/capability probes
scripts/      future setup/maintenance/training script grouping
database/     SQLite state
outputs/      generated output
cache/        temporary compiler/experiment data
logs/         runtime logs
tools/        installed project-local runtimes/tools
```

Implemented cleanup actions:

- created `references/free/main/` and `references/free/pose/`;
- `.gitignore` now keeps actual FREE reference images local-only;
- added `schemas/free_generation_input.schema.json` for two images + five slots + Rendering/Lineart profiles;
- created `experiments/` and moved the active IP-Adapter authority diagnostic out of `src/`;
- removed the superseded img2img-authority experiment from current tree (Git history retains it);
- created `tests/` organization and migrated standalone IP-Adapter and pose capability probes to `tests/capabilities/`;
- updated installers to point to the migrated capability probes;
- created `scripts/README.md` but intentionally did **not** mass-move root PowerShell scripts because several derive repo root from `$MyInvocation.MyCommand.Path` and blind relocation could break working paths;
- updated `START_HERE.md`, root `README.md`, `domains/free/README.md`, `models/README.md` and this handoff.

The cleanup is deliberately conservative: durable data and known runtime code were not deleted for aesthetics.

Several historical `*_test.py` files still remain in `src/`. They should be migrated gradually only when imports/commands are updated and locally verified.

---

## 13. Current important paths after reorganization

### Production FREE engine

```text
src/free_generation_plan.py
src/free_compiler.py
src/free_runtime.py
src/generation_bridge.py
src/comfyui_client.py
src/model_catalog.py
```

### Active authority diagnostic

```text
experiments/active/free_ipadapter_pose_json_experiment.py
```

### Capability probes

```text
tests/capabilities/ipadapter_capability_test.py
tests/capabilities/pose_control_capability_test.py
```

### Authority data

```text
shared/rendering/matte_dimensional_anime.json
shared/lineart/strong_anime_lineart.json
profiles/free_sdxl_v1.json
workflows/free_sdxl_conditioned_api.json
```

### FREE reference images

```text
references/free/main/
references/free/pose/
```

### JSON lifecycle

```text
src/json_parts.py
learning/local-ai/JSON_PARTS.md
learning/local-ai/store/staging/
learning/local-ai/store/json-parts/
```

### Local AI / Oracle

```text
src/local_ai_client.py
src/local_ai_tools.py
src/oracle_knowledge_store.py
config/local_ai.json
config/local_tools.json
infra/oracle/
```

---

## 14. Postprocess remains deferred

The user explicitly chose to establish high-level intended behavior first.

Do not jump to hand/finger/face correction while appearance/pose/rendering/lineart authority balance is still being finalized.

Later order remains:

```text
targeted Inpaint
-> Detailer
-> Upscale
```

---

## 15. Open/tunable items

- exact IP-Adapter weight/start schedule;
- exact DWPose/ControlNet strength for stronger pose fidelity;
- final Lineart Authority strength and wording;
- explicit structured Matte Dimensional Anime Rendering JSON vNext;
- whether/when to enable the trained Rendering LoRA in the new stack;
- mechanical staging -> accepted JSON sync/validation utility;
- production runtime support for the bounded five-slot contract;
- desktop UI for MAIN image + POSE image + five JSON slots + Rendering/Lineart;
- targeted Inpaint / Detailer / Upscale after core behavior stabilizes.

---

## 16. Immediate next work order

Unless the user changes priority:

1. Pull and locally verify the repository reorganization paths.
2. Put test/user reference images under `references/free/main/` and `references/free/pose/`.
3. Build mechanical JSON staging -> accepted sync/validation without semantic rewriting.
4. Rewrite/strengthen Matte Dimensional Anime into explicit structured Rendering Authority JSON.
5. Make runtime consume the bounded two-image + five-slot contract.
6. A/B tune appearance, pose, rendering and lineart authorities.
7. Only then add targeted correction/postprocess.

---

## 17. Commands after reorganization

From:

```powershell
cd C:\Dev\local-image-generator
```

IP-Adapter capability:

```powershell
.\tools\python312\python.exe .\tests\capabilities\ipadapter_capability_test.py
```

Pose capability:

```powershell
.\tools\python312\python.exe .\tests\capabilities\pose_control_capability_test.py
```

Active experiment CLI sanity check:

```powershell
.\tools\python312\python.exe .\experiments\active\free_ipadapter_pose_json_experiment.py --help
```

JSON Part read (legacy location, not yet migrated):

```powershell
.\tools\python312\python.exe .\src\json_part_read_test.py --ref part:<part_id>@<version>
```

Local stack:

```powershell
.\verify_local_stack.ps1
```

PowerShell policy failures should normally use per-invocation bypass rather than global policy changes:

```powershell
powershell -ExecutionPolicy Bypass -File .\<script>.ps1
```

---

## 18. Final continuation vector

The current FREE project is **not** generic prompt engineering and **not** source-image img2img.

The intended system is:

```text
MAIN IMAGE
-> IP-Adapter appearance authority

POSE IMAGE
-> DWPose / OpenPose ControlNet pose authority

FIVE ROLE-BOUND JSON SLOTS MAX
-> content/deltas

RENDERING AUTHORITY
-> strongest persistent drawing-method definition
-> matte + anime realism + depth + slight 3D-anime dimensionality

LINEART AUTHORITY
-> independently strong/clear contours

FRESH LATENT
-> redraw/generate final image
```

Local AI creates reusable JSON in LEARN. FREE consumes accepted structured inputs mechanically. MEMORIELA remains a separate canon-aware planning domain.

Do not collapse these authorities into one prompt, do not let one image silently own all responsibilities, and do not reintroduce Qwen into FREE.