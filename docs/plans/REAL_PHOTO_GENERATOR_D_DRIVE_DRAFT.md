# Real Photo Generator — D: Drive Directory Draft

**Status: DRAFT / HANDOFF ONLY — NOT IMPLEMENTED / NOT APPROVED AS FINAL**
**Recorded:** 2026-11-24 (JST)
**Temporary storage:** `Pin-Gin/local-image-generator` (existing repository)

This note preserves the user's **provisional** directory layout and migration intent for a new, independent, photorealistic adult-woman local image generator. The user has additional requirements to communicate; do **not** finalize, provision, install, delete, or reorganize any runtime or repository on the basis of this document alone.

## Goal and phases

1. **Phase 1:** Generate a photorealistic adult woman **from text only** and assess image quality before introducing identity reference images.
2. **Phase 2:** If quality is accepted, derive a realistic representation of the adult woman in the user-provided image, preserving agreed facial, hair, and bodily identity characteristics. Acceptance of a new realistic master is a separate user decision.
3. **Phase 3:** Build a local tool with Japanese-language prompt input, references, generation settings and history, using the chosen verified generation backend.

The old anime-oriented architecture and v1–v19 experiments are historical context **not inherited as the new design**. Already-downloaded models may still be useful: inventory them, but do not presume they are selected or verified for the new photorealistic goal.

## Proposed filesystem layout (subject to change)

```text
D:\AI\real-photo-generator\
│
├─ repo\                      # NEW Git repository; user creates/clones manually
│
├─ runtime\
│  ├─ comfyui\                # ComfyUI runtime
│  └─ python\                 # Python runtime
│
├─ assets\
│  ├─ models\                 # Active selected models
│  └─ references\
│     ├─ incoming\            # New reference images
│     ├─ masters\             # User-approved masters
│     └─ poses\               # Pose references
│
├─ outputs\
│  ├─ quality-tests\          # Image-quality comparisons
│  └─ approved\               # User-approved outputs
│
├─ backups\
│  ├─ downloaded-apps\        # Downloaded apps and archives
│  ├─ downloaded-models\      # Backup copies of downloaded model files
│  └─ manifests\              # Inventory CSV / hashes
│
├─ state\                     # Local settings / persistent state
├─ logs\
└─ temp\
```

## Storage and migration boundaries

- Keep `repo/` separate from local applications, model weights, reference images, generated outputs, state, and backups. Heavy or private assets must not be committed merely because they exist under the project root.
- **Do not create or initialize the new Git repository.** The user will create it manually.
- The user's intention is eventually to retire/delete the **old local repository and historical experiment code**, and move the work from C: to D:. This document does not authorize automatic deletion or migration.
- Preserve an inventory of downloaded models from existing ComfyUI / downloads locations. Actual files need a verified copy and checksum comparison before any old location is removed. An inventory CSV alone is not a backup.
- Previously observed installed model filenames (presence was confirmed in a user-supplied 2026-11-24 preflight log):
  - `qwen_image_2.1_int8_convrot.safetensors`
  - `qwen3vl_8b_int8_convrot.safetensors`
  - `qwen_image_2.1_vae_bf16.safetensors`
  Other FLUX, SDXL and Qwen-Edit models are **candidates for inventory only**, not confirmed selections.
- The user reports that source reference imagery is in Downloads. Verify those files and copies before any deletion.
- Existing project and local files may contain untracked work; avoid `git clean`, mass staging (`git add .`), moving folders, or destructive scripts.
- Because this **temporary handoff is stored in the old repository**, copy it to the new repository (or independent backup) before deleting the old repository or remote.
- A setup PowerShell script was described in the conversation; its integrity, current contents and Windows execution are **not independently verified here**. Do not assume it has been run.
- Paths and folder names above are **provisional**. Await further user requirements before implementation.

## Scope of this Git change

This Git change adds **only this planning document**. It does not modify `START_HERE.md`, the current FREE/LEARN/MEMORIELA architecture, code, model files, experiments, or local environments.
