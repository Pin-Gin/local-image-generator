# local-RAG — Production Specification

Status: **ACTIVE / DESKTOP + DOMAIN SPLIT + RENDERING LEARNING IMPLEMENTATION**

## 1. Product objective

Build a local Windows desktop image-generation application launched as `local-RAG.exe` and backed by local ComfyUI generation.

The application has two generation domains:

- **FREE**: reproduce natural-language / JSON requests without MEMORIELA-specific assets.
- **MEMORIELA**: controlled named-character production using reusable character, outfit, situation, background, pose, expression, and camera assets.

Both domains use the same shared rendering layer.

## 2. Generation architecture

```text
Desktop UI
  -> Local Backend / Controller
  -> Intent / Generation Request
  -> Domain Router
       -> FREE
       -> MEMORIELA
  -> Shared Rendering
       -> Prompt rendering rules
       -> optional learned rendering LoRA
  -> Generation Compiler
  -> ComfyUI API
  -> Local model/runtime
  -> Generated image
  -> Manifest / SQLite history
```

## 3. Domain rules

### FREE

FREE accepts natural language or JSON and should reproduce the specified content as directly as possible.

FREE must not inject:
- MEMORIELA MASTER images
- MEMORIELA character LoRAs
- MEMORIELA outfit assets
- MEMORIELA situation/background assets
- MEMORIELA-specific corrections

FREE uses its own base profile (`free-sdxl-v1`) and the shared rendering layer only.

### MEMORIELA

Natural-language references to the named cast route to MEMORIELA:
- YURA / ゆら / 久遠ゆら
- KANAME / 要 / 水瀬要
- SHIORI / 栞
- YAMATO / 大和
- MIO / 美緒

Only YURA currently has a connected runtime character profile. An unregistered MEMORIELA character must fail explicitly instead of falling back to FREE or another character.

MEMORIELA production assets are modular. Outfit learning is intended to use outfit-only/mannequin datasets so clothing can be replaced without retraining character identity.

## 4. Shared rendering

Shared rendering is stored under `shared/rendering/` and is applied to both FREE and MEMORIELA.

Current rendering identity:

`Matte Dimensional Anime`

Target qualities:
- stylized anime foundation
- pronounced 3D-anime-like volume and spatial depth
- matte surface response
- restrained highlights
- clear volumetric shading and modeled form planes
- no photoreal human skin
- no glossy/PBR CGI appearance

Prompt-only rendering remains the fallback. When a learned rendering LoRA is trained and activated, the generation compiler injects the standard ComfyUI `LoraLoader` into both text2img and img2img workflows.

## 5. Rendering learning

Rendering learning lives under `learning/rendering/` and is independent from MEMORIELA asset learning.

Current implementation target:
- SDXL LoRA
- local `sd-scripts` trainer
- captioned local dataset
- trigger token `mdanime_style`
- U-Net-only LoRA training for reduced VRAM use
- trained `.safetensors` copied to the configured ComfyUI `models/loras` directory
- explicit activation updates the shared rendering configuration

Training data and model weights are local runtime assets and are not committed to Git.

A training implementation is not considered verified until a real dataset has been supplied and local training/publish/generation have completed successfully.

## 6. Source-of-truth separation

This repository owns the local application, generation routing, shared rendering, training pipeline, and runtime metadata.

The external MEMORIELA repository owns MEMORIELA canon and approved character visual authority. FREE generation must not read MEMORIELA authority.

## 7. Manifest requirements

Generation manifests should record:
- generation timestamp and ID
- generation domain
- request / effective profile
- source authority where applicable
- shared rendering ID/version
- whether rendering LoRA was enabled
- effective workflow/model/sampler settings
- seed
- output path/hash
- later QA/adoption state

## 8. Runtime data policy

`cache/`, `outputs/`, `logs/`, SQLite databases, learning datasets, training outputs, and model weights are runtime/local data and should not be committed by default.

## 9. Current high-level directory ownership

```text
src/                         application/controller/compiler code
ui/                          desktop UI
config/                      runtime config
domains/free/                FREE domain
domains/memoriela/           MEMORIELA domain
shared/rendering/            shared rendering definition
learning/rendering/          rendering LoRA training pipeline
profiles/                    machine-readable runtime profiles
workflows/                   ComfyUI workflow templates
intent/                      input intent dictionaries
cache/ database/ outputs/    runtime state
```
