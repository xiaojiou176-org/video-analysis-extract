# RSSHub Probe Artifacts

This directory stores long-lived RSSHub probe and tuning evidence retained as performance artifacts.

Rules:

- These files are historical evidence, not runtime cache.
- New probe outputs must not be written to root `data/`.
- Fresh probe runs should land in artifact or runtime evidence paths according to their retention semantics.
- Public/source-first docs must treat these files as sanitized historical probes, not as current provider guarantees.
