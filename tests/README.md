# Tests

This directory is the destination for test/capability/integration scripts as they are migrated out of `src/`.

Current repository history predates this separation, so several verified test scripts still live under `src/`. Do not mass-move them without updating import paths and documented verification commands.

Target grouping:

```text
tests/
├─ unit/
├─ integration/
├─ capabilities/
└─ fixtures/
```

Rules:

- production runtime modules belong in `src/`;
- diagnostic experiments belong in `experiments/`;
- repeatable validation belongs in `tests/`;
- migration must preserve the ability to run tests with the project-local `tools/python312/python.exe` runtime.
