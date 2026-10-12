# local-RAG — Consolidated Handoff

Last consolidated checkpoint: **2026-10-12 JST**

This is the single authoritative continuation document for `Pin-Gin/local-image-generator`.

A new chat must read `START_HERE.md`, then this file, then inspect current `main`. Repository state overrides old chat memory.

---

## 1. Status vocabulary

- **VERIFIED** — user supplied successful local runtime/log/visual evidence.
- **IMPLEMENTED / UNVERIFIED** — code exists in Git but the current path has not yet been locally confirmed.
- **NOT IMPLEMENTED** — no complete path exists yet.
- **TARGET DESIGN** — architecture is chosen but not fully implemented.
- **OPEN** — intentionally tunable/undecided.

Never promote code existence to VERIFIED.

---

## 2. Non-negotiable working rules

1. FREE generation must not reintroduce Qwen/local conversational AI into generation interpretation.
2. MEMORIELA canon/assets remain isolated from generic FREE.
3. Local-AI/user JSON semantics must not be silently rewritten during persistence/sync.
4. Appearance, pose, JSON content, rendering, lineart and later postprocess are separate authorities.
5. Manual ComfyUI work is diagnostic only; production must be automated.
6. Preserve `models/`, `database/`, `.env.local-ai`, accepted JSON, Oracle persistent data, Ollama/local-AI models and LoRA assets during cleanup.
7. Never use `docker compose down -v` as cleanup.
8. The user verifies Windows/GPU behavior locally; Git edits remain UNVERIFIED until local evidence is supplied.
9. Rendering LoRA must not be silently enabled. Current shared rendering config still has it disabled.
10. Do not restore the rejected source-latent img2img architecture as the primary FREE path.

---

## 3. Project boundaries

Application:

```text
local-RAG
repo: Pin-Gin/local-image-generator
local root: C:\Dev\local-image-generator
```

MEMORIELA is a separate canon repository:

```text
repo: Pin-Gin/MEMORIELA
expected local clone: C:\Dev\MEMORIELA
```

Do not use MEMORIELA as the generic app/build/storage name.

---

## 4. Verified local environment

### ComfyUI — VERIFIED

```text
C:\Users\shift\Downloads\ComfyUI_windows_portable_nvidia\ComfyUI_windows_portable
API/UI: http://127.0.0.1:8188
ComfyUI: 0.39.0
Python: 3.13.14 embedded
PyTorch: 2.14.0+cu130
GPU: RTX 5080 16GB
```

Base checkpoint — VERIFIED:

```text
models/checkpoints/sd_xl_base_1.0.safetensors
SHA256: 31E35C80FC4829D14F90153F4C74CD59C90B779F6AFE05A74CD6120B893F7E5B
```

### Rendering training foundation — VERIFIED

```text
tools/python312
Python 3.12.10
PyTorch 2.8.0+cu128
CUDA true / RTX 5080
20-image dataset
5 epochs / 2000 steps
avr_loss=0.142
[LEARNING:TRAIN:OK]
```

### Local AI / Oracle foundation — VERIFIED

```text
Ollama API: 127.0.0.1:11435
LEARN model: qwen3-vl:8b-instruct
Oracle: 127.0.0.1:1521/FREEPDB1
schema: LOCALRAG_KB1
```

---

## 5. Fixed domain responsibilities

### FREE

Deterministic image generation only.

```text
explicit inputs
-> mechanical JSON resolution
-> deterministic GenerationPlan/compiler
-> ComfyUI
```

No Qwen semantic interpretation/rewriting in FREE generation.

### MEMORIELA

AI may plan/resolve canon, then hands a validated structured plan to the deterministic engine.

### LEARN

Local AI creates reusable JSON candidates.

```text
instruction/image
-> local AI JSON candidate
-> status=staging
-> structural validation
-> explicit user acceptance
-> accepted JSON
```

JSON persistence is not model-weight learning.

---

## 6. FREE engine milestones

### A. FREE AI bypass — VERIFIED

```text
[FREE:JSON-PART:OK]
[FREE:AI-BYPASS:OK]
```

### B. Deterministic GenerationPlan — VERIFIED

Separate content/rendering/lineart/LoRA/pose/postprocess fields exist.

### C. Content + Rendering conditioning runtime — VERIFIED

Content CLIP and Rendering CLIP combine deterministically before sampling.

### D. Checkpoint + separate Lineart channel — VERIFIED technically

Line strength remains tunable.

### E. DWPose/OpenPose ControlNet — VERIFIED E2E

```text
DWPreprocessor
ControlNetLoader
ControlNetApplyAdvanced
models/controlnet/SDXL/controlnet-openpose-sdxl-1.0/diffusion_pytorch_model.safetensors
```

Current capability commands after repository reorganization were user-verified again on 2026-10-12:

```text
[IPADAPTER:CAPABILITY:READY]
[POSE:CAPABILITY:READY]
```

---

## 7. Rejected source-latent approach

Rejected architecture:

```text
source image -> VAEEncode -> sampler latent
pose image -> DWPose / ControlNet
```

Observed failure mode:

- low denoise kept appearance but also locked source pose;
- high denoise allowed pose movement but destroyed appearance consistency.

Conclusion: source latent couples appearance and spatial pose too strongly for the intended authority split.

---

## 8. Current successful FREE authority architecture

```text
MAIN IMAGE
-> IP-Adapter Plus
-> appearance authority

POSE IMAGE
-> DWPose
-> OpenPose ControlNet
-> pose authority

FIVE JSON CONTENT SLOTS
-> explicit content/deltas

RENDERING AUTHORITY
-> drawing method

LINEART AUTHORITY
-> contour clarity

FRESH LATENT
-> redraw/generate final image
```

User qualitative verification:

- fixed seed/inputs repeat deterministically enough for A/B comparison;
- main-image appearance remains recognizable;
- output is redrawn rather than source-pixel copied;
- pose influence is materially stronger than the rejected img2img-latent experiment;
- rendering became stronger after conditioning increases.

Current useful diagnostic baseline:

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

These are tuning baselines, not permanent production constants.

---

## 9. Fixed production input model

### Reference images — exactly two roles

```text
references/free/main/
-> MAIN IMAGE / IP-Adapter / appearance

references/free/pose/
-> POSE IMAGE / DWPose-ControlNet / pose
```

Actual user images remain local-only and ignored by Git.

### Five bounded JSON content slots

```text
1. character_body
2. outfit_prop
3. expression_face
4. camera_composition
5. background_scene
```

Each slot holds zero or one exact `part:<id>@<version>` reference.

Rendering and lineart are not ordinary content slots.

Machine contract:

```text
schemas/free_generation_input.schema.json
```

Do not turn the production UI into an unlimited unordered JSON-Part list.

---

## 10. Rendering Authority

Working identity:

```text
Matte Dimensional Anime
```

Fixed artistic target:

```text
ANIME FOUNDATION
- clearly anime/illustration
- not photoreal/live action

REAL-ANIME FORM
- readable face/body/hair/clothing mass and volume
- avoid flat featureless cel planes

MATTE MATERIAL
- restrained gloss/highlights
- no plastic CGI or PBR dominance
- stylized anime skin

DEPTH
- foreground/subject/midground/background separation
- readable perspective and spatial layering

SLIGHT 3D-ANIME DIMENSIONALITY
- mild modeled depth/form
- still unmistakably illustration, not raw 3D

LINE CLARITY
- intentional visible contours
- face/body/hair/clothing boundaries remain readable
```

Responsibility:

```text
what is drawn             -> JSON slots
who/how they look         -> MAIN IMAGE
how they move             -> POSE IMAGE
how the image is drawn    -> Rendering Authority
how clear contours are    -> Lineart Authority
```

Rendering LoRA remains disabled until explicitly reintroduced and validated.

---

## 11. JSON staging / sync lifecycle

Canonical ref:

```text
part:<part_id>@<version>
```

Stores:

```text
learning/local-ai/store/staging/
learning/local-ai/store/json-parts/
learning/local-ai/store/receipts/
```

### Core mechanical sync — VERIFIED

Implemented in:

```text
src/json_part_sync.py
tests/integration/json_part_sync_test.py
```

User-local verification on 2026-10-12:

```text
[JSON-SYNC:STAGE:OK]
[JSON-SYNC:HASH-GATE:OK]
[JSON-SYNC:PAYLOAD-PRESERVED:OK]
[JSON-SYNC:ACCEPT:OK]
[JSON-SYNC:ROLE-GATE:OK]
[JSON-SYNC:TEST:OK]
```

Rules enforced by the core lifecycle:

- canonical JSON structure is validated;
- FREE `part_type` is restricted to the five production slot roles;
- accepted ID/version cannot be silently overwritten;
- staging SHA256 gates acceptance;
- acceptance may change `status: staging -> accepted` only;
- payload semantic SHA256 must remain unchanged;
- an acceptance receipt is written.

### Desktop/API hash-gated acceptance — VERIFIED

Implemented in:

```text
src/ui_server.py
ui/json_download.js
tests/integration/json_part_ui_api_test.py
```

User-local verification on 2026-10-12:

```text
[JSON-UI-API:HTTP:OK]
[JSON-UI-API:HASH-GATED-ACCEPT:OK]
[JSON-UI-API:PAYLOAD-PRESERVED:OK]
[JSON-UI-API:RECEIPT:OK]
[JSON-UI-API:TEST:OK]
```

The `Part採用` path is therefore verified to route through the same structural validation and hash-gated acceptance logic at the API integration level.

The next remaining proof is the **real interactive LEARN chat path**: local AI emits one staging JSON candidate, user clicks `Part採用`, and the resulting accepted file/receipt are confirmed.

---

## 12. Repository organization

Phase 1 reorganization is **VERIFIED locally** for the moved capability/experiment paths.

```text
src/          production runtime
ui/           frontend
references/   local FREE reference images
shared/       Rendering + Lineart authorities
profiles/     generation profiles
workflows/    ComfyUI workflow templates
schemas/      machine contracts
learning/     local-AI JSON lifecycle + rendering training
models/       model assets
config/       configuration
infra/        Oracle/infrastructure
experiments/  diagnostic experiments
tests/        validation/capability/integration tests
scripts/      setup/maintenance grouping target
database/     SQLite state
outputs/      generated outputs
cache/        temporary data
logs/         logs
tools/        project-local runtimes/tools
```

Active experiment:

```text
experiments/active/free_ipadapter_pose_json_experiment.py
```

Capability probes:

```text
tests/capabilities/ipadapter_capability_test.py
tests/capabilities/pose_control_capability_test.py
```

---

## 13. Current implementation priorities

1. **Verify the real interactive LEARN chat -> staging JSON -> Part採用 path.**
2. Rewrite/strengthen `Matte Dimensional Anime` as explicit structured Rendering Authority JSON.
3. Make production FREE runtime consume the two-image + five-slot input contract directly.
4. A/B tune appearance, pose, rendering and lineart.
5. Only after high-level authority balance works: targeted Inpaint -> Detailer -> Upscale.

Do not jump to hand/finger/face detail correction before the high-level authority stack is settled.

---

## 14. Current verification commands

From:

```powershell
cd C:\Dev\local-image-generator
```

Core JSON sync:

```powershell
.\tools\python312\python.exe .\tests\integration\json_part_sync_test.py
```

Desktop/API JSON acceptance integration:

```powershell
.\tools\python312\python.exe .\tests\integration\json_part_ui_api_test.py
```

IP-Adapter capability:

```powershell
.\tools\python312\python.exe .\tests\capabilities\ipadapter_capability_test.py
```

Pose capability:

```powershell
.\tools\python312\python.exe .\tests\capabilities\pose_control_capability_test.py
```

Authority experiment CLI:

```powershell
.\tools\python312\python.exe .\experiments\active\free_ipadapter_pose_json_experiment.py --help
```

---

## 15. Continuation vector

The project direction is not generic prompt engineering and not img2img source-latent editing.

The intended FREE system is:

```text
MAIN IMAGE -> appearance
POSE IMAGE -> pose
FIVE ROLE-BOUND JSON SLOTS -> content/deltas
RENDERING AUTHORITY -> strongest persistent drawing method
LINEART AUTHORITY -> independent contour strength
FRESH LATENT -> redraw final image
```

LEARN creates reusable staging JSON. User acceptance promotes it mechanically without semantic rewriting. FREE consumes accepted structured inputs deterministically. MEMORIELA remains a separate canon-aware planning domain.
