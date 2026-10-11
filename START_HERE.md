# MEMORIELA Local Image Generator — START HERE

Status: **PRODUCTION ENVIRONMENT ROOT / INITIAL FOUNDATION**

This repository is the production development root for the MEMORIELA local image generation application.

## Final goal

A Windows desktop application distributed as an `.exe` that can generate MEMORIELA images locally.

Target high-level path:

```text
Desktop App (.exe)
  -> Local Controller / Backend
  -> Generation Compiler
  -> ComfyUI API
  -> NVIDIA RTX 5080
  -> Generated Image
```

## Current verified baseline

The following prototype capabilities were verified before this production repository was initialized:

1. ComfyUI can run locally on the RTX 5080.
2. Python can submit a workflow to the ComfyUI API and retrieve a generated image.
3. A generation run can combine a supplied MASTER image, generation JSON, and Git-backed source metadata.

These prototype results are evidence only. Prototype code is not automatically production authority.

## Production repository responsibilities

This repository owns the local generation application itself:

- application source code
- runtime configuration
- database schema and migrations
- generation profiles
- ComfyUI workflow definitions
- local cache layout
- output/manifest layout
- logging layout

MEMORIELA canon and visual authority remain outside this repository and must be read from the designated MEMORIELA Git source at runtime or sync time.

## Directory map

```text
src/        application source code
config/     runtime and environment configuration
database/   SQLite schema, migrations, and DB-related code/data definitions
profiles/   machine-readable generation profiles
workflows/  ComfyUI API workflow templates
cache/      local synchronized/read-through cache (runtime data)
outputs/    generated images and manifests (runtime data)
logs/       application/runtime logs (runtime data)
```

## Governing documents

- `SPEC.md` — current production scope and architecture
- `GATE.md` — promotion and acceptance gates
- `START_HERE.md` — repository entry point

## Development rule

Build in small verified increments. A capability is not marked production-ready until it has been executed locally and the acceptance gate for that step has passed.
