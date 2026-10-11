# Shared rendering learning

This area owns local learning for the shared rendering style only. It is separate from MEMORIELA character/outfit learning and from FREE prompt content.

Target learned style: `Matte Dimensional Anime`.

## Dataset contract

Place training images under:

`learning/rendering/dataset/20_mdanime/`

Each image must have a same-name `.txt` caption. Example:

- `0001.png`
- `0001.txt`

Every caption should include the trigger token `mdanime_style` plus content tags that describe what is depicted. The style itself should stay consistent across the dataset while subjects/scenes should vary.

## Commands

1. Copy `train_config.example.json` to `train_config.local.json` and set local paths.
2. Validate dataset and environment:
   `python src/rendering_learning.py validate --config learning/rendering/train_config.local.json`
3. Train:
   `python src/rendering_learning.py train --config learning/rendering/train_config.local.json`
4. Publish the resulting LoRA into ComfyUI and activate it in shared rendering:
   `python src/rendering_learning.py publish --config learning/rendering/train_config.local.json --activate`
5. Rebuild the desktop app so the activated shared rendering config is bundled.

## Important

The repository implements and validates the training pipeline, but no LoRA is considered trained or verified until a real dataset has been supplied and the local training command has completed successfully.
