# Reference images

This directory stores local reference images used by deterministic FREE generation.

```text
references/
└─ free/
   ├─ main/   # IP-Adapter appearance authority
   └─ pose/   # DWPose/OpenPose pose authority
```

## `free/main/`

Use for the main appearance reference image. The target FREE architecture reads it through IP-Adapter and generates from a fresh latent; it is not used as an img2img starting latent.

## `free/pose/`

Use for the pose reference image. The target FREE architecture reads it through DWPose and OpenPose ControlNet.

Actual reference images are local runtime/user assets and are ignored by Git by default. Keep filenames stable when a JSON/request references them by relative path.