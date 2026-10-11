# Shared rendering learning

This area owns local learning for the shared rendering style only. It is separate from MEMORIELA character/outfit learning and from FREE prompt content.

Target learned style: `Matte Dimensional Anime`.

## Local tool ownership

All learning tools created for this project stay below the repository root:

- `tools/python312/` — private Python 3.12 runtime used only for learning setup
- `tools/sd-scripts/` — local clone of `kohya-ss/sd-scripts`
- `tools/_downloads/` — setup downloads

These directories are runtime/tool dependencies and are ignored by Git.

## One-time setup

From `C:\Dev\local-image-generator`:

```powershell
powershell -ExecutionPolicy Bypass -File .\train_rendering.ps1 -Action setup
```

The setup action:

1. installs a private Python 3.12 runtime under `tools/python312` when missing;
2. clones/updates `kohya-ss/sd-scripts` under `tools/sd-scripts`;
3. creates `tools/sd-scripts/venv`;
4. installs PyTorch 2.8.0 / CUDA 12.8 packages for RTX 50-series training;
5. installs the current `sd-scripts` requirements;
6. verifies CUDA/GPU visibility;
7. resolves the existing ComfyUI SDXL Base checkpoint and LoRA directory;
8. writes the Git-ignored `learning/rendering/train_config.local.json`.

The default ComfyUI root is:

`%USERPROFILE%\Downloads\ComfyUI_windows_portable_nvidia\ComfyUI_windows_portable\ComfyUI`

Override it with `-ComfyUIRoot` if the installation moves.

## Manifest-driven reference generation

`generation_manifest.json` defines the twenty independent reference-image specifications and their canonical LoRA captions. `GENERATION_BATCH_INSTRUCTIONS.md` defines how another image-generation project should consume that manifest.

Only rendering characteristics are shared between items. Character identity, clothing, background, pose, camera and composition are deliberately varied.

Generated images are staged locally under:

`learning/rendering/incoming/`

The incoming directory is ignored by Git except for `.gitkeep`.

If files are named with their four-digit ID, for example `0005.png` or `0005_result.webp`, run:

```powershell
powershell -ExecutionPolicy Bypass -File .\train_rendering.ps1 -Action prepare
```

The prepare action:

- maps each incoming image to its manifest ID;
- copies it into `learning/rendering/dataset/20_mdanime/` with a canonical ID filename;
- writes the matching `.txt` caption from the manifest automatically;
- preserves an already imported image unless `-Replace` is explicitly supplied;
- detects exact duplicate image files by SHA-256;
- reports missing, ambiguous and unassigned images.

For downloaded images that do not contain IDs in their filenames, sequential assignment is available explicitly:

```powershell
powershell -ExecutionPolicy Bypass -File .\train_rendering.ps1 -Action prepare -Sequential -StartId 5
```

Sequential mode sorts untagged incoming files by modification time and maps them to remaining manifest IDs beginning at `StartId`. Use it only when the download order is known. It does not visually infer which prompt produced an image.

To preview without copying files:

```powershell
powershell -ExecutionPolicy Bypass -File .\train_rendering.ps1 -Action prepare -DryRun
```

To intentionally replace an existing imported item:

```powershell
powershell -ExecutionPolicy Bypass -File .\train_rendering.ps1 -Action prepare -Replace
```

## Dataset contract

The prepared training dataset lives under:

`learning/rendering/dataset/20_mdanime/`

Each image has a same-name `.txt` caption. Example:

- `0001.png`
- `0001.txt`

Every caption includes the trigger token `mdanime_style` plus content tags describing what is depicted. The style itself stays consistent while subjects, camera distance, scene depth, lighting direction, materials, and backgrounds vary.

Do not use near-duplicate frames as a substitute for real variation. The automatic importer detects byte-identical duplicates only; visual QA for near-duplicates and style compliance remains a separate acceptance step.

## Training sequence

1. Prepare staged images:

```powershell
powershell -ExecutionPolicy Bypass -File .\train_rendering.ps1 -Action prepare
```

2. Validate local environment and dataset:

```powershell
powershell -ExecutionPolicy Bypass -File .\train_rendering.ps1 -Action validate
```

3. Train:

```powershell
powershell -ExecutionPolicy Bypass -File .\train_rendering.ps1 -Action train
```

4. Publish into ComfyUI and activate the shared rendering LoRA:

```powershell
powershell -ExecutionPolicy Bypass -File .\train_rendering.ps1 -Action publish -Activate
```

5. Rebuild the desktop app so the activated shared-rendering configuration is bundled.

## Important

The repository implements and validates the training pipeline, but no LoRA is considered trained or verified until a real accepted dataset has been supplied and the local training command has completed successfully. `publish` is intentionally invalid before the `.safetensors` training output exists.
