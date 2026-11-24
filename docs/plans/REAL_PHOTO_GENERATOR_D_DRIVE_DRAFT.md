# Real Photo Generator — D: Drive Directory Draft

**Status: DRAFT / HANDOFF ONLY — NOT IMPLEMENTED / NOT APPROVED AS FINAL**
**Recorded:** 2026-11-24 (JST)
**Temporary storage:** `Pin-Gin/local-image-generator` (existing repository)

This note preserves the user's **provisional** directory layout and migration intent for a new, independent, photorealistic adult-woman local image generator. The user has additional requirements to communicate; do **not** finalize, provision, install, delete, or reorganize any runtime or repository on the basis of this document alone.

## Goal and planned sequence (updated user requirements, 2026-11-24)

**Product direction:** Locally generate high-quality, photorealistic images of a fictional adult woman, eventually with reference-master-driven image and video generation. The intended quality benchmark is *GPT image-generation-like quality*, not a currently verified achievement or a numerical guarantee.

**Order of work (do not skip forward):**

0. **Environment reset & model inventory:** After approval of the D: layout, build a clean runtime independent of the anime-focused repository. Inventory downloaded apps/models and verify copies before any removal. Git repository creation remains user-controlled.
1. **Find & evaluate photorealistic image models:** Search for models that excel at photorealistic adult female subjects and fit available local hardware (RTX 5080, 16 GB VRAM). Run multiple **text-to-image only** trials and judge actual images. Do not carry old anime tuning assumptions, previous models, or test results forward as accepted baselines. Evaluate visual realism, anatomy, face/hair/skin, lighting, consistency and practical runtime constraints.
2. **Master-driven image generation:** Only after user accepts the text-only output quality, create/evaluate a photoreal interpretation of the fictional adult woman in the supplied reference. Preserve the approved face/hair/body features. Support **text + master image** to generate different scenes, clothing and poses; **chat-style input is a future interface goal**, not a present dependency. Validate identity consistency separately from image quality.
3. **Video generation capability:** Plan both (a) master/reference image plus a textual motion instruction and (b) interpreting a supplied still image and creating appropriate motion (image-to-video). **60 FPS final video output is a goal**, not a confirmed local capability or a promise of native 60-FPS synthesis. Whether native FPS, interpolation and/or temporal consistency processing are appropriate remains to be tested. Evaluate motion coherence, identity retention, temporal flicker, generation time, VRAM, resolution and duration. Do not assume the chosen still-image model also supports video.
4. **Application packaging last:** Only after the image and video paths are evaluated, decide whether the tool should be a **web application or desktop application**. Neither platform is fixed now. Keep generation backends independent of the eventual user interface.

**Gates:** Model choice, photo realism, identity fidelity, video quality and 60-FPS viability must each be established by user-reviewed output, not by a filename, installed node, successful preflight or marketing claim. No image/video models have been newly selected here.

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

This plan's Git changes edit **only this planning document**. It does not modify `START_HERE.md`, the current FREE/LEARN/MEMORIELA architecture, code, model files, experiments, or local environments.


## Future video expansion and open design decisions (not yet fixed)

The initial directory tree remains a **provisional scaffold**, not a production-ready layout. The final tree must be revised after the user finishes specifying requirements. In particular, avoid baking photo-only assumptions into the eventual storage and runtime layout; video models, temporary frames, video outputs and post-processing may need their own storage segregation. Exact names and component boundaries are **undecided**, so none are provisioned by this document.

Open decisions include: which model(s) satisfy photoreal image quality; which model(s) perform image-conditioned/video synthesis; output resolution, duration and aspect ratio; identity and motion review criteria; the exact meaning of achieving 60 FPS; processing costs and latency; privacy/security requirements; and web-versus-desktop UI.

**Safety/continuation:** The user has indicated that additional requirements may follow. This is a record for handoff only. Do not act on the destructive migration plan or begin implementation without a subsequent explicit request.
