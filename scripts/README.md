# Operational scripts

This directory is the destination for setup, maintenance and migration scripts as root-level PowerShell helpers are safely consolidated.

Current root scripts were created incrementally and some compute repository paths from `$MyInvocation.MyCommand.Path`; moving them blindly can break verified behavior. Therefore migration must be explicit, one script at a time, with call sites updated.

Target grouping:

```text
scripts/
├─ setup/         # install/configure ComfyUI-adjacent and local runtimes
├─ maintenance/   # status/repair/verification
├─ migration/     # one-time repository/state migrations
└─ training/      # rendering/LoRA training wrappers
```

Until a script is migrated, its current root path remains authoritative.

Persistent state must never be deleted as a side effect of source-layout cleanup.