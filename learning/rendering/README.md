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

## Dataset contract

Place training images under:

`learning/rendering/dataset/20_mdanime/`

Each image must have a same-name `.txt` caption. Example:

- `0001.png`
- `0001.txt`

Every caption must include the trigger token `mdanime_style` plus content tags describing what is depicted. The style itself should stay consistent across the dataset while subjects, camera distance, scene depth, lighting direction, materials, and backgrounds should vary.

Do not use near-duplicate frames as a substitute for real variation. The dataset is intended to teach rendering characteristics rather than a specific person, outfit, or background.

## Training sequence

1. Validate local environment and dataset:

```powershell
powershell -ExecutionPolicy Bypass -File .\train_rendering.ps1 -Action validate
```

2. Train:

```powershell
powershell -ExecutionPolicy Bypass -File .\train_rendering.ps1 -Action train
```

3. Publish into ComfyUI and activate the shared rendering LoRA:

```powershell
powershell -ExecutionPolicy Bypass -File .\train_rendering.ps1 -Action publish -Activate
```

4. Rebuild the desktop app so the activated shared-rendering configuration is bundled.

## Important

The repository implements and validates the training pipeline, but no LoRA is considered trained or verified until a real dataset has been supplied and the local training command has completed successfully. `publish` is intentionally invalid before the `.safetensors` training output exists.
