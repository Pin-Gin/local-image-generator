# local-RAG — Production Specification

Status: **ACTIVE / FREE-DETERMINISTIC + MEMORIELA-AI-PLANNED TARGET ARCHITECTURE**

For current verified/unverified state and exact continuation order, read:

```text
docs/handoff/LOCAL_RAG_HANDOFF.md
```

## 1. Product objective

Build a local Windows desktop image-generation application launched as `local-RAG.exe` and backed by local ComfyUI generation.

The application has two generation domains plus a LEARN assistant workflow:

- **FREE**: deterministic natural-language / JSON / JSON-Part driven generation without MEMORIELA-specific assets and without mandatory Qwen pre-generation interpretation.
- **MEMORIELA**: controlled named-character production where local AI may interpret the request/canon/assets and produce a validated structured generation plan.
- **LEARN**: local AI analysis and reusable JSON Part candidate creation, with explicit user acceptance before persistent reuse.

The local AI subsystem remains part of the application. The architectural change is that FREE execution does not depend on the conversational/local-AI selector.

## 2. Target generation architecture

```text
Desktop UI
  -> Local Backend / Controller
  -> Domain Router
       -> FREE
            exact text/JSON
            explicit JSON Parts
            deterministic options
            NO mandatory Qwen pre-generation call
       -> MEMORIELA
            local-AI/canon planning as needed
            validated registered assets
  -> structured GenerationPlan
       checkpoint
       content / character / pose
       rendering conditioning
       rendering LoRA
       lineart conditioning / LoRA
       negative conditioning
       pose control
       postprocess stages
  -> Generation Compiler
  -> ComfyUI API
  -> Local model/runtime
  -> Generated image
  -> optional Inpaint / Detailer / Upscale stages
  -> Manifest / SQLite history
```

The common generation engine should be deterministic from the resolved plan. Manual ComfyUI node construction is diagnostic/development work, not the intended production UX.

## 3. Domain rules

### FREE

FREE accepts natural language or JSON and should reproduce the specified content as directly as possible.

FREE must not inject:

- MEMORIELA MASTER images;
- MEMORIELA character LoRAs;
- MEMORIELA outfit assets;
- MEMORIELA situation/background assets;
- MEMORIELA-specific corrections;
- Qwen-generated prompt rewrites or Qwen pre-generation asset selections.

FREE may use:

- explicitly referenced reusable JSON Parts;
- a selected checkpoint;
- shared rendering conditioning / rendering LoRA;
- line-art conditioning / LoRA;
- pose-control assets;
- deterministic postprocessing stages.

Current base profile is `free-sdxl-v1`, but checkpoint selection is intended to become configurable rather than permanently fixed to SDXL Base.

### MEMORIELA

Natural-language references to the named cast route to MEMORIELA:

- YURA / ゆら / 久遠ゆら
- KANAME / 要 / 水瀬要
- SHIORI / 栞
- YAMATO / 大和
- MIO / 美緒

Only YURA currently has a connected runtime character profile. An unregistered MEMORIELA character must fail explicitly instead of falling back to FREE or another character.

MEMORIELA AI may interpret request/canon/registered assets, but its result must become a validated structured plan before execution. AI must not invent runtime assets or silently substitute identities.

MEMORIELA production assets remain modular: character identity, outfit, expression, pose, situation, background, camera and rendering are separate concerns.

## 4. LEARN rules

LEARN uses project-local `qwen3-vl:8b-instruct` for analysis and structured candidate creation.

Target lifecycle:

```text
analysis
  -> JSON Part candidate
  -> staging
  -> explicit user acceptance
  -> accepted reusable Part
  -> later generation use
```

Structured JSON persistence is not model-weight learning. Dataset registration/training/validation/publishing is a separate lifecycle.

Manual accepted JSON Parts are also supported as local generation-read assets.

## 5. Shared rendering and line art

Shared rendering is stored under `shared/rendering/`.

Current rendering identity:

```text
Matte Dimensional Anime
```

Target rendering qualities:

- stylized anime foundation;
- pronounced 3D-anime-like volume and spatial depth;
- matte surface response;
- restrained highlights;
- clear volumetric shading and modeled form planes;
- no photoreal human skin;
- no glossy/PBR CGI appearance.

Line-art strength is now a separate controllable concern. Do not treat stronger line art as equivalent to stronger rendering shading and do not use CFG as a substitute for a proper line-art control path.

Target positive-conditioning structure supports separate content and rendering conditioning, for example:

```text
Content/JSON CLIP -----\
                        -> Conditioning Combine -> sampler positive
Rendering CLIP --------/
```

A dedicated line-art LoRA/conditioning stage may be added separately.

## 6. Pose/anatomy and postprocessing

Pose/anatomy is separate from rendering style.

Target runtime layers may include:

```text
ControlNet / OpenPose / DWPose
  -> first generation
  -> hand / face / body check
  -> targeted Inpaint
  -> Detailer
  -> Upscale
```

These stages must be implemented and locally verified incrementally; they are not all production-complete at this specification checkpoint.

## 7. Rendering learning

Rendering learning lives under `learning/rendering/` and is independent from MEMORIELA asset learning.

Current implementation:

- SDXL LoRA;
- local `sd-scripts` trainer;
- captioned local dataset;
- trigger token `mdanime_style`;
- trained `.safetensors` copied to the configured ComfyUI `models/loras` directory;
- explicit configuration/activation.

A real Matte Dimensional Anime rendering LoRA training run has already been locally verified. Model weights remain local runtime assets and are not committed to Git.

## 8. JSON Part runtime

Reusable exact refs use:

```text
part:<part_id>@<version>
```

Accepted manual/canonical local files live under:

```text
learning/local-ai/store/json-parts/
```

Canonical Part persistence may also use Oracle. Manual compatibility files are local generation-read assets unless explicitly converted/registered.

See:

```text
learning/local-ai/JSON_PARTS.md
```

## 9. Source-of-truth separation

This repository owns the local application, generation routing, shared rendering, training/runtime plumbing and local metadata.

The external `Pin-Gin/MEMORIELA` repository owns MEMORIELA canon and approved character visual authority.

FREE generation must not read/inject MEMORIELA authority assets.

## 10. Manifest requirements

Generation manifests should record:

- generation timestamp and ID;
- generation domain;
- request / effective profile;
- exact JSON Part refs used;
- source authority where applicable;
- checkpoint;
- rendering ID/version;
- rendering/lineart LoRAs actually applied;
- pose-control assets actually applied;
- effective workflow/sampler settings;
- seed;
- postprocessing stages;
- output path/hash;
- later QA/adoption state.

## 11. Runtime data policy

`cache/`, `outputs/`, `logs/`, SQLite databases, learning datasets, training outputs and model weights are runtime/local data and should not be committed by default.

Current configured SQLite path:

```text
database/local_rag.db
```

## 12. Current high-level directory ownership

```text
src/                         application/controller/compiler code
ui/                          desktop UI
config/                      runtime config
domains/free/                FREE domain
domains/memoriela/           MEMORIELA domain
shared/rendering/            shared rendering definition
learning/rendering/          rendering LoRA training pipeline
learning/local-ai/           JSON Parts / local AI persistent store contracts
learning/registry/           learned runtime asset inventory
profiles/                    machine-readable runtime profiles
workflows/                   ComfyUI workflow templates
intent/                      input intent dictionaries
infra/oracle/                local Oracle schema/runtime
cache/ database/ outputs/    runtime state
docs/handoff/                single continuation handoff
```
