# Tests

This directory owns repeatable validation and tracked diagnostic fixtures.

Current grouping:

```text
tests/
├─ capabilities/
│  ├─ ipadapter_capability_test.py
│  └─ pose_control_capability_test.py
├─ fixtures/
│  └─ json-parts/
│     └─ diagnostic.authority_probe.v1.json
├─ unit/          # target destination as tests are migrated
└─ integration/   # target destination as tests are migrated
```

The repository predates this separation, so several verified test scripts still live under `src/`. Migrate them incrementally only when import paths and documented verification commands are updated.

Rules:

- production runtime modules belong in `src/`;
- diagnostic experiments belong in `experiments/`;
- repeatable validation belongs in `tests/`;
- developer diagnostic JSON belongs in `tests/fixtures/`, not the accepted user JSON Part store;
- migration must preserve execution with `tools/python312/python.exe`.
