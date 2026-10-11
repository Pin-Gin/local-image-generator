# Local AI persistent store

This directory defines the persistent storage contract for content accepted from the local AI workflow.

## Runtime storage root

```text
learning/local-ai/store/
  json-parts/   reusable versioned JSON parts
  knowledge/    accepted structured knowledge documents
  sources/      source metadata / provenance records
  staging/      temporary candidates that are not yet accepted
```

`store/` is machine-local runtime data and is intentionally ignored by Git except for `.gitkeep` files.

Oracle is used as the searchable/indexed knowledge database. The file store remains the durable local source for reusable JSON parts and source artifacts. A database row must not be treated as evidence that model training occurred; it records accepted knowledge/assets only.

## JSON part reference

Canonical reference syntax:

```text
part:<part_id>@<version>
```

Example:

```text
part:pose.hair-touch@1
```

Generation JSON may reuse parts with:

```json
{
  "positive": "anime woman standing outdoors",
  "parts": [
    "part:pose.hair-touch@1",
    "part:camera.three-quarter@2"
  ]
}
```

The runtime always resolves an exact version. There is no implicit `latest` in generation manifests, so a past generation remains reproducible.

See `JSON_PARTS.md` and `schemas/json_part.schema.json` for the contract.
