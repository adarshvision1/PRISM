# PRISM development history

This is a reconstruction of **when the project work happened**, using retained project records. It is not a reconstruction of original Git commits. Exact dates for work before 26 September are not recoverable from this checkout.

| Period | Development milestone | Evidence in this repository |
|---|---|---|
| Mid-September 2026 | The team began the LiDAR segmentation and adaptive mapping prototype. The precise day and order of early edits are not recorded here. | Team account of the work; the [26 September progress entry](../PROGRESS_LOG.md) describes the PointNet++ application, grid, upload jobs and dashboard as already implemented. |
| By 26 September | Working PointNet++ prototype, initial short training run and 512-scan sequence-08 benchmark. Legacy components were audited and the UI and data scope were clarified. | [Progress log](../PROGRESS_LOG.md), [historical point-cloud benchmark](../data/pointnet_benchmark.json). |
| 26 September | Recorded a verified snapshot, removed obsolete components, migrated tests and built the interactive comparison and processing views. | [Progress log](../PROGRESS_LOG.md) under “Revised scope”; [cleanup manifest](../data/cleanup_manifest.json). |
| 27 September | Expanded validated SemanticKITTI training inputs, prepared blocks and measured the first controlled runtime candidates. Refined the dashboard and introduced the PointNeXt-S model path. | [Data inventory](../data/MANIFEST.md), [performance report](reports/performance.md), [progress log](../PROGRESS_LOG.md). |
| 28 September | Completed the selected-checkpoint evidence pass, dual-model comparison workflow and evaluator-oriented interface revisions. The 256-scan grid analysis documents both the storage benefit and grid-time cost. | [Finalist evidence](reports/finalist-evidence.md), [training run](../data/training_run.json), [PointNeXt-S training run](../data/models/pointnext_s/training_run.json), [progress log](../PROGRESS_LOG.md). |
| 28 September | Created the first Git snapshot of the prototype. Earlier local work was imported together, so the Git history does not contain one original commit per milestone. | Git commit `caeaa49`. |
| 2 October | Deployed the CPU-hosted reviewer prototype on AWS and documented the application for SIH reviewers. Recorded GPU replay and fresh cloud CPU inference are identified separately. | [Hosting overview](hosting.md), Git commit `ea78a44`. |

The dates above refer to project activity where records support it. Git commit dates continue to show when snapshots were actually committed. Benchmark values and checkpoint provenance are in [measured evidence](evidence.md); this timeline does not add new performance claims.
