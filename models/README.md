# local-RAG model asset root

This directory is the canonical local storage root for image-generation model assets used by local-RAG.

Model binaries are local runtime assets and are ignored by Git.

Expected layout:

```text
models/
  checkpoints/
  loras/
  controlnet/
  ipadapter/
  clip_vision/
  upscale_models/
  vae/
```

## Base checkpoint — VERIFIED

```text
models/checkpoints/sd_xl_base_1.0.safetensors
SHA256: 31E35C80FC4829D14F90153F4C74CD59C90B779F6AFE05A74CD6120B893F7E5B
```

`configure_comfyui_models.ps1` exposes the project-owned model root to the portable ComfyUI runtime through `extra_model_paths.yaml`.

## Pose Control — VERIFIED

```text
models/controlnet/SDXL/controlnet-openpose-sdxl-1.0/diffusion_pytorch_model.safetensors
```

The current DWPose/OpenPose stack was user-verified through the capability probe and real FREE runtime generation.

## IP-Adapter appearance authority — VERIFIED capability

```text
models/ipadapter/ip-adapter-plus_sdxl_vit-h.safetensors
models/clip_vision/CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors
```

The user verified that ComfyUI exposes:

```text
IPAdapterUnifiedLoader
IPAdapterAdvanced
IPAdapterModelLoader
CLIPVisionLoader
```

and both project-owned model files are visible to ComfyUI.

The target FREE architecture uses the main reference image through IP-Adapter and generates from a fresh latent; the source image is not used as a VAE/img2img starting latent.

## Rendering / lineart LoRAs

Project-local LoRA binaries belong under:

```text
models/loras/
```

The trained Matte Dimensional Anime LoRA has previously generated successfully, but `shared/rendering/matte_dimensional_anime.json` currently keeps its LoRA `enabled: false`. Do not silently enable it.

Do not commit `.safetensors`, `.ckpt`, `.pt`, `.pth`, `.onnx`, or `.gguf` files.
