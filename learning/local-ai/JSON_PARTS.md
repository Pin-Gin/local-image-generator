# Reusable JSON Parts

## 1. Naming

A reusable part has a stable `part_id` and an integer `version`.

Canonical call syntax:

```text
part:<part_id>@<version>
```

Rules:

- `part_id`: lowercase ASCII, digits, `.`, `_`, `-`; no `/` or path separators.
- `version`: positive integer.
- A changed payload creates a new version; do not overwrite an accepted older version.
- Generation records store the exact resolved reference.

Examples:

```text
part:pose.hair-touch@1
part:camera.three-quarter@2
part:outfit.school-uniform-summer@3
```

## 2. Canonical document shape

```json
{
  "schema_version": 1,
  "document_type": "local-rag/json-part",
  "part_id": "pose.hair-touch",
  "version": 1,
  "part_type": "pose",
  "name": "Hair touch pose",
  "status": "accepted",
  "aliases": ["髪に手を添える"],
  "tags": ["pose", "hand"],
  "payload": {
    "generation": {
      "positive": "one hand gently touching the hair, relaxed elbow",
      "negative": "merged fingers, broken wrist"
    }
  },
  "provenance": {
    "source_type": "local-ai-learning",
    "source_ref": ""
  }
}
```

Canonical documents keep their own identity/status inside the JSON and remain the preferred format for application-managed persistence and Oracle indexing.

## 3. Manual structured JSON compatibility

Files manually placed in the accepted `json-parts` directory may also use a simpler structured JSON shape without the canonical `local-rag/json-part` wrapper.

Example:

```json
{
  "file_name": "anime_pose_hair_touch.v1.json",
  "description": "anime hair-touch pose data",
  "pose": {
    "type": "hair-touch",
    "character": {
      "gender": "female",
      "hair_color": "blonde",
      "eye_color": "blue"
    },
    "hands": {
      "left_hand": "touching hair",
      "right_hand": "crossed over chest"
    },
    "camera_composition": "full-body shot"
  }
}
```

For this manual compatibility path:

- the canonical identity/version comes from the filename and requested ref;
- `anime_pose_hair_touch.v1.json` resolves as `part:anime_pose_hair_touch@1`;
- when `file_name` exists inside the JSON, it must match the actual canonical filename (case-insensitive);
- `description` becomes display metadata only and is not injected into the generation prompt;
- nested structured scalar values are deterministically flattened into the positive generation prompt;
- optional top-level `positive` overrides automatic flattening;
- optional top-level `negative` or `negative_prompt` becomes the negative generation prompt;
- the file is considered generation-eligible only because it physically lives in the accepted `json-parts` store;
- the loader does not rewrite the manual file and does not automatically register it into Oracle.

The strict canonical schema is still required for the explicit `Part登録` / `Part採用` API path. Manual compatibility is a generation-read feature, not a relaxation of the persistent-write contract.

## 4. Generation reuse

The first implemented reusable payload is `payload.generation` for canonical parts:

- `positive`: appended to the positive generation prompt.
- `negative`: appended to the negative generation prompt.

Manual structured parts are converted at read time into the same internal positive/negative representation.

Generation JSON references parts through `parts`:

```json
{
  "positive": "silver-haired woman in a park",
  "negative": "low quality",
  "parts": [
    "part:pose.hair-touch@1"
  ]
}
```

For a manually stored file named `anime_pose_hair_touch.v1.json`:

```json
{
  "positive": "anime character",
  "parts": [
    "part:anime_pose_hair_touch@1"
  ]
}
```

Other payload sections may be added later for ControlNet, LoRA, character identity, outfit adapters, backgrounds, or camera controls. They must be versioned and explicitly implemented before the runtime may use them.

## 5. Storage

Accepted local files:

```text
learning/local-ai/store/json-parts/<part_id>.v<version>.json
```

Example:

```text
learning/local-ai/store/json-parts/pose.hair-touch.v1.json
```

Canonical accepted parts may also be mirrored/indexed in Oracle table `LR_JSON_PART`. Manual structured compatibility files are read directly from the accepted local file store unless separately converted/registered through the canonical persistence path.

## 6. Local read verification

To verify a local part without starting ComfyUI:

```powershell
.\tools\python312\python.exe .\src\json_part_read_test.py --ref part:anime_pose_hair_touch@1
```

Expected first line:

```text
[JSON-PART:READ:OK] ref=part:anime_pose_hair_touch@1
```
