# RSSHub Probe Artifacts

This directory stores public-safe RSSHub performance evidence only.

Rules:

- Raw probe TSV files are forbidden in the tracked public tree.
- Only sanitized or synthetic summaries may remain here.
- New probe outputs must not be written to root `data/`.
- Fresh probe runs should land in runtime evidence or private local storage according to their retention semantics.
- Public/source-first docs must treat the retained sample here as a sanitized explanatory sample, not as current provider guarantees.
