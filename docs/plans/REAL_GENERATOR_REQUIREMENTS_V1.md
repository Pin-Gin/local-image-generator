# LOCAL REAL GENERATOR — Requirements Baseline v1

**Status:** USER-CONFIRMED GOALS / IMPLEMENTATION NOT STARTED  
**Date:** 2026-11-24 (JST)  
**Temporary home:** `Pin-Gin/local-image-generator` (old Git repository; this is a handoff document, not an instruction to reuse its anime generation engine)  
**D-drive directory/migration plan:** [REAL_PHOTO_GENERATOR_D_DRIVE_DRAFT.md](REAL_PHOTO_GENERATOR_D_DRIVE_DRAFT.md)

## 1. Product objective — exact distinction

Build an independent, locally operated image-and-video generation workflow capable of generating original **adult women** with quality comparable to the user-provided example images.

**Target rendering range: HIGH-QUALITY SEMI-REAL CG → PHOTOREAL-LEANING.**
- Do **not** redefine this as exclusively photographic realism or a direct reproduction of an unretouched camera photograph.
- Do **not** classify the goal as conventional flat 2D anime. Facial beauty, softly idealized proportions and skin may be retained when appropriate to the example's semi-real CG aesthetics.
- Quality is judged against the **user-provided examples**: appealing and stable face, fine hair, coherent human anatomy, skin/surface material, form/depth, lighting, background integration, and image-wide consistency.
- Different lighting/material responses are permitted: the user presented both a bright outdoor pool setting with soft light and a darker sauna setting with stronger wet-skin reflections. **Do not ban CG-like highlights or wet-surface gloss globally** because legacy anime-specific rules discouraged CGI/PBR gloss.
- “GPT-level quality” means the user's desired qualitative visual benchmark, **not** that equivalence has already been demonstrated or that a universal numerical score has been agreed.

**Character vs style references:** A previously supplied portrait of the short light-brown-haired fictional adult woman is the intended *future character reference/master candidate*. The subsequently supplied poolside and sauna images illustrate the desired **style/quality range**. Do not assume they establish a single canonical body, identical identity, outfit or lighting. Exact accepted character master(s) and image asset paths are to be confirmed during Phase 2; do not invent them.

## 2. Fixed development order and acceptance gates

### Phase 0 — Clean rebuild / inventory

- Move project organization to the D: drive, independent of the old anime-focused repository; the user will manually create the new Git repository.
- Retire old local repository and historical experiments **only after** verifying backups; do not inherit old model/experiment configurations as the new implementation baseline.
- Inventory **already downloaded** model files and installed applications, preserve reusable copies and hashes, and assess reusability later. No model is selected merely because it was installed in old ComfyUI.
- Existing reference images are reportedly in Downloads; verify their presence and backup before deletion.
- The detailed directory layout is retained in the linked draft; revise it for video workloads when finalizing infrastructure.

### Phase 1 — Text-only image model research and image-quality tests

1. Identify current, locally runnable models capable of high-quality **semi-real CG to photoreal-leaning adult female subjects**. Do not filter only for “pure photoreal” checkpoints.
2. Consider the available RTX 5080 (16 GB VRAM), Windows runtime compatibility, model licenses, costs, memory, and expected runtime when selecting candidates. Local use and no recurring generation charges are preferred constraints.
3. Test selected models multiple times with **text prompts only**. **No master/reference image conditioning at this stage.**
4. Review outputs against user examples, evaluating facial quality, fine hair, beautiful but coherent skin, anatomy/limbs and hands, body proportions, shading, lighting, environmental consistency, visual artifacts, and repeatability.
5. Advance only when the user approves the output quality. No arbitrary threshold or model winner is predetermined.

### Phase 2 — Master image + text-guided image generation

- After Phase 1 quality approval, create/evaluate the fictional adult woman's appearance in the target semi-real CG–photoreal rendering range.
- The user approves a master reference; preserve its face, hairstyle/color, body type, and agreed individual identity features.
- Use **natural-language instructions + master image** to generate new scenes/images, including clothing, body pose, expression, camera angle and background changes, without unintended identity or rendering-quality drift.
- Verify both **image quality** and **same-character consistency** separately across different prompts/seeds.
- Direct text input is the initial interface requirement. Conversational/chat-style instructions are an intended **future capability**, not a requirement to implement before quality is established.
- The chosen image-generation backend may be different from the video backend.

### Phase 3 — Local video generation

- Support generating motion from **master/reference image + written motion instruction**.
- Support interpreting an input still image and generating plausible motion from it (**image-to-video**), while preserving agreed character appearance and quality.
- Aim for **60 FPS output**. This is a target, not a verified capability, and does not mandate native 60-FPS generation. Test native frame rates vs. frame interpolation and temporal refinement as applicable.
- Evaluate character consistency over time, motion coherence, anatomy, temporal flicker, resolution, video length, memory consumption and generation time. Specific resolution, duration, performance targets, and model choices remain undecided.
- Anticipate separate models, frame staging, encoded video files and optional post-processing. Do not assume one image model meets all video goals.

### Phase 4 — Application implementation (last)

- Only after the desired image and video generation pipelines work and quality is assessed, choose between a **Web app** and a **desktop app**.
- Keep backend generation/model orchestration decoupled from the future user interface so the interface decision need not dictate model selection.
- The final UI/UX will support text/master-driven generation and is intended eventually to support chat-like input. Detailed screen design and framework are not fixed.

## 3. Acceptance criteria / current unknowns

| Area | Intended criterion | Status |
| --- | --- | --- |
| Rendering | Semi-real CG to photoreal-leaning, matching user example image quality | GOAL; not verified locally |
| Text-only image generation | Multiple successful outputs from textual instructions alone | TO TEST |
| Character reference | Approved fictional adult woman master usable across scenes | NOT YET ACCEPTED FOR NEW SYSTEM |
| Identity preservation | Same recognizable individual after pose/outfit/scene changes | TO TEST |
| Natural-language control | Text + master drive desired changes without unwanted appearance drift | TO TEST |
| Video | Animate from image/master with text and image understanding | TO RESEARCH / TEST |
| 60 FPS | Final video output target; assess visual quality after conversion | GOAL; no native FPS guarantee |
| App platform | Web or desktop after working generation engines | UNDECIDED |

The images attached in conversation are **quality references**, not uploaded assets stored in Git. Do not commit user reference images or infer asset paths. Do not assert the target quality is already attainable on the specified GPU without experiments.

## 4. Non-destructive migration and Git boundaries

- **Do not edit the old FREE/LEARN/MEMORIELA implementation**, migrate historical v1–v19 code as accepted baselines, or change character canon.
- The old repo is only the temporary storage location for these requirements. The user intends to remove it and create a fresh repository manually. **Preserve this requirements document and the linked directory plan outside the old repo before deleting the old remote/local repo.**
- Old untracked files and downloaded models may have value. Verify files and copy integrity before the user removes any old local directory. Inventory files are not backup copies.
- Do not execute deletion, `git clean`, bulk `git add .`, model downloads, migrations, or generation just because this requirement document is committed.
- Newly chosen models, source licenses and detailed architecture must be established by research and user-reviewed tests when Phase 1 begins.

## 5. Authority and future change procedure

This document reflects the **user-confirmed scope and sequence as of 2026-11-24**. The D-drive folder tree in the linked document remains an **implementation proposal**, not a claim that folders have been created. Technical choices still marked undecided are not silently promoted to fixed requirements.

If later user instructions supersede these requirements, record the delta explicitly and preserve the older text in Git history.
