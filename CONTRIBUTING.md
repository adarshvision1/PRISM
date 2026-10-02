# Contributing to PRISM

Changes should preserve the distinction between semantic class, measured motion, recorded playback and fresh inference. Keep benchmark claims tied to their checkpoint, scan set, hardware and evaluated stages.

1. Use a focused branch and explain the behavior being changed.
2. Run `python scripts/doctor.py` and the relevant tests. For model or grid changes, run the appropriate evaluation and attach the measured before/after scope.
3. Update documentation when inputs, limits, checkpoint selection or metric definitions change.
4. Keep raw datasets, generated exports, uploaded scans and credentials out of commits.

For a first review, follow [local setup](docs/quickstart.md) and [architecture](docs/architecture.md). Please describe any expected performance trade-off in the pull request.
