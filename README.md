# local-RAG

Local Windows image-generation application.

## Generation domains

### FREE

Deterministic generic generation. FREE does not use conversational/local AI to reinterpret the request.

Current target authority split:

```text
main reference image -> IP-Adapter -> appearance
pose reference image -> DWPose/OpenPose -> pose
up to five role-bound JSON Parts -> content/deltas
Rendering Authority -> drawing/rendering method
Lineart Authority -> contour strength/clarity
fresh latent -> final redraw/generation
```

### MEMORIELA

Canon-aware named-character production. Local AI may plan/resolve canon, then the validated plan executes through the deterministic generation engine.

### LEARN

Local AI analyzes text/images and creates reusable JSON candidates. Persistent reuse requires staging/acceptance rather than chat text alone.

## Start here

```text
START_HERE.md
docs/handoff/LOCAL_RAG_HANDOFF.md
docs/architecture/REPOSITORY_LAYOUT.md
```

## Current reference-image roots

```text
references/free/main/
references/free/pose/
```

Actual user reference images are local runtime assets and are ignored by Git by default.

Shared drawing authorities live under:

```text
shared/rendering/
shared/lineart/
```
