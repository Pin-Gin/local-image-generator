# local-RAG — Consolidated Handoff

Last consolidated checkpoint: **2026-10-11 JST**

This is the **single authoritative continuation document** for a new ChatGPT session working on `Pin-Gin/local-image-generator`.

Read this file completely before changing architecture or implementation. Then inspect the current `main` branch before editing. Specialized documents remain useful references, but continuation status, current direction, verified/unverified boundaries, and next work are centralized here.

---

## 1. Status vocabulary

Use these labels exactly:

- **VERIFIED** — the user supplied successful local runtime evidence.
- **IMPLEMENTED / UNVERIFIED** — code exists in Git but the current path has not been confirmed locally.
- **NOT IMPLEMENTED** — no complete runtime path exists yet.
- **TARGET DESIGN** — the user has chosen the architecture, but code has not yet been fully changed to match it.
- **OPEN** — decision is intentionally not fixed yet.

Never promote an item to VERIFIED because code exists or because it looks correct in Git.

---

## 2. Working method that must not drift

New sessions must continue with the same method:

1. Read `START_HERE.md`, then this handoff.
2. Inspect current Git `main`; repository state overrides chat memory.
3. Keep changes incremental and narrowly scoped.
4. After each meaningful runtime change, give the user one concrete local verification command/path.
5. Only user-supplied local output promotes a runtime path to VERIFIED.
6. When a failure occurs, isolate the failing layer before changing unrelated components.
7. Prefer automated application/API workflows over manual ComfyUI node construction. Manual ComfyUI work is diagnostic only.
8. Do not silently reinterpret the user's objective or add generation assets the user did not request.
9. Do not silently rewrite manual JSON Part content.
10. Keep FREE and MEMORIELA semantic assets isolated.
11. Persistent writes require explicit user/application actions. AI chat text alone does not register/accept/train anything.
12. Do not expose or repeat local credentials/secrets.
13. If imported Python changes while `ui_server.py` is running, restart it before judging behavior.
14. Preserve lifecycle distinctions: analysis -> staging -> user acceptance -> accepted structured knowledge -> dataset/training/publish when applicable -> runtime use.
15. Project-created tools belong under `C:\Dev\local-image-generator`, except explicitly existing external runtimes such as the current ComfyUI portable installation.

The user runs and verifies Windows/GPU behavior locally; Git changes can be made remotely.

---

## 3. Product identity and source-of-truth boundaries

Desktop application/repository identity:

```text
local-RAG
repo: Pin-Gin/local-image-generator
local root: C:\Dev\local-image-generator
```

External canon/visual authority repository:

```text
MEMORIELA
repo: Pin-Gin/MEMORIELA
expected local clone: C:\Dev\MEMORIELA
```

`MEMORIELA` is not the generic app/build/storage name.

Current SQLite path from app config:

```text
database/local_rag.db
```

Older documentation/gate history may mention `database/memoriela_local.db`; treat that as historical evidence, not the current configured path.

Generated application outputs:

```text
C:\Dev\local-image-generator\outputs\
```

Direct ComfyUI `SaveImage` output is under the external ComfyUI runtime's `ComfyUI\output\` directory.

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

Current base checkpoint:

```text
ComfyUI\models\checkpoints\sd_xl_base_1.0.safetensors
```

### Rendering-training runtime — VERIFIED

```text
tools\python312
tools\sd-scripts
Python 3.12.10
PyTorch 2.8.0+cu128
CUDA: True
GPU: RTX 5080
```

### Project-local Ollama/Qwen — VERIFIED for LEARN

```text
runtime: tools\ollama\ollama.exe
API: http://127.0.0.1:11435
LEARN model: qwen3-vl:8b-instruct
```

Text inference and direct vision inference are VERIFIED. Vision analysis is evidence only and has previously overclaimed visual details.

`qwen2.5-coder:14b` remains the configured DEV role; installation/runtime has not been promoted to VERIFIED here.

---

## 5. Architecture decision made at this checkpoint

The user has chosen a new responsibility split. **This is the direction to implement next.**

The AI remains installed in the desktop application, but **FREE generation must be separated from conversational/local-AI interpretation and AI asset selection**.

High-level split:

```text
FREE
  -> deterministic generation path
  -> no Qwen prompt rewrite
  -> no Qwen pre-generation learned-asset selector
  -> exact user prompt / exact referenced JSON Parts drive generation

MEMORIELA
  -> local AI remains available
  -> AI interprets request / canon / controlled assets and builds a generation plan
  -> image execution should then use the common deterministic generation engine

LEARN
  -> local AI remains available
  -> analyzes images/text and can create JSON Part candidates
  -> user explicitly accepts the candidate
  -> accepted JSON Parts are later consumed mechanically by generation
```

Important: the current code has not yet been fully refactored to this split. `src/ui_server.py` still calls the generation-side AI selector for both `free` and `memoriela`, and `config/local_ai.json` still contains a `generate` role. Therefore the split above is **TARGET DESIGN**, not current runtime truth.

---

## 6. Target FREE generation pipeline

The user selected this target pipeline:

```text
Desktop application
  -> JSON Part read
  -> Checkpoint selection
  -> Character / Pose / content prompt
  -> Rendering Conditioning
  -> Rendering LoRA
  -> Lineart LoRA
  -> ControlNet / OpenPose
  -> first generation
  -> hand / face / body check
  -> required-region Inpaint
  -> Detailer
  -> Upscale
  -> final image
```

Principles:

- FREE must not ask Qwen to reinterpret, sanitize, summarize, select, or rewrite the requested generation content.
- Manual JSON Parts are mechanically resolved and compiled.
- Rendering and line-art should be independent concerns rather than relying on one huge positive prompt.
- Content/pose conditioning and rendering conditioning should be separable.
- Checkpoint choice is part of the generation engine and should become a desktop-app option/profile rather than requiring manual ComfyUI work.
- Actual output capability still depends on the selected checkpoint/LoRAs; bypassing Qwen does not guarantee that SDXL Base understands every requested concept.

Current implementation only covers part of this chain. ControlNet/OpenPose injection, automated body/hand/face correction, Inpaint orchestration, Detailer and Upscale orchestration are not production-complete.

---

## 7. Target MEMORIELA generation pipeline

MEMORIELA retains AI because its job is different from FREE.

Target:

```text
User request
  -> MEMORIELA AI
  -> read current canon/approved authority as needed
  -> resolve character / outfit / expression / pose / situation / background / camera
  -> structured GenerationPlan
  -> common deterministic generation engine
  -> ComfyUI
  -> image
```

AI is the **planner/interpreter**, not the uncontrolled final renderer.

Current named routing includes:

```text
YURA / ゆら / 久遠ゆら
KANAME / 要 / 水瀬要
SHIORI / 栞
YAMATO / 大和
MIO / 美緒
```

Only YURA currently has a connected MEMORIELA runtime profile. Unregistered characters must fail explicitly; never substitute YURA or silently fall back to FREE.

Known routing caution: `chat_contract.py` contains stricter detection for the single character `要`, but regression behavior such as `必要な背景を生成して` still requires explicit local evidence before calling it fixed.

---

## 8. Target LEARN workflow

Keep LEARN AI intact.

Target structured workflow:

```text
image / text / discussion
  -> qwen3-vl:8b-instruct analysis
  -> reusable JSON Part candidate
  -> staging
  -> explicit user acceptance
  -> accepted local JSON Part (+ Oracle for canonical app-managed parts)
  -> later FREE or MEMORIELA runtime use
```

The user has already observed Qwen produce adult-oriented/anatomy JSON during LEARN conversations, so do not assume that category is inherently blocked at the LEARN stage. However, content integrity must be checked at the saved/readback stage instead of assumed.

Do not equate JSON knowledge with model-weight learning. Persistent LoRA/adapter dataset registration -> training -> validation -> publishing is a separate lifecycle and is not end-to-end production complete.

The explicit `Part採用` UI behavior is IMPLEMENTED / UNVERIFIED. A LEARN smoke test previously produced only a natural-language response saying approval was needed rather than a JSON candidate/button, so do not claim that UI path is verified yet.

---

## 9. JSON Parts — current implementation and verified evidence

Canonical ref syntax:

```text
part:<part_id>@<version>
```

File naming:

```text
<part_id>.v<version>.json
```

Accepted local store:

```text
learning/local-ai/store/json-parts/
```

Staging store:

```text
learning/local-ai/store/staging/
```

Generation example:

```json
{
  "positive": "anime woman, full body",
  "parts": [
    "part:anime_pose_hair_touch@1"
  ]
}
```

### Manual structured JSON compatibility — VERIFIED

`src/json_parts.py` supports manually authored structured JSON directly in the accepted `json-parts` directory in addition to canonical `local-rag/json-part` documents.

Current behavior:

- canonical identity/version comes from the ref/filename;
- optional `file_name` must match the canonical filename;
- UTF-8 BOM is accepted;
- a whole-file Markdown JSON fence (```json ... ```) is accepted;
- the manual source file is not rewritten;
- `description` is metadata/name and is not injected into the prompt;
- hierarchy is preserved at generation conversion time as dotted paths;
- scalar values, order and duplicate leaves are retained;
- top-level `positive` can explicitly override automatic linearization;
- `negative` / `negative_prompt` is supported;
- manual compatibility files are local-file generation assets and are not automatically mirrored into Oracle.

Relevant fixes:

```text
23ce5e8e21baa05af2491b4bf1b00ad4c4f3d920
  Accept fenced and BOM-prefixed manual JSON part files

14060065cd4281a1b842dc2c0b66ab6576d64a76
  Preserve manual JSON hierarchy in generation prompt
```

### User-verified manual Part read

`part:anime_pose_hair_touch@1` produced:

```text
[JSON-PART:READ:OK]
```

and resolved a noncanonical manually authored JSON file.

`part:nude_bust_anatomy_detail@1` also produced:

```text
[JSON-PART:READ:OK] ref=part:nude_bust_anatomy_detail@1
part_type=pose
```

with the hierarchy preserved in the positive output, for example:

```text
pose.body.state: nude
pose.body.anatomy.torso: fully exposed
pose.hands.left_hand: covering the left breast
pose.rendering: anime style with detailed shading and highlights
```

Therefore **manual structured JSON -> loader -> dotted-path internal positive/negative conversion is VERIFIED**.

Verification command:

```powershell
.\tools\python312\python.exe .\src\json_part_read_test.py --ref part:<part_id>@<version>
```

Do not infer from a successful read test that every downstream generation stage has been verified for that Part.

---

## 10. Direct ComfyUI diagnostic performed in this session

The user manually assembled a minimal SDXL text2img workflow in ComfyUI to remove local-RAG/Qwen from the path:

```text
CheckpointLoaderSimple
  -> CLIP Text Encode positive
  -> CLIP Text Encode negative
  -> KSampler
  -> VAE Decode
  -> Save Image
```

Settings were aligned to the current FREE baseline:

```text
checkpoint: sd_xl_base_1.0.safetensors
1024 x 1024
steps: 20
cfg: 6.5
sampler: euler
scheduler: normal
denoise: 1.0
```

The JSON-derived prompt was pasted directly into the positive CLIP encoder.

### Result — VERIFIED observation

The user reported that direct ComfyUI generation **did generate an image**, but the requested effect was weak.

Interpretation boundary:

- Qwen/local-RAG is not required for the weak result to appear;
- therefore SDXL Base / prompt semantics / checkpoint training distribution are part of the current bottleneck;
- this does **not** prove that local-RAG's downstream prompt transport is perfect; it only proves that the direct base-model test also has limited strength.

### Rendering-conditioning experiment

A second positive CLIP encoder plus `Conditioning Combine` was manually wired so content/pose and rendering can be separated:

```text
Content / JSON CLIP -----\
                          -> Conditioning Combine -> KSampler positive
Rendering-only CLIP ----/
Negative CLIP -------------------------------------> KSampler negative
```

The wiring was constructed interactively, but do not treat the final quality effect of this split as formally VERIFIED yet.

The user specifically wants stronger anime line work in addition to dimensional rendering.

---

## 11. Rendering / line-art direction

Shared rendering identity remains:

```text
Matte Dimensional Anime
```

Rendering LoRA training — VERIFIED:

```text
20 images
5 epochs
2000 steps
avr_loss=0.142
[LEARNING:TRAIN:OK]
```

A generated FREE sample with the trained LoRA was previously evaluated as:

```text
rendering / dimensionality: PASS
anime retention: PASS
depth: PASS
hand/finger anatomy: FAIL
```

Responsibility remains separated:

```text
Rendering LoRA -> style / dimensionality / matte shading
Lineart LoRA or line conditioning -> main-line strength / contour character
Pose/Control -> body / arms / hands / fingers / posture
Character asset -> identity
Outfit asset -> clothing identity
```

Important current config detail: `shared/rendering/matte_dimensional_anime.json` describes line weight as medium-fine and subordinate to form. This is consistent with the user's observation that the current line work is weak for the desired output. Do not solve line strength by blindly increasing CFG; line-art should become its own controllable concern.

Rendering LoRA is currently configured in the shared JSON but `lora.enabled` is false in Git at this checkpoint; local weights exist separately and are not committed.

---

## 12. Checkpoint direction

Current FREE profile still uses:

```text
sd_xl_base_1.0.safetensors
```

The direct ComfyUI test showed that SDXL Base can generate from the JSON-derived prompt but is weak for the desired content/style strength.

A checkpoint replacement/comparison is therefore a legitimate next diagnostic, especially with anime-specialized checkpoints. Do not hard-code a new model as production authority before the user installs and locally compares it.

Checkpoint selection should ultimately be exposed through the desktop generation plan/UI rather than requiring manual ComfyUI editing.

---

## 13. Current code mismatch with the new FREE target

This is the first implementation problem to solve next.

Current `src/ui_server.py` does:

```text
build_generation_request
  -> _attach_learned_asset_selection
  -> select_assets_with_local_ai(qwen role=generate)
```

for both FREE and MEMORIELA.

Current `src/generation_bridge.py` also consumes `request.learning` and resolves AI-selected registry assets.

Current `learning/registry/registry.json` contains only the shared rendering inventory asset with `selection_mode: always`; there are no production `selection_mode: ai` pose/hand/etc. assets.

### New required behavior

FREE:

```text
build_generation_request
  -> exact JSON Part resolution / deterministic options
  -> GenerationPlan
  -> compiler
  -> ComfyUI
```

No generation-role Qwen call is allowed on the FREE path.

MEMORIELA may retain AI planning/selection, but its outputs must be validated against registered/canonical assets before deterministic execution.

Do not delete the local AI subsystem. The change is a routing/responsibility change, not removal of AI from the application.

---

## 14. Oracle / local tools — verified stable foundation

Oracle Free:

```text
container: local-rag-oracle
listener: 127.0.0.1:1521
service: FREEPDB1
schema: LOCALRAG_KB1
tablespace: LOCALRAG_DATA
```

Schema tables:

```text
LR_SCHEMA_META
LR_KNOWLEDGE_ITEM
LR_JSON_PART
LR_SOURCE_REF
LR_TOOL_AUDIT
```

Verified end-to-end path:

```text
Qwen LEARN
  -> json_part_get
  -> LocalAIToolbox
  -> Oracle LR_JSON_PART
  -> tool result
  -> Qwen final answer
```

Important VERIFIED hardening completed after the older handoff was written:

### Test residue cleanup — VERIFIED

```text
[TEST-CLEANUP:ORACLE] deleted=True reason=deleted
[TEST-CLEANUP:FILE] deleted=True
[TEST-CLEANUP:OK]
```

### Oracle app-password rotation — VERIFIED

The safe `rotate-app-password` action was run successfully and Python health remained online afterward. Never reproduce any old exposed credential in chat/docs.

### One-command integration stack — VERIFIED

Command:

```powershell
.\verify_local_stack.ps1
```

User-verified successful stages included:

```text
[INTEGRATION:ORACLE:OK]
[INTEGRATION:UPSERT:OK]
[INTEGRATION:READBACK:OK]
[INTEGRATION:GIT-READ:OK]
[INTEGRATION:TOOLBOX:OK]
[INTEGRATION:LOCAL-AI-TOOL:OK]
[LOCAL-STACK:INTEGRATION:OK]
[INTEGRATION:CLEANUP:OK]
[VERIFY:LOCAL-STACK:OK]
```

Therefore the repeatable Oracle/Git-read/LocalAIToolbox/Qwen tool stack is VERIFIED.

Git local-tool permissions remain read-only. Do not broaden them casually.

---

## 15. Current verified / unverified matrix

### VERIFIED

- ComfyUI local runtime/API and RTX 5080 environment.
- Existing local-RAG base generation gates through prior G0-G5 work.
- Matte Dimensional Anime LoRA training completion.
- Rendering LoRA actual FREE-generation path after Windows name normalization fix.
- Project-local Ollama LEARN text and vision inference.
- Oracle schema connectivity.
- Canonical staging JSON Part write/read through Oracle.
- `LocalAIToolbox -> Oracle` exact Part lookup.
- `Qwen -> json_part_get -> Oracle -> Qwen` tool loop.
- Narrow test-Part cleanup.
- Oracle application credential rotation.
- `verify_local_stack.ps1` disposable integration flow.
- Manual structured JSON read compatibility.
- Markdown-fenced/BOM manual JSON parsing.
- Manual JSON hierarchy-preserving dotted-path conversion for `nude_bust_anatomy_detail`.
- Direct ComfyUI SDXL Base generation from the JSON-derived prompt succeeded, though quality/effect was weak.

### IMPLEMENTED / UNVERIFIED or superseded by new design

- Pre-generation Qwen learned-asset selection for generation: code exists, but FREE use is now superseded by the new target design and should be removed/bypassed there.
- Multiple learned LoRA compiler chain: code exists; production asset compatibility not fully locally verified.
- Explicit UI `Part採用` interaction.
- Some latest pywebview LEARN UI paths.
- DEV model/runtime.
- Generation-time exact JSON Part merge through the full desktop -> compiler -> ComfyUI path after the latest manual JSON hierarchy changes; only the loader conversion is verified.
- Separate content conditioning + rendering conditioning in the automated compiler.

### NOT IMPLEMENTED end-to-end

- FREE fully deterministic no-Qwen route.
- Desktop checkpoint selection.
- Automated separated Rendering Conditioning.
- Dedicated Lineart LoRA/line-strength control path.
- ControlNet/OpenPose/DWPose runtime injection.
- Automated body/hand/face validation and targeted Inpaint.
- Detailer orchestration.
- Upscale orchestration.
- Full persistent dataset -> train -> validate -> publish -> registry activation lifecycle for learned non-rendering assets.

---

## 16. Exact next implementation order

Do not restart the project from first principles. Continue from this order unless the user explicitly changes priority.

### Step A — FREE AI bypass

Refactor generation request handling so:

```text
FREE -> no `select_assets_with_local_ai`
MEMORIELA -> AI planning may remain
```

Preserve the local AI subsystem for MEMORIELA/LEARN/DEV.

Add a focused test proving that a FREE request can be built without an Ollama call and still carries exact referenced JSON Parts.

### Step B — deterministic FREE GenerationPlan

Separate generation-plan concerns explicitly:

```text
content / character / pose
rendering conditioning
rendering LoRA
lineart conditioning / LoRA
checkpoint
negative conditioning
pose control
postprocess stages
```

Do not flatten all responsibilities into a single undifferentiated prompt if separate compiler channels are available.

### Step C — content + rendering conditioning compiler

Automate the manual ComfyUI experiment:

```text
Content CLIP + Rendering CLIP -> ConditioningCombine -> sampler positive
```

Keep negative conditioning separate.

### Step D — checkpoint selector + lineart control

Add configurable checkpoint choice and a dedicated line-art strength mechanism. Do not use CFG as a substitute for line-art control.

### Step E — pose/anatomy control

Add ControlNet/OpenPose/DWPose in a controlled way and verify one stage at a time.

### Step F — postprocessing pipeline

Add in this order:

```text
targeted Inpaint
Detailer
Upscale
```

Do not build all postprocessing stages at once without isolated tests.

### Step G — MEMORIELA AI planner on the common engine

Once the common deterministic engine is stable, keep MEMORIELA AI at the planning/canon-resolution layer and execute the resolved plan through the same engine.

### Step H — LEARN integrity improvements

Keep JSON candidate generation + explicit acceptance. Add source/candidate/readback comparison/diff if needed so the user can confirm that accepted JSON was not weakened or changed during conversion/persistence.

---

## 17. Important files to inspect before implementation

Generation path:

```text
src/ui_server.py
src/chat_contract.py
src/generation_bridge.py
src/compiler.py
workflows/sdxl_text2img_api.json
profiles/free_sdxl_v1.json
shared/rendering/matte_dimensional_anime.json
```

JSON Parts:

```text
src/json_parts.py
src/json_part_read_test.py
learning/local-ai/JSON_PARTS.md
learning/local-ai/store/json-parts/
learning/local-ai/store/staging/
```

Local AI:

```text
config/local_ai.json
config/local_tools.json
src/local_ai_client.py
src/local_ai_tools.py
docs/local-ai/
```

Oracle/integration:

```text
src/oracle_knowledge_store.py
src/local_stack_integration_test.py
src/cleanup_test_json_part.py
verify_local_stack.ps1
oracle_local.ps1
infra/oracle/
```

MEMORIELA authority:

```text
C:\Dev\MEMORIELA
external authority: Pin-Gin/MEMORIELA
```

---

## 18. Diagnostic commands worth preserving

Manual JSON Part read:

```powershell
cd C:\Dev\local-image-generator
.\tools\python312\python.exe .\src\json_part_read_test.py --ref part:anime_pose_hair_touch@1
```

Local stack integration:

```powershell
.\verify_local_stack.ps1
```

Oracle status:

```powershell
powershell -ExecutionPolicy Bypass -File .\oracle_local.ps1 -Action status
```

Local AI status:

```powershell
powershell -ExecutionPolicy Bypass -File .\local_ai.ps1 -Action status
```

ComfyUI connectivity is expected at:

```text
http://127.0.0.1:8188
```

---

## 19. Anti-drift rules for future chats

Do not:

- reintroduce Qwen into FREE merely because a `generate` role already exists;
- claim the new FREE split is implemented before changing/testing code;
- auto-select manual JSON Parts from the directory unless the user explicitly chooses that behavior later;
- treat canonical Oracle Parts and local-only manual compatibility files as identical persistence mechanisms;
- silently change user-authored JSON content;
- conflate stronger rendering with stronger line art;
- conflate pose/anatomy control with rendering style;
- assume a new checkpoint is better before local A/B testing;
- treat manual ComfyUI node work as the production UX;
- expose Oracle credentials;
- claim adult/anatomy output capability solely because a JSON Part contains those keys; actual rendering depends on checkpoint/runtime assets;
- mix MEMORIELA identity assets into FREE.

The intended end state is a desktop application where the user does not need to construct ComfyUI nodes manually.

---

## 20. Reference documents

This handoff is the continuation source of truth. Specialized documents are references only:

```text
START_HERE.md
SPEC.md
GATE.md
learning/local-ai/JSON_PARTS.md
docs/local-ai/README.md
docs/local-ai/LOCAL_TOOLS_AND_ORACLE.md
docs/local-ai/GENERATION_ASSISTANT.md
learning/rendering/README.md
```

If a specialized document conflicts with the architecture decision in this handoff, update that document rather than reverting the handoff direction without user approval.
