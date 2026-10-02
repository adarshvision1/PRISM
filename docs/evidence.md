# Measured evidence and boundaries

PRISM has several experiments with different checkpoints, scan counts and pipeline stages. Use the matching report for each claim.

| Claim | Scope | Primary record |
|---|---|
| PointNet++ MSG 79.00% block mIoU, epoch 48 | 600 sequence-08 validation blocks. Checkpoint selected using validation. | [`data/training_run.json`](../data/training_run.json) |
| PointNeXt-S 78.40% block mIoU, epoch 21 | Same prepared validation block count. | [`data/models/pointnext_s/training_run.json`](../data/models/pointnext_s/training_run.json) |
| Near common-cell mIoU 80.935% for uniform and PRISM; 5.45% fewer occupied leaves | 256 of 4,071 sequence-08 validation scans, PointNet++ epoch 48, RTX 2060 SUPER. | [`data/grid_evidence.json`](../data/grid_evidence.json), [`finalist-evidence.md`](reports/finalist-evidence.md) |
| Leaf storage 2.423 to 2.291 MiB and grid construction 46.29 to 78.01 ms | Same 256-scan report; adaptive grid reduces storage but takes longer to build. | [`finalist-evidence.md`](reports/finalist-evidence.md) |
| Network input 386,944 to 179,968 points; model-plus-grid 1.237 to 1.914 frames/s | Separate controlled 32-scan sampling comparison; mIoU decreases from 81.04% to 80.47%. | [`data/performance_trials.json`](../data/performance_trials.json), [`performance.md`](reports/performance.md) |
| Full result latency P50 1,392 ms | Separate 32-scan PointNet++ epoch-48 runtime sample. Includes proposals, two grids and JSON serialization; excludes disk, HTTP and browser. | [`finalist-evidence.md`](reports/finalist-evidence.md), [`data/runtime_audit.json`](../data/runtime_audit.json) |

**Evaluation interpretation:** sequence 08 is excluded from gradient training but used for validation, model selection and parameter choices. These are not independent test-set results. Common-cell mIoU, validation block mIoU and point-level mIoU measure different units. Replay speed is not inference speed. Grid-only time is not full backend latency.

The broader 512-scan epoch-30 study is historical and remains in [`performance.md`](reports/performance.md). Its runtime and checkpoint must not be attributed to the selected epoch-48 model.

The hosted AWS CPU demo is for access and functional inspection. GPU measurements above were taken on the development RTX 2060 SUPER. The cloud instance does not establish GPU or edge-device performance.
