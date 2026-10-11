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
- A changed canonical payload should create a new version rather than silently overwriting an accepted older version.
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

Canonical documents keep their identity/status inside the JSON and remain the preferred format for application-managed persistence and Oracle indexing.

## 3. Manual structured JSON compatibility

Files manually placed in the accepted `json-parts` directory may use a simpler structured JSON shape without the canonical `local-rag/json-part` wrapper.

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

- identity/version comes from the filename and requested ref;
- `anime_pose_hair_touch.v1.json` resolves as `part:anime_pose_hair_touch@1`;
- when `file_name` exists inside the JSON, it must match the actual canonical filename case-insensitively;
- `description` becomes display metadata only and is not injected into generation content;
- UTF-8 BOM-prefixed files are accepted;
- a whole-file Markdown fence such as ` ```json ... ``` ` is accepted;
- the source file is never rewritten by the read path;
- when no explicit top-level `positive` exists, nested scalar content is linearized into the internal positive prompt using **dotted hierarchy paths**;
- original scalar values, traversal order, and duplicate leaves are retained;
- optional top-level `positive` overrides automatic hierarchy linearization;
- optional top-level `negative` or `negative_prompt` becomes the negative generation prompt;
- the file is generation-eligible because it physically lives in the accepted `json-parts` store;
- the loader does not automatically register a manual compatibility file into Oracle.

Example conversion:

```json
{
  "pose": {
    "body": {
      "state": "nude"
    },
    "expression": "smiling"
  }
}
```

becomes an internal positive string containing:

```text
pose.body.state: nude, pose.expression: smiling
```

The strict canonical schema is still required for the explicit application-managed `Part登録` / `Part採用` persistence path. Manual compatibility is a generation-read feature, not a relaxation of the canonical persistence contract.

## 4. Generation reuse

Canonical parts currently expose `payload.generation`:

- `positive`: appended/combined with positive generation content.
- `negative`: appended/combined with negative generation content.

Manual structured parts are converted at read time into the same internal positive/negative representation.

Generation JSON references exact parts through `parts`:

```json
{
  "positive": "silver-haired woman in a park",
  "negative": "low quality",
  "parts": [
    "part:pose.hair-touch@1"
  ]
}
```

Manual file example:

```text
learning/local-ai/store/json-parts/anime_pose_hair_touch.v1.json
```

is referenced as:

```json
{
  "positive": "anime character",
  "parts": [
    "part:anime_pose_hair_touch@1"
  ]
}
```

Current `chat_contract.py` resolves explicit `parts` references and merges their internal positive/negative strings into `prompt_input`.

Important: automatic selection of JSON Parts from the directory is **not** current behavior. A Part is used only when the request explicitly references it, unless a future design explicitly adds another selection mechanism.

## 5. Storage

Accepted local files:

```text
learning/local-ai/store/json-parts/<part_id>.v<version>.json
```

Staging files:

```text
learning/local-ai/store/staging/<part_id>.v<version>.json
```

Canonical accepted parts may also be mirrored/indexed in Oracle table `LR_JSON_PART`.

Manual structured compatibility files are local-file generation assets unless they are separately converted/registered through the canonical persistence path.

## 6. Local read verification

Verify a Part without starting ComfyUI:

```powershell
.\tools\python312\python.exe .\src\json_part_read_test.py --ref part:anime_pose_hair_touch@1
```

Expected first line:

```text
[JSON-PART:READ:OK] ref=part:anime_pose_hair_touch@1
```

This verifies resolution and internal positive/negative conversion only. It does not by itself prove the full desktop -> compiler -> ComfyUI generation path.

## 7. Current architecture note

The current target architecture is recorded in:

```text
docs/handoff/LOCAL_RAG_HANDOFF.md
```

FREE generation is being moved toward deterministic JSON Part consumption without Qwen pre-generation interpretation/asset selection. MEMORIELA and LEARN retain local-AI responsibilities.
