# FREE generation domain

FREE is the deterministic generic generation domain.

It must not use conversational/local AI to reinterpret, sanitize, summarize, select or rewrite generation content.

## Authority split

```text
main reference image
  -> IP-Adapter
  -> appearance authority

pose reference image
  -> DWPose / OpenPose ControlNet
  -> pose/spatial authority

up to five role-bound JSON Parts
  -> content/deltas

shared/rendering/
  -> Rendering Authority

shared/lineart/
  -> Lineart Authority

fresh latent
  -> final redraw/generation
```

## Five content slots

```text
1. CHARACTER / BODY
2. OUTFIT / PROP
3. EXPRESSION / FACE
4. CAMERA / COMPOSITION
5. BACKGROUND / SCENE
```

Rendering and lineart are separate authorities and do not consume one of these five slots.

## Boundaries

- Do not inject MEMORIELA character MASTERs, outfits, character LoRAs, backgrounds or canon authority into FREE.
- Do not use the main reference image as the KSampler img2img starting latent in the target architecture.
- Do not auto-select arbitrary JSON Parts from storage.
- Exact accepted Part refs are mechanically resolved.
- Contradictory inputs are not silently reconciled by AI.

Canonical local reference directories:

```text
references/free/main/
references/free/pose/
```

Machine-readable target input contract:

```text
schemas/free_generation_input.schema.json
```
