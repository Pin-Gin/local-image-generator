# Generation-side Local AI Assistant

Status: **IMPLEMENTED / LOCAL VERIFICATION REQUIRED**

The image-generation view now has a local-AI assistant using the already installed `qwen3-vl:8b-instruct` model through the project-local Ollama service.

## What is implemented

- `generate` local-AI role in `config/local_ai.json`.
- Generation-view AI chat.
- The assistant can receive the current generated image plus the original generation instruction.
- Optional `生成後に自動解析` switch.
- Generated-image analysis keeps requested content separate from visibly observed output.
- `この画像を学習へ送る` transfers the current generated image into the LEARN image slot without requiring a manual file upload.
- Generation-side assistant replies use the existing copyable chat-message UI.

## Important boundary

This feature does **not** yet perform persistent dataset registration, LoRA training, or model-weight updates automatically.

Current flow:

```text
Generate image
  -> local generation AI can inspect prompt + generated image
  -> user can discuss defects / learning candidates
  -> user can send the generated image to LEARN
  -> LEARN can inspect and classify learning candidates
```

Future persistent-learning flow is still separate:

```text
explicit acceptance
  -> dataset registration
  -> validation
  -> training
  -> publish / activate
```

The generation pipeline itself remains the existing FREE / MEMORIELA -> compiler -> ComfyUI path. The local AI assistant does not silently rewrite the generation prompt or replace the existing router/compiler.

## Verification required

After pulling and rebuilding the desktop app, verify on the local Windows machine:

1. `生成AIアシスト` reports `オンライン: qwen3-vl:8b-instruct`.
2. Generate an image normally.
3. Ask the generation AI about the current result and confirm it sees the generated image.
4. Enable `生成後に自動解析`, generate again, and confirm automatic analysis appears.
5. Press `この画像を学習へ送る` and confirm the same generated image appears in LEARN.

Do not mark these UI paths VERIFIED until those checks have been run locally.
