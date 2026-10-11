# Generation-side Local AI Boundary

Status: **TARGET SPLIT DECIDED / CURRENT CODE STILL NEEDS FREE BYPASS REFACTOR**

For the authoritative continuation state, read:

```text
docs/handoff/LOCAL_RAG_HANDOFF.md
```

## 1. Current architecture decision

The local AI subsystem remains part of the desktop application, but it must no longer be treated as a mandatory pre-generation layer for every generation request.

Target responsibility split:

```text
FREE
  -> no Qwen prompt rewrite
  -> no Qwen pre-generation learned-asset selection
  -> deterministic prompt / JSON Part / configured generation controls

MEMORIELA
  -> local AI remains for request/canon/asset interpretation
  -> AI produces or assists a controlled GenerationPlan
  -> resolved plan executes through the common deterministic generation engine

LEARN
  -> local AI remains for analysis and JSON Part candidate generation
  -> explicit user acceptance before persistence/reuse
```

The AI is not being removed from local-RAG. The change is specifically that **FREE image generation is separated from conversational/local-AI interpretation**.

## 2. Current code versus target

Current `src/ui_server.py` still performs:

```text
build_generation_request
  -> _attach_learned_asset_selection
  -> select_assets_with_local_ai
```

for both FREE and MEMORIELA.

That behavior is now legacy for FREE and must be bypassed/refactored.

Current registry:

```text
learning/registry/registry.json
```

contains the shared Matte Dimensional Anime rendering asset as `selection_mode: always`, but no production `selection_mode: ai` pose/hand/outfit/character/background asset.

The previous AI-selector implementation remains useful engineering history and may still be reused on the MEMORIELA side where controlled AI planning is appropriate. It must not be reintroduced into FREE merely because the code already exists.

## 3. Target FREE flow

```text
Desktop UI
  -> parse exact user text/JSON
  -> resolve explicitly referenced JSON Parts
  -> deterministic GenerationPlan
       checkpoint
       content / character / pose
       rendering conditioning
       rendering LoRA
       lineart conditioning / LoRA
       negative conditioning
       pose control
       postprocess configuration
  -> compiler
  -> ComfyUI
  -> image
```

Later pipeline stages are planned:

```text
ControlNet / OpenPose
first generation
hand / face / body check
targeted Inpaint
Detailer
Upscale
```

These later stages are not yet production-complete.

## 4. Target MEMORIELA AI flow

```text
User request
  -> local AI / controlled tools
  -> MEMORIELA canon / approved authority lookup as needed
  -> resolve registered character/outfit/expression/pose/background/camera assets
  -> validated structured GenerationPlan
  -> common deterministic generation engine
```

AI must not invent assets, silently substitute characters, or bypass authority validation.

Only YURA currently has a connected runtime character profile. Other routed MEMORIELA characters must fail explicitly until their runtime profiles exist.

## 5. Post-generation AI

Post-generation image discussion/analysis can remain available as an optional assistant feature. It is separate from the deterministic FREE generation execution path.

Vision output remains advisory evidence, not ground truth.

## 6. Historical learned-asset selector

The existing selector implementation can:

- ask the local `generate` role to return exact registry asset IDs;
- reject unknown/ineligible IDs;
- resolve prompt/LoRA assets;
- record selected IDs into request/plan/manifest metadata;
- chain learned LoRAs after shared rendering in the compiler.

This code is **not the target FREE design anymore**.

`src/learning_generation_test.py` remains useful for testing the old selector/LoRA-chain mechanics in isolation, but a passing result does not mean FREE should continue to call Qwen.

## 7. Next implementation requirement

The first generation-side change after this documentation checkpoint is:

```text
FREE request
  -> build_generation_request
  -> exact JSON Part resolution
  -> deterministic GenerationPlan
  -> no LocalAIClient/Qwen call
```

while:

```text
MEMORIELA request
  -> controlled AI planning may remain
```

Add a focused test that proves FREE request construction/generation planning works even when Ollama is unavailable or not called.

Do not mark this split VERIFIED until the user runs the resulting local test.
