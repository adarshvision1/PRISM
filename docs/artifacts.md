# Repository and artifact policy

**Tracked:** source code, tests, frontend, compact recorded demo frames, evidence reports, JSON measurements, manifests and selected best-validation checkpoints.

**Kept outside Git:** full SemanticKITTI scans and labels, prepared training caches, uploaded jobs, previous epoch checkpoints, generated TorchScript bundles, virtual environments and local recovery snapshots. The `.gitignore` and `.dockerignore` enforce most of these boundaries.

SemanticKITTI data must be obtained under its official terms. Source-code notices embedded in adapted third-party components remain in place. The repository does not assign a blanket license to data, model weights and all code.

For each published measurement, record checkpoint identity, sequence and scan count, evaluation unit, hardware, pipeline stages and exclusions. Saved results are evidence; they are not substitutes for an independent test set. See [measured evidence](evidence.md) and the [data inventory](../data/MANIFEST.md).
