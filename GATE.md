# MEMORIELA Local Image Generator — Production Gates

Status: **ACTIVE / G0–G5 VERIFIED**

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

**Status: PASS — locally verified**

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

This G3 PASS verifies the current working-Master compilation path only. It does not promote YURA to final Production Authority and does not override the authority lifecycle recorded in MEMORIELA.

## G4 — Manifest and Output Integrity

**Status: PASS — locally verified**

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

**Status: PASS — locally verified**

PASS requires:

- database initializes from a clean state
- generation metadata can be inserted
- generation/history can be queried
- accepted/rejected status can be stored without modifying source canon

Verified G5 run:

- database: `database/memoriela_local.db`
- generation id: `20261011T004449955189Z`
- manifest SHA-256: `2b6888063b9f4685124b7847402aada46275aa653dfae4fd05a98cbc3a87043c`
- output SHA-256: `e78d3f41078fa572d1e179bc35d546bbf9a5201996c155d95d20dc9ea17f9f26`
- initial QA status: `unreviewed`
- accepted status write: PASS
- rejected status write: PASS
- restore to `unreviewed`: PASS
- history lookup: PASS

The G5 verification modified only the local SQLite history state and did not write back to MEMORIELA canon.

## G6 — Identity Stability

**Status: NEXT — criteria must be defined before implementation**

PASS criteria will be defined before implementation begins.

This gate must evaluate repeated generation against approved MASTER/identity authority and must separate visual acceptance from mere pipeline success.

## G7 — UI Integration

PASS requires the user-facing UI to invoke the production core without bypassing authority/profile/manifest rules.

## G8 — Desktop Packaging

PASS requires:

- Windows application can be launched from the packaged desktop build
- required backend processes are started or connected correctly
- generation can be initiated from the desktop application
- result can be viewed/retrieved from the application
- packaging does not require manual source-code execution for normal use

## Current status

- G0 Repository Foundation: PASS
- G1 Local Core Bootstrap: PASS
- G2 ComfyUI Connectivity: PASS
- G3 Authority / Profile Compilation: PASS
- G4 Manifest and Output Integrity: PASS
- G5 SQLite History / Lookup: PASS
- G6 Identity Stability: NEXT
