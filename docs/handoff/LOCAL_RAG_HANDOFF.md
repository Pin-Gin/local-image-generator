# local-RAG — Consolidated Handoff

Last consolidated checkpoint: **2026-10-12 JST**

This file is the **single authoritative continuation document** for a new ChatGPT session working on `Pin-Gin/local-image-generator`.

Read `START_HERE.md`, then this file completely, then inspect the current `main` branch before changing architecture or implementation. Repository state overrides chat memory. Specialized documents are references only when they do not conflict with this handoff.

---

## 1. Status vocabulary

Use these labels exactly:

- **VERIFIED** — the user supplied successful local runtime evidence or direct local visual observation.
- **IMPLEMENTED / UNVERIFIED** — code exists in Git but the current path has not been confirmed locally.
- **NOT IMPLEMENTED** — no complete runtime path exists yet.
- **TARGET DESIGN** — the user chose the architecture, but code is not yet fully changed to match it.
- **OPEN** — intentionally undecided.

Never promote code existence to VERIFIED.

---

## 2. Working method / anti-drift rules

1. Read `START_HERE.md` and this handoff first.
2. Inspect current `main`; Git state overrides old chat memory.
3. Keep work incremental and isolate one failing layer at a time.
4. The user runs and verifies Windows/GPU behavior locally. Remote Git changes are only IMPLEMENTED / UNVERIFIED until the user reports results.
5. FREE generation must not silently reintroduce Qwen/local conversational AI.
6. MEMORIELA and FREE assets/authority must remain separate.
7. Do not silently rewrite user-authored or local-AI-authored JSON Part semantics.
8. Do not infer missing requirements. Ask only when a genuinely required decision is unresolved.
9. Rendering, line art, pose, appearance, content and postprocess are separate responsibilities. Do not solve one by distorting another.
10. Manual ComfyUI work is diagnostic only. Production UX must be automated by the app/API path.
11. Preserve durable local state: `models/`, `database/`, `.env.local-ai`, accepted local JSON Parts, Oracle persistent data, local AI/Ollama models, trained LoRA data/weights. Never use `docker compose down -v` as cleanup.
12. Project-created tools live under `C:\Dev\local-image-generator`; the existing external ComfyUI portable runtime remains outside the repo.
13. Do not expose local credentials or secrets.
14. If imported Python changes while the app is running, restart it before judging behavior.

---

## 3. Product identity and source boundaries

Application/repository:

```text
local-RAG
repo: Pin-Gin/local-image-generator
local root: C:\Dev\local-image-generator
```

External MEMORIELA authority:

```text
repo: Pin-Gin/MEMORIELA
expected local clone: C:\Dev\MEMORIELA
```

`MEMORIELA` is a canon/character/brand authority, not the generic app/build/storage name.

Current persistent/state locations that must survive cleanup:

```text
models/
database/local_rag.db
learning/local-ai/store/
learning/rendering/
infra/oracle/ + Oracle container persistent volume
tools/ollama/          # local runtime/model data when installed
tools/python312/       # project-local Python runtime when installed
tools/sd-scripts/      # rendering training environment when installed
outputs/               # generated output; disposable by policy but not delete without user intent
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

Project checkpoint exposure — VERIFIED:

```text
C:\Dev\local-image-generator\models\checkpoints\sd_xl_base_1.0.safetensors
SHA256: 31E35C80FC4829D14F90153F4C74CD59C90B779F6AFE05A74CD6120B893F7E5B
```

`configure_comfyui_models.ps1` exposes project-owned model directories through ComfyUI `extra_model_paths.yaml`.

### Rendering training — VERIFIED

```text
tools\python312
Python 3.12.10
PyTorch 2.8.0+cu128
CUDA: True
GPU: RTX 5080

tools\sd-scripts
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

LEARN text/vision inference, Oracle JSON Part lookup, LocalAIToolbox, password rotation and the disposable `verify_local_stack.ps1` flow were previously VERIFIED.

---

## 5. Responsibility split — fixed architecture

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

MEMORIELA retains AI at the planning/canon layer only.

```text
user request
  -> MEMORIELA AI / canon resolution
  -> validated structured GenerationPlan
  -> common deterministic generation engine
```

MEMORIELA identity assets must not leak into generic FREE generation.

### LEARN

LEARN retains local AI for knowledge/JSON creation.

```text
text/image/discussion
  -> local AI
  -> JSON candidate
  -> staging
  -> explicit acceptance/sync
  -> accepted reusable JSON
```

JSON persistence is not model-weight learning. LoRA/dataset training remains a separate lifecycle.

---

## 6. FREE deterministic engine — VERIFIED milestones

### Step A — no-Qwen FREE path — VERIFIED

User-verified evidence included:

```text
[FREE:JSON-PART:OK]
[FREE:AI-BYPASS:OK]
[FREE:TEST-CLEANUP:OK]
```

### Step B — deterministic FREE GenerationPlan — VERIFIED

Separate contract fields exist for content, rendering, lineart, LoRA, pose and postprocess placeholders.

### Step C — content/rendering conditioning + real ComfyUI runtime — VERIFIED

Compiler wiring:

```text
Content CLIP -------\
                     -> ConditioningCombine -> sampler
Rendering CLIP ----/
```

User-verified real runtime output, manifest and SQLite recording succeeded.

### Step D — checkpoint + lineart channel — VERIFIED technically

Project checkpoint catalog and separate lineart conditioning path are operational.

Important quality boundary: the lineart channel executes, but its final preferred visual strength is still being tuned.

### Step E — DWPose/OpenPose ControlNet — VERIFIED E2E

Installed/verified stack:

```text
comfyui_controlnet_aux
DWPreprocessor
ControlNetLoader
ControlNetApplyAdvanced
xinsir/controlnet-openpose-sdxl-1.0
```

User-verified runtime path:

```text
pose image upload
-> DWPose
-> SDXL OpenPose ControlNet
-> KSampler
-> output image
-> manifest / SQLite
```

Technical execution is VERIFIED. Exact pose fidelity remains a tunable quality property.

Licensing note: the selected DWPose/OpenPose preprocessor source contains a non-commercial licensing notice. Do not make commercial/redistribution claims without a dedicated license review.

---

## 7. Appearance authority experiment — img2img rejected as final architecture

The first source-image experiment used:

```text
source image -> VAEEncode -> KSampler latent
pose image -> DWPose / ControlNet
```

User observations:

- lower denoise retained the original appearance but also retained the original pose too strongly;
- higher denoise let pose move more but the result became a substantially different image/person.

Conclusion: **img2img latent couples appearance and spatial pose too strongly for the intended FREE architecture.**

`src/free_image_pose_authority_experiment.py` is historical/superseded diagnostic code and must not define the production direction.

---

## 8. IP-Adapter appearance authority — current successful direction

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

Installed project-owned models:

```text
models/ipadapter/ip-adapter-plus_sdxl_vit-h.safetensors
models/clip_vision/CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors
```

Current experiment uses a **fresh latent**, not source-image VAE latent:

```text
main reference image
  -> IP-Adapter Plus
  -> appearance influence

pose reference image
  -> DWPose
  -> OpenPose ControlNet
  -> spatial pose influence

JSON Part
  -> content/delta influence

Rendering Conditioning
Lineart Conditioning
  -> drawing/rendering influence

fresh latent
  -> SDXL generation
```

### User-verified qualitative observation

With the strengthened diagnostic configuration, the user observed:

- repeated generation under the same fixed conditions is not behaving randomly;
- the original/main-image appearance remains recognizable;
- the output appears to be **redrawn/generated anew rather than copying source pixels directly**;
- pose influence is noticeably stronger than the earlier img2img-latent experiment, though not yet absolute;
- rendering became noticeably stronger.

This is the current direction. Do not revert to source-image VAE latent as the primary appearance-authority mechanism unless a new experiment explicitly justifies it.

---

## 9. New fixed FREE input model — TARGET DESIGN

The user chose a bounded input model instead of unlimited JSON accumulation.

### Image inputs — exactly two conceptual roles

```text
1. MAIN REFERENCE IMAGE
   role: appearance authority
   mechanism: IP-Adapter
   target: face, hair, body appearance, clothing appearance, colors, general look

2. POSE REFERENCE IMAGE
   role: spatial/body-pose authority
   mechanism: DWPose -> OpenPose ControlNet
   target: skeleton, posture, arm/leg direction, body placement
```

Do not add extra reference-image roles casually. Additional reference images make authority ownership ambiguous.

### JSON slots — maximum about five role slots

Target slot set:

```text
1. CHARACTER / BODY
2. OUTFIT / PROP
3. EXPRESSION / FACE
4. CAMERA / COMPOSITION
5. BACKGROUND / SCENE
```

Each slot should hold zero or one explicit JSON Part reference in the production UI/contract. Internally a Part can remain structured and detailed.

FREE does **not** resolve semantic conflicts with AI. Contradictory JSON Parts must be rejected by structural/role validation where possible or surfaced to the user; do not silently choose a winner.

### Separate authority channels — not counted in the five content slots

```text
RENDERING PROFILE
LINEART PROFILE
```

Rendering and lineart are persistent drawing-method authorities, not ordinary scene/content JSON Parts.

---

## 10. Rendering authority — fixed artistic target

The desired drawing method is more specific than the previous generic style prompt.

Working name remains:

```text
Matte Dimensional Anime
```

Target characteristics:

```text
ANIME FOUNDATION
- clearly anime / illustration based
- not live action
- not photoreal human texture

REAL-ANIME FORM
- face/body/hair/clothing must have readable form and mass
- avoid flat featureless cel planes
- cheeks, nose, jaw, neck, limbs and torso should read as volumes

MATTE MATERIAL RESPONSE
- low-gloss / restrained highlights
- no plastic CGI look
- no PBR-style material dominance
- skin remains stylized anime skin

DEPTH / SPACE
- foreground, subject, midground and background separation
- readable perspective and spatial layering
- visible depth rather than flat poster-like composition

SLIGHT 3D-ANIME DIMENSIONALITY
- enough modeled form to feel mildly 3D/anime-rendered
- must still read as an illustration/anime image, not a raw 3D render

LINE CLARITY
- contours must remain visible and intentional
- face/body/hair/clothing boundaries must not dissolve into soft shading
- stronger line presence than the earlier medium-fine/subordinate setting
- lineart is controlled separately from rendering depth
```

The user wants this rendering description made more explicit as structured JSON and then used as the **strongest drawing-method authority**.

Important implementation principle:

```text
What is drawn       -> JSON content slots
Who/how they look   -> main reference image / IP-Adapter
How they move       -> pose reference image / DWPose-ControlNet
How the image is drawn -> Rendering Authority
How strong/clear contours are -> Lineart Authority
```

A longer prompt alone is not sufficient. Rendering authority should be structurally strong through dedicated conditioning and, when explicitly enabled/validated, the trained Rendering LoRA.

Current `shared/rendering/matte_dimensional_anime.json` still has its LoRA `enabled: false`; do not silently enable it.

---

## 11. JSON generation/sync policy

The user intends to let the **local AI** produce detailed JSON, including content the remote assistant does not need to semantically inspect.

Desired operational flow:

```text
local AI produces JSON
-> learning/local-ai/store/staging/
-> structural validation
-> explicit acceptance/sync
-> learning/local-ai/store/json-parts/
-> FREE mechanically references exact Part IDs
```

The sync/accept layer should be able to operate without semantically rewriting the JSON. It may validate mechanically:

```text
valid JSON
schema/version
part_id/version
role / part_type
filename/ref consistency
status
SHA256
```

Do not weaken, summarize or normalize payload prose merely to sync it.

Manual structured JSON compatibility remains supported. Exact ref syntax remains:

```text
part:<part_id>@<version>
```

---

## 12. Reference-image storage decision

A project-local FREE reference store is the chosen direction:

```text
C:\Dev\local-image-generator\references\free\main\
C:\Dev\local-image-generator\references\free\pose\
```

Responsibilities:

```text
references/free/main/ -> IP-Adapter appearance sources
references/free/pose/ -> DWPose pose sources
```

These are local runtime assets, not MEMORIELA canon assets. By default actual image files should stay out of Git; only directory documentation/placeholders should be tracked.

Production input should ultimately reference these assets through deterministic relative paths/IDs rather than arbitrary implicit selection.

---

## 13. Current generation contract direction

Target production request shape conceptually:

```json
{
  "main_image": "references/free/main/example.png",
  "pose_image": "references/free/pose/example.png",
  "parts": {
    "character_body": "part:...@1",
    "outfit_prop": "part:...@1",
    "expression_face": "part:...@1",
    "camera_composition": "part:...@1",
    "background_scene": "part:...@1"
  },
  "rendering_profile": "matte-dimensional-anime",
  "lineart_profile": "strong-anime-lineart"
}
```

Null/unused content slots are allowed. Do not turn the five-slot design into an unlimited unordered Part list in the production UI.

The existing lower-level JSON Parts array support can remain for compatibility/internal implementation, but the user-facing design should enforce role ownership.

---

## 14. Current verified / open quality state

### VERIFIED / sufficiently established to continue

- FREE can bypass local conversational AI.
- deterministic GenerationPlan exists.
- separate content and rendering conditioning executes.
- project checkpoint selection works.
- lineart has a separate conditioning path.
- DWPose/OpenPose ControlNet executes E2E.
- IP-Adapter Plus SDXL + CLIP Vision are installed and recognized by ComfyUI.
- fresh-latent IP-Adapter + DWPose direction preserves main-image appearance better than pure text generation while allowing more pose movement than source-latent img2img.
- repeated fixed-condition output is sufficiently deterministic for A/B diagnosis.
- stronger rendering/lineart conditioning produced a visible improvement according to the user.

### OPEN / needs tuning

- exact IP-Adapter weight/start schedule for best appearance vs pose balance.
- exact DWPose/ControlNet strength needed for stronger pose fidelity.
- final lineart strength; current line clarity is still a priority.
- explicit structured Rendering JSON vNext.
- whether/when to enable the trained Rendering LoRA in the new IP-Adapter + pose pipeline.
- hand/finger/face/body correction pipeline.
- targeted Inpaint, Detailer and Upscale.
- desktop UI for two reference images + five JSON slots + rendering/lineart authorities.

---

## 15. Postprocess remains deferred

The user explicitly chose to solve the high-level intended behavior before fine anatomical correction.

Do not jump ahead to hand/detailer/inpaint work while the core authority balance is still being established.

Later order remains:

```text
targeted Inpaint
-> Detailer
-> Upscale
```

---

## 16. Repository organization direction

The repository has accumulated diagnostic/test artifacts in `src/` and many root-level support scripts. Cleanup must preserve working runtime behavior while separating responsibilities.

Canonical responsibility map going forward:

```text
src/          production Python runtime/app engine
ui/           desktop/webview frontend
references/   user-supplied FREE reference images (actual images ignored by Git)
shared/       global generation authorities: rendering + lineart
profiles/     engine/generation profiles
workflows/    ComfyUI API workflow templates
learning/     local-AI knowledge lifecycle + rendering training lifecycle
models/       project-owned large model assets, ignored by Git
config/       app/local-AI/tool config
schemas/      machine contracts
infra/        Oracle and infrastructure
docs/         handoff + architecture documentation
outputs/      generated images/manifests
cache/        compiler/experiment cache
logs/         runtime logs
database/     SQLite state
tools/        installed project-local runtimes/tools
experiments/  active/historical diagnostic scripts only; not production engine
scripts/      setup/maintenance wrappers when root scripts are safely migrated
```

Do not perform a mass move that breaks known runtime commands merely for aesthetics. First classify, then migrate with compatibility or updated call sites.

Historical/superseded diagnostic code should not remain mixed with production logic indefinitely. Git history is the archive; dead diagnostic code may be removed after its conclusions are captured here.

---

## 17. Immediate next work order

Current priority after this handoff update:

1. **Repository/directory cleanup** without destroying persistent local state.
2. Create canonical `references/free/main/` and `references/free/pose/` stores.
3. Formalize the two-image + five-slot + Rendering/Lineart request contract.
4. Add mechanical JSON staging -> accepted sync/validation without semantic rewriting.
5. Rewrite/strengthen Matte Dimensional Anime as an explicit structured Rendering Authority JSON.
6. Make the active IP-Adapter + DWPose experiment consume the canonical reference paths and role slots.
7. A/B tune appearance authority, pose authority, rendering authority and lineart authority.
8. Only after the core generation behavior is stable, proceed to targeted correction/postprocess.

---

## 18. Important implementation files

FREE engine:

```text
src/free_generation_plan.py
src/free_compiler.py
src/free_runtime.py
src/generation_bridge.py
src/comfyui_client.py
src/model_catalog.py
```

Current active diagnostic:

```text
src/free_ipadapter_pose_json_experiment.py
```

Capability tests:

```text
src/ipadapter_capability_test.py
src/pose_control_capability_test.py
```

Generation authority/profile data:

```text
shared/rendering/matte_dimensional_anime.json
shared/lineart/strong_anime_lineart.json
profiles/free_sdxl_v1.json
workflows/free_sdxl_conditioned_api.json
```

JSON lifecycle:

```text
src/json_parts.py
learning/local-ai/JSON_PARTS.md
learning/local-ai/store/staging/
learning/local-ai/store/json-parts/
```

Local AI / Oracle:

```text
src/local_ai_client.py
src/local_ai_tools.py
src/oracle_knowledge_store.py
config/local_ai.json
config/local_tools.json
infra/oracle/
```

---

## 19. Diagnostic commands worth preserving

IP-Adapter capability:

```powershell
cd C:\Dev\local-image-generator
.\tools\python312\python.exe .\src\ipadapter_capability_test.py
```

Pose capability:

```powershell
.\tools\python312\python.exe .\src\pose_control_capability_test.py
```

JSON Part read:

```powershell
.\tools\python312\python.exe .\src\json_part_read_test.py --ref part:<part_id>@<version>
```

Local stack:

```powershell
.\verify_local_stack.ps1
```

ComfyUI endpoint:

```text
http://127.0.0.1:8188
```

PowerShell execution-policy failures should normally be handled per invocation rather than changing the system policy globally:

```powershell
powershell -ExecutionPolicy Bypass -File .\<script>.ps1
```

---

## 20. Final anti-drift summary

The current project direction is **not** generic prompt engineering and **not** source-image img2img.

The intended FREE system is:

```text
MAIN IMAGE
  -> IP-Adapter appearance authority

POSE IMAGE
  -> DWPose / OpenPose ControlNet spatial authority

UP TO FIVE ROLE-BOUND JSON PARTS
  -> content/deltas

RENDERING AUTHORITY
  -> strongest persistent drawing-method definition
  -> matte + anime realism + depth + slight 3D-anime dimensionality

LINEART AUTHORITY
  -> independently strong/clear contours

FRESH LATENT
  -> redraw/generate the final image
```

Local AI creates reusable JSON in LEARN; FREE mechanically consumes accepted structured inputs. MEMORIELA remains a separate canon-aware planning domain.

Do not collapse these authorities back into one prompt, do not let one reference image silently own all responsibilities, and do not reintroduce Qwen into FREE.