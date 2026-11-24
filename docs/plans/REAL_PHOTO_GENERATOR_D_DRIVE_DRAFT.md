# Local Real Generator — D: Drive Layout / Migration Draft

**Status: DIRECTORY/MIGRATION DRAFT — REQUIREMENTS CONFIRMED IN THE LINKED BASELINE; NOT IMPLEMENTED**
**Recorded:** 2026-11-24 (JST)
**Temporary storage:** `Pin-Gin/local-image-generator` (existing repository)

This note preserves the proposed D-drive layout and migration boundaries for a new local adult-woman **semi-real CG to photoreal-leaning image-and-video generation system**. Product scope and development sequence are now confirmed in [REAL_GENERATOR_REQUIREMENTS_V1.md](REAL_GENERATOR_REQUIREMENTS_V1.md). This document covers only the filesystem/migration proposal; nothing has been implemented or deleted.

## Confirmed product requirements (separate authority)

Read [REAL_GENERATOR_REQUIREMENTS_V1.md](REAL_GENERATOR_REQUIREMENTS_V1.md) for the **user-confirmed target and development order**. In summary:

- Target **high-quality semi-real CG to photoreal-leaning** women, as demonstrated by the user's images; not exclusively real-world photography and not traditional flat anime.
- First: evaluate locally runnable models through several **text-only image generation** trials; use the example images as the quality benchmark.
- Next: on successful quality evaluation, generate the intended woman with **master-image + natural-language instructions** and check persistent identity across scenes; conversational input is a later goal.
- Then: add local **master/reference-image-to-video** and image interpretation/motion, with **60 FPS final output as an unverified goal**.
- Finally: decide **web or desktop application**; platform is not chosen now.
- Preserve downloaded-model inventories and backups, but do not inherit the legacy anime model choices, workflows or quality tests as new-system baselines.

The product **requirements are confirmed**, while the specific D-drive directory names and runtime components below remain provisional until implementation. A future video workflow may need additional model, frame, encoded-video and post-processing folders.

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
- Paths and folder names above are **provisional**. Implement them only on a subsequent explicit user request.

## Scope of this Git change

These Git updates add the separate requirements baseline and update **only planning documentation**. They do not modify `START_HERE.md`, the current FREE/LEARN/MEMORIELA architecture, code, model files, experiments, or local environments.


## Future video expansion and open design decisions (not yet fixed)

The initial directory tree remains a **provisional scaffold**, not a production-ready layout. User product requirements are complete as of 2026-11-24, including video generation. Before actual setup, check video models, frame staging, video outputs and post-processing storage segregation. Exact names and component boundaries are **undecided**, so none are provisioned by this document.

Open technical decisions include: which model(s) satisfy the target semi-real CG to photoreal-leaning image quality; which model(s) perform image-conditioned/video synthesis; output resolution, duration and aspect ratio; identity and motion review criteria; the exact meaning of achieving 60 FPS; processing costs and latency; privacy/security requirements; and web-versus-desktop UI.

**Safety/continuation:** Requirements were finalized for this checkpoint in the linked baseline. This directory plan is still a record for handoff only. Do not act on the destructive migration plan or begin implementation without a subsequent explicit request.
