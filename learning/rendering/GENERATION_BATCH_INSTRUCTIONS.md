# Matte Dimensional Anime reference-image generation

Use `generation_manifest.json` as the sole content plan for the rendering-training reference images.

## Goal

Generate independent reference images that share only the target rendering characteristics. Do not create a continuing character series. The LoRA must learn rendering, not one person, outfit, background, composition, or camera setup.

## Required generation behavior

For every manifest item:

1. Start from a fresh text-to-image generation state.
2. Do not use any previously generated image as an image reference, edit target, variation source, identity reference, pose reference, or composition reference.
3. Combine only:
   - `shared_rendering_prompt`
   - the current item's `content_prompt`
4. Apply `shared_negative_prompt` as exclusions.
5. Generate at the manifest `image_size`.
6. Do not draw the item ID, caption, text, logo, signature, or watermark inside the image.
7. After generation, identify the result outside the image with the current four-digit item ID.
8. If the result materially violates the current `content_prompt` or target rendering, regenerate only that item from a fresh state.

The previous item's subject, face, hair, clothing, palette, background, pose, framing, and camera placement are all forbidden as continuity constraints.

## Rendering target

Keep the image visibly anime rather than photorealistic, while preserving readable 3D-anime-like volume, modeled planes, smooth form-describing shading, matte surfaces, restrained highlights, and clear spatial depth.

Reject strong photorealism, live-action skin, glossy CGI/PBR, waxy or plastic surfaces, flat cel shading, watercolor, painterly wash, sketch rendering, weak depth, or text artifacts.

## Batch operation

You may process multiple manifest items in one user request, but each image-generation call must be independent. Never derive item N+1 by editing, varying, or referencing item N.

If resuming after accepted images, begin from the requested item ID and leave already accepted IDs unchanged.

Captions do not need to be generated manually. `generation_manifest.json` already contains the canonical caption for every item, and the local `prepare` action writes the `.txt` files automatically.
