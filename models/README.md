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

The user verified that the copy under `C:\Dev\local-image-generator\models\checkpoints` has the same SHA-256 as the previous ComfyUI-local copy.

ComfyUI should read this directory through `extra_model_paths.yaml` rather than requiring duplicate model files under the portable ComfyUI installation.

Do not commit `.safetensors`, `.ckpt`, `.pt`, `.pth`, `.onnx`, or `.gguf` files.
