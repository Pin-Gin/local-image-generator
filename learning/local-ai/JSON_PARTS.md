# Reusable JSON Parts

## 1. Naming

A reusable Part has a stable `part_id` and integer `version`.

```text
part:<part_id>@<version>
```

Rules:

- `part_id`: lowercase ASCII, digits, `.`, `_`, `-`; no path separators.
- `version`: positive integer.
- An accepted payload is immutable for that version. Changed content creates a new version.
- FREE generation stores/resolves exact Part refs; it does not ask Qwen to reinterpret them.

## 2. FREE production roles

The user-facing FREE contract has at most five content Part slots:

```text
character_body
outfit_prop
expression_face
camera_composition
background_scene
```

`Rendering` and `Lineart` are separate profile authorities and are not members of these five Part slots.

The lower-level Part loader may still read older/manual Part types for compatibility, but the new FREE staging/acceptance sync gate accepts only the five production roles above unless an explicit maintenance command opts out.

## 3. Canonical candidate shape

Local AI should emit canonical application-managed candidates with `status: staging`.

```json
{
  "schema_version": 1,
  "document_type": "local-rag/json-part",
  "part_id": "body.example",
  "version": 1,
  "part_type": "character_body",
  "name": "Example body definition",
  "status": "staging",
  "aliases": [],
  "tags": ["free"],
  "payload": {
    "generation": {
      "positive": "generation-ready positive representation",
      "negative": "generation-ready negative representation"
    },
    "structured": {
      "any": "additional detailed structured data may remain here"
    }
  },
  "provenance": {
    "source_type": "local-ai-learning",
    "source_ref": ""
  }
}
```

The local AI must not set `accepted` itself. Acceptance is a separate application/user action.

## 4. Storage lifecycle

```text
local AI / authored candidate
-> learning/local-ai/store/staging/
-> structural + role validation
-> SHA256 gate
-> explicit acceptance
-> learning/local-ai/store/json-parts/
-> FREE exact Part reference
```

Accepted local files:

```text
learning/local-ai/store/json-parts/<part_id>.v<version>.json
```

Staging files:

```text
learning/local-ai/store/staging/<part_id>.v<version>.json
```

Acceptance receipts are runtime-local audit records under:

```text
learning/local-ai/store/receipts/
```

The receipts directory is runtime state and is ignored by Git.

## 5. Mechanical sync / integrity guarantee

`src/json_part_sync.py` is the canonical staging/acceptance utility for the new FREE content workflow.

It validates mechanically rather than semantically rewriting content:

```text
valid canonical JSON Part
schema/document identity
part_id/version/filename identity
status
FREE role / part_type
staging SHA256
payload semantic SHA256
accepted target collision/version safety
```

Acceptance changes only:

```text
status: staging -> accepted
```

All other parsed document content must have the same semantic SHA256 before/after acceptance. The payload has its own SHA256 check and the receipt records staging/accepted/payload hashes.

If an accepted `<part_id>@<version>` already exists, the sync utility rejects overwrite. Create a new version instead.

### Stage a local-AI JSON file

```powershell
.\tools\python312\python.exe .\src\json_part_sync.py stage-file "C:\path\candidate.json"
```

The output includes:

```text
[JSON-SYNC:STAGE:OK]
[JSON-SYNC:STAGE:SHA256]
[JSON-SYNC:PAYLOAD:SHA256]
```

### Validate without printing payload content

```powershell
.\tools\python312\python.exe .\src\json_part_sync.py validate --ref part:<part_id>@<version>
```

This prints identity/role/hashes only. It does not print the semantic payload.

### Accept with a hash gate

Use the SHA returned by staging/validation:

```powershell
.\tools\python312\python.exe .\src\json_part_sync.py accept `
  --ref part:<part_id>@<version> `
  --expected-sha256 <STAGING_SHA256>
```

Successful acceptance includes:

```text
[JSON-SYNC:ACCEPT:OK]
[JSON-SYNC:SEMANTIC-PRESERVATION:OK] status-only change
```

This CLI currently performs local file-store promotion. Oracle/UI integration of this exact hash-gated acceptance path is a separate next step.

## 6. Manual structured JSON compatibility

Files manually placed in the accepted `json-parts` directory may still use the older simple structured JSON shape without the canonical wrapper.

For this compatibility path:

- identity/version comes from filename + requested ref;
- optional `file_name` must match the canonical filename;
- UTF-8 BOM and a whole-file Markdown JSON fence are accepted;
- the source file is never rewritten by the read path;
- without an explicit top-level `positive`, nested scalar content is linearized into dotted hierarchy paths;
- scalar values, traversal order and duplicate leaves are retained;
- optional `positive`, `negative`, or `negative_prompt` override/define generation strings;
- it is generation-eligible because it physically lives in the accepted store;
- it is not automatically mirrored into Oracle.

This is compatibility/read behavior. New local-AI-managed FREE Parts should use the canonical staging -> accept flow above.

## 7. Generation reuse

Canonical Parts expose `payload.generation.positive/negative` to the existing Part loader. FREE production will ultimately bind exact refs to the five named slots defined in `schemas/free_generation_input.schema.json`.

The lower-level historical `parts: []` mechanism remains for compatibility/internal use, but the production UI must not become an unlimited unordered Part list.

## 8. Verification

Sync integrity test:

```powershell
.\tools\python312\python.exe .\tests\integration\json_part_sync_test.py
```

The expected final marker is:

```text
[JSON-SYNC:TEST:OK]
```

Existing accepted-Part read verification remains available through the current JSON Part read test until that historical test is migrated from `src/`.

## 9. Architecture authority

Current continuation decisions are in:

```text
docs/handoff/LOCAL_RAG_HANDOFF.md
```

FREE generation remains deterministic/no-Qwen. MEMORIELA and LEARN retain their separate AI responsibilities.
