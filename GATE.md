# MEMORIELA Local Image Generator — Production Gates

Status: **INITIAL / ACTIVE FOR FOUNDATION PHASE**

## Gate principle

A feature is not promoted to production-ready status because code exists. It must be executed in the target local environment and verified against the gate for that phase.

No failed result is silently relabeled as PASS.

## G0 — Repository Foundation

PASS requires:

- `START_HERE.md` exists
- `SPEC.md` exists
- `GATE.md` exists
- required production directories exist in Git
- repository can be read and written through the connected GitHub integration

This gate does not prove local runtime execution.

## G1 — Local Core Bootstrap

PASS requires local execution proving:

- application/core entry point starts
- configuration can be loaded
- required paths can be resolved
- logs can be written locally
- fatal startup errors are reported clearly

## G2 — ComfyUI Connectivity

PASS requires local execution proving:

- configured ComfyUI endpoint is reachable
- system/status endpoint can be read
- a standard workflow can be submitted
- generation history can be polled
- output image can be retrieved

## G3 — Authority / Profile Compilation

PASS requires:

- generation request loads an explicit generation profile
- configured MEMORIELA authority sources are resolved
- source revision/hash information is captured
- MASTER/source file hashes are captured where applicable
- effective ComfyUI workflow is compiled deterministically from the selected inputs

Fetching source documents without affecting or validating the compiled generation request is not sufficient for this gate.

## G4 — Manifest and Output Integrity

PASS requires:

- generated image is stored in the intended output structure
- manifest is created for the generation
- manifest records effective parameters and source identifiers
- output and manifest can be associated unambiguously

## G5 — SQLite History / Lookup

PASS requires:

- database initializes from a clean state
- generation metadata can be inserted
- generation/history can be queried
- accepted/rejected status can be stored without modifying source canon

## G6 — Identity Stability

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

- Prototype evidence exists for local ComfyUI generation and Python-to-ComfyUI API execution.
- Production repository foundation is being constructed now.
- No production runtime gate beyond repository foundation is currently claimed as PASS.
