# local-RAG — Production Gates

Status: **ACTIVE / G0–G5 HISTORICALLY VERIFIED / CURRENT ARCHITECTURE EVOLVING**

Current continuation source:

```text
docs/handoff/LOCAL_RAG_HANDOFF.md
```

The G0–G5 entries below are preserved as historical verification evidence. Some names/paths recorded in those runs predate the current `local-RAG` cleanup. In particular, the G5 run used `database/memoriela_local.db`; the **current configured database path is `database/local_rag.db`**. Do not reinterpret historical verification metadata as current configuration.

The newer FREE-deterministic / MEMORIELA-AI-planned architecture is documented in `SPEC.md` and the consolidated handoff. Existing gate PASS evidence is not automatic verification of newly refactored paths.

## Gate principle

A feature is not promoted to production-ready status because code exists. It must be executed in the target local environment and verified against the gate for that phase.

No failed result is silently relabeled as PASS.

## G0 — Repository Foundation

**Status: PASS**

PASS requires:

- `START_HERE.md` exists
- `SPEC.md` exists
- `GATE.md` exists
- required production directories exist in Git
- repository can be read and written through the connected GitHub integration

This gate does not prove local runtime execution.

## G1 — Local Core Bootstrap

**Status: PASS — locally verified**

PASS requires local execution proving:

- application/core entry point starts
- configuration can be loaded
- required paths can be resolved
- logs can be written locally
- fatal startup errors are reported clearly

## G2 — ComfyUI Connectivity

**Status: PASS — locally verified**

PASS requires local execution proving:

- configured ComfyUI endpoint is reachable
- system/status endpoint can be read
- a standard workflow can be submitted
- generation history can be polled
- output image can be retrieved

## G3 — Authority / Profile Compilation

**Status: PASS — locally verified for the recorded historical path**

PASS requires:

- generation request loads an explicit generation profile
- configured MEMORIELA authority sources are resolved
- source revision/hash information is captured
- MASTER/source file hashes are captured where applicable
- effective ComfyUI workflow is compiled deterministically from the selected inputs

Fetching source documents without affecting or validating the compiled generation request is not sufficient for this gate.

Verified G3 authority state:

- repository: `Pin-Gin/MEMORIELA`
- branch: `main`
- authority commit: `da167885779897d6b643d19218183e035bdbcfd5`
- working Master SHA-256: `81ac67b8395d5e3b49abcd75db77d420aa9cab94bcff4b582eaaed13bfeaf94d`
- compiled workflow SHA-256: `c879a1e46f62c3be987def3cb227dd24c968ddded1501685bacb6d9da41f6cdc`

This G3 PASS verifies the recorded working-Master compilation path only. It does not promote YURA to final Production Authority and does not override the authority lifecycle recorded in MEMORIELA.

## G4 — Manifest and Output Integrity

**Status: PASS — locally verified for the recorded historical path**

PASS requires:

- generated image is stored in the intended output structure
- manifest is created for the generation
- manifest records effective parameters and source identifiers
- output and manifest can be associated unambiguously

Verified G4 run:

- generation id: `20261011T004449955189Z`
- ComfyUI prompt id: `d6088d86-1520-4f0f-86cc-a6eaef9aaead`
- output SHA-256: `e78d3f41078fa572d1e179bc35d546bbf9a5201996c155d95d20dc9ea17f9f26`
- manifest SHA-256: `2b6888063b9f4685124b7847402aada46275aa653dfae4fd05a98cbc3a87043c`
- authority commit: `da167885779897d6b643d19218183e035bdbcfd5`
- profile SHA-256: `c224477d71e6535ec263b62c90c557fd9a2b9deb4dfe36d1dde6f542616f8636`
- compiled workflow SHA-256: `c879a1e46f62c3be987def3cb227dd24c968ddded1501685bacb6d9da41f6cdc`

The generated image and its `manifest.json` were stored under the same generation-specific output directory, establishing an unambiguous one-to-one association for this run.

## G5 — SQLite History / Lookup

**Status: PASS — locally verified for the recorded historical path**

PASS requires:

- database initializes from a clean state
- generation metadata can be inserted
- generation/history can be queried
- accepted/rejected status can be stored without modifying source canon

Verified G5 run:

- historical database used: `database/memoriela_local.db`
- current configured database: `database/local_rag.db`
- generation id: `20261011T004449955189Z`
- manifest SHA-256: `2b6888063b9f4685124b7847402aada46275aa653dfae4fd05a98cbc3a87043c`
- output SHA-256: `e78d3f41078fa572d1e179bc35d546bbf9a5201996c155d95d20dc9ea17f9f26`
- initial QA status: `unreviewed`
- accepted status write: PASS
- rejected status write: PASS
- restore to `unreviewed`: PASS
- history lookup: PASS

The G5 verification modified only local SQLite history state and did not write back to MEMORIELA canon.

A future refactor that materially changes the current history path should receive its own focused verification instead of inheriting this PASS blindly.

## G6 — Identity Stability

**Status: DEFERRED BY AUTHOR DECISION**

Current output similarity was sufficient for that stage. Stronger face/touch/identity constraints remain deferred until explicitly resumed.

This gate is not marked PASS.

## G7 — Desktop UI / Generation Integration

**Status: IN PROGRESS / ARCHITECTURE CHANGED SINCE INITIAL SLICE**

The original G7 slice established UI/chat/request foundations. The current target now additionally requires:

```text
FREE
  -> deterministic generation without Qwen pre-generation selection

MEMORIELA
  -> AI planning allowed, validated structured plan

LEARN
  -> AI analysis / JSON Part candidates with explicit acceptance
```

PASS for the current architecture requires the desktop UI to invoke the production generation core without bypassing the current domain/manifest rules and without reintroducing mandatory Qwen processing into FREE.

## G8 — Desktop Packaging

PASS requires:

- Windows application launches from the packaged desktop build;
- required backend processes are started or connected correctly;
- generation can be initiated from the desktop application;
- result can be viewed/retrieved from the application;
- packaging does not require manual source-code execution for normal use.

## Current gate summary

- G0 Repository Foundation: PASS
- G1 Local Core Bootstrap: PASS
- G2 ComfyUI Connectivity: PASS
- G3 Authority / Profile Compilation: PASS for recorded path
- G4 Manifest and Output Integrity: PASS for recorded path
- G5 SQLite History / Lookup: PASS for recorded path
- G6 Identity Stability: DEFERRED
- G7 Desktop UI / Generation Integration: IN PROGRESS under new architecture
- G8 Desktop Packaging: pending full current-architecture verification
