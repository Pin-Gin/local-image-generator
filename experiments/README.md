# Experiments

Diagnostic scripts live here instead of `src/`.

```text
experiments/
├─ active/    # current diagnostic paths still used for architecture/quality decisions
└─ archive/   # superseded diagnostics kept only when their source is still useful
```

Rules:

- Experiments are not production runtime entry points.
- A successful experiment does not automatically become architecture.
- Conclusions that matter must be recorded in `docs/handoff/LOCAL_RAG_HANDOFF.md`.
- Once an experiment is superseded and its conclusion is captured, it may be archived or removed; Git history remains the final source archive.
- Production implementations belong in `src/` only after the behavior and ownership model are accepted.
