# MEMORIELA Local Image Generator — Production Specification

Status: **INITIAL / ACTIVE FOR FOUNDATION PHASE**

## 1. Product objective

Build a local Windows desktop image-generation application for MEMORIELA, with the final deliverable launched from an `.exe`.

The application must use local GPU generation and must not require a cloud image-generation API for normal operation.

## 2. Initial production architecture

```text
Desktop UI
  -> Local Backend / Controller
  -> Intent / Generation Request
  -> SQLite + JSON metadata
  -> Generation Compiler
  -> ComfyUI API
  -> Local model/runtime
  -> Generated image
  -> Manifest / history / QA record
```

## 3. Current backend baseline

Initial backend target:

- Windows 11
- NVIDIA RTX 5080 16 GB
- ComfyUI as generation backend
- local HTTP API communication with ComfyUI
- Python for the initial controller/backend layer
- SQLite for local metadata/history
- JSON for machine-readable generation profiles and manifests

Frontend and final desktop shell are intentionally deferred until the generation core is stable.

## 4. Source-of-truth separation

### This repository

Owns executable application logic and local-generation infrastructure.

### MEMORIELA repository

Owns canon, visual authority, approved MASTER assets, and related source documents.

The generator must not silently rewrite MEMORIELA canon.

## 5. Generation authority model

Target production execution is based on an explicit bundle such as:

```text
MASTER IMAGE
+ approved visual/source documents
+ machine-readable generation profile JSON
+ workflow definition
+ model/runtime version information
```

Every generation should be reproducible enough to identify which authority inputs and runtime settings were used.

## 6. Manifest requirements

A production generation manifest should be able to record at least:

- generation timestamp
- generation request/profile identifier
- source repository and source revision/hash where applicable
- MASTER image path/identifier and file hash
- source document paths and hashes
- generation profile version/hash
- workflow version/hash
- model/checkpoint identifier/hash where practical
- seed
- sampler/scheduler/steps/CFG/denoise and other effective parameters
- generated output path(s)
- generation result/status
- later QA/adoption status

The exact schema will be fixed when the database/profile layer is implemented.

## 7. Runtime data policy

`cache/`, `outputs/`, and `logs/` are runtime-oriented locations. Large generated artifacts, model weights, and transient cache data should not be committed to Git by default.

Model files are external runtime dependencies and are not intended to be stored in this repository.

## 8. Character identity direction

The production system must support stronger identity stability than the initial SDXL img2img prototype.

Identity stabilization is a dedicated implementation phase. Candidate mechanisms may be evaluated later, but no specific reference adapter, LoRA, or custom-node solution is production authority yet.

## 9. Development sequence

Initial sequence:

1. repository foundation
2. local core/bootstrap
3. ComfyUI connectivity
4. configuration/profile loading
5. generation compiler
6. manifest/output handling
7. SQLite history/index layer
8. identity-stability implementation and testing
9. chat-style UI
10. Windows desktop packaging / `.exe`

## 10. Non-goals for the foundation phase

The foundation phase does not claim:

- final image quality
- final identity stability
- final UI design
- final model selection
- final packaging technology
- final LoRA/reference implementation

Those decisions must be promoted through explicit gates after local verification.
