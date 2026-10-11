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

Do not commit `.safetensors`, `.ckpt`, `.pt`, `.pth`, `.onnx`, or `.gguf` files.
