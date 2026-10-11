# Generation-side Local AI / Learned Asset Pipeline

Status: **IMPLEMENTED / LOCAL VERIFICATION REQUIRED**

The generation path now uses the project-local `qwen3-vl:8b-instruct` model **before** ComfyUI generation to decide whether any registered learned asset applies to the user's request.

## Current generation flow

```text
User input
  -> existing FREE / MEMORIELA routing
  -> local generation AI (qwen3-vl:8b-instruct)
  -> learning/registry/registry.json
  -> AI selects only registered, eligible asset IDs
  -> selection is validated against the registry
  -> generation plan applies selected learned prompts / LoRAs
  -> shared Rendering LoRA
  -> ComfyUI
  -> generated image
  -> optional generation-side visual QA/chat
```

The local AI is **not allowed to invent runtime assets or silently rewrite the user's generation request**. It returns selected asset IDs only. Unknown or ineligible IDs are rejected before generation.

## Learning registry

Mutable source:

```text
learning/registry/registry.json
```

The desktop build also bundles a fallback copy, but when the executable remains under the repository build tree the application prefers the repository copy so future published learning assets can be added without treating bundled data as the mutable source of truth.

Registry assets currently support these conditional runtime types:

```text
prompt
lora
```

`shared_rendering` is inventory-only / always-applied and is not an AI-selected conditional runtime.

### Current production registry state

At this checkpoint the registry records the already-trained Matte Dimensional Anime shared rendering asset as `selection_mode: always`.

There are currently **no production `selection_mode: ai` pose / hand / outfit / character / background assets yet**. Therefore the new selector is connected, but it should currently return an empty conditional selection for normal requests until a real learned asset is published into the registry.

## Learned LoRA composition

`src/compiler.py` now supports a LoRA chain:

```text
SDXL Base
  -> Shared Rendering LoRA (if active)
  -> AI-selected Learned LoRA #1
  -> AI-selected Learned LoRA #2
  -> ...
  -> CLIP conditioning / sampler
```

Duplicate learned asset IDs, duplicate learned LoRA files, and duplication of the shared rendering LoRA are rejected.

## Request / manifest traceability

The generation request now records:

```text
learning.registry_version
learning.selector
learning.selector_role
learning.selector_model
learning.selected_asset_ids
learning.reason
```

The generation plan records resolved learned assets and runtime types. The manifest records the learned assets actually applied to the generated image.

The desktop generation result metadata displays `learned_asset_ids` so it is visible whether a conditional learned asset was used.

## Generation-side visual assistant

The previously added generation-side AI chat remains available after image generation. It can inspect the generated image, compare it to the original request, and transfer the image into LEARN mode for further analysis.

This post-generation visual assistant is separate from the new **pre-generation learned-asset selector**.

## Important remaining boundary

The generation side can now **consume** registered learned assets, but LEARN mode still does not automatically perform the complete persistent lifecycle:

```text
accepted image
  -> dataset registration
  -> train
  -> validate
  -> publish asset
  -> add/update learning registry
```

That lifecycle remains the next major implementation step for hand / pose / outfit / character learning.

## Verification commands

After pulling the current branch, first run the local deterministic test:

```powershell
cd C:\Dev\local-image-generator
python .\src\learning_generation_test.py
```

Expected:

```text
[LEARNED-GENERATION:TEST:OK]
```

Then rebuild and run the desktop application:

```powershell
powershell -ExecutionPolicy Bypass -File .\build_desktop.ps1
.\dist\local-RAG\local-RAG.exe
```

With the current production registry, a normal generation should show:

```text
learned_asset_ids: []
```

while the shared rendering LoRA remains governed by the existing shared-rendering configuration.

Do not mark the pre-generation AI selector, multi-LoRA runtime chain, or desktop metadata as VERIFIED until the user runs these checks locally.
