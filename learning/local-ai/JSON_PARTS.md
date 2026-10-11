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

## 2. Document shape

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

## 3. Generation reuse

The first implemented reusable payload is `payload.generation`:

- `positive`: appended to the positive generation prompt.
- `negative`: appended to the negative generation prompt.

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

Other payload sections may be added later for ControlNet, LoRA, character identity, outfit adapters, backgrounds, or camera controls. They must be versioned and explicitly implemented before the runtime may use them.

## 4. Storage

Accepted local files:

```text
learning/local-ai/store/json-parts/<part_id>.v<version>.json
```

Example:

```text
learning/local-ai/store/json-parts/pose.hair-touch.v1.json
```

Oracle table `LR_JSON_PART` is the searchable index/mirror for accepted parts. The previous AI-development schema is not migrated or reused.
