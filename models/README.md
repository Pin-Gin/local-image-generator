# local-RAG model asset root

This directory is the canonical local storage root for image-generation model assets used by local-RAG.

Model binaries are local runtime assets and are ignored by Git.

Expected layout:

```text
models/
  checkpoints/
  loras/
  controlnet/
  upscale_models/
  vae/
```

Current base checkpoint location:

```text
models/checkpoints/sd_xl_base_1.0.safetensors
```

Verified local state on 2026-10-11:

- the project copy under `C:\Dev\local-image-generator\models\checkpoints` matched the source SHA-256;
- `configure_comfyui_models.ps1` configured the portable ComfyUI `extra_model_paths.yaml` with the `local_rag` model root;
- after restart, ComfyUI `CheckpointLoaderSimple` exposed `sd_xl_base_1.0.safetensors` through `/object_info/CheckpointLoaderSimple` while using the project model root.

The previous Downloads/ComfyUI-local duplicate checkpoint is no longer required once removed locally.

ComfyUI should read this directory through `extra_model_paths.yaml` rather than requiring duplicate model files under the portable ComfyUI installation.

## Pose-control target

Step E uses a project-owned SDXL OpenPose ControlNet at:

```text
models/controlnet/SDXL/controlnet-openpose-sdxl-1.0/diffusion_pytorch_model.safetensors
```

`install_pose_control.ps1` installs the DWPose preprocessor under the existing portable ComfyUI runtime and downloads the OpenPose ControlNet above into the project model root. The binary remains ignored by Git.

The pose-control asset is not considered locally verified until ComfyUI has been restarted and `src/pose_control_capability_test.py` reports `[POSE:CAPABILITY:READY]`.

Do not commit `.safetensors`, `.ckpt`, `.pt`, `.pth`, `.onnx`, or `.gguf` files.
