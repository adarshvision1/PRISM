# PRISM finalist evidence — 2026-09-28

Evaluated **256 / 4,071 sequence-08 scans**. Sequence 08 remains validation, used for checkpoint/runtime selection. Untouched sequence 11: **64 scans**, runtime only; official test labels are private.

Checkpoint epoch 48, SHA-256 `c503090fde204971934386cebb0ae80ac48a0a1b6993cbfa090f5e03275acecf`. Hardware: NVIDIA GeForce RTX 2060 SUPER.

## What the measurements prove

PRISM uses 57,205 occupied leaves versus 60,501 uniform (5.45% fewer). Leaf storage 2.423 → 2.291 MiB. Grid time 46.29 → 78.01 ms. This is an allocation/accuracy trade-off, not a blanket speed win.

Near common-cell mIoU 80.935% → 80.935%. Model+grid 1.117 FPS. The prototype is an offline demonstrator, not a production real-time autonomous stack.

| Policy | Near common-cell mIoU | Cells | Leaf MiB | Grid ms | Model+grid FPS |
|---|---:|---:|---:|---:|---:|
| uniform | 80.935% | 60,501 | 2.423 | 46.29 | 1.158 |
| distance | 80.935% | 47,333 | 1.896 | 66.33 | 1.132 |
| ground | 80.935% | 55,961 | 2.241 | 75.90 | 1.120 |
| semantic | 80.935% | 48,553 | 1.945 | 67.76 | 1.130 |
| prism | 80.935% | 57,205 | 2.291 | 78.01 | 1.117 |

## Runtime

32 spread validation scans, actual process_frame (both display grids + object clustering + curb ribbons) plus JSON serialization. Input disk read, compressed cache write, HTTP and browser excluded. CPU RSS sampled after frame; GPU allocator peak reset per frame.

Cold first full result: 2759.5 ms, including 447.1 ms checkpoint load.

| Stage/resource | P50 | P95 | P99 | n |
|---|---:|---:|---:|---:|
| preprocess_ms | 61.16 | 83.29 | 85.60 | 32 |
| network_ms | 569.58 | 953.19 | 986.19 | 32 |
| reassemble_ms | 107.88 | 146.96 | 151.69 | 32 |
| inference_ms | 743.96 | 1197.67 | 1223.49 | 32 |
| detection_ms | 298.94 | 375.37 | 382.45 | 32 |
| processing_ms | 1229.95 | 1692.23 | 1727.32 | 32 |
| serialization_ms | 164.09 | 208.27 | 212.49 | 32 |
| total_pipeline_ms | 1392.28 | 1904.66 | 1917.75 | 32 |
| grid_ms | 75.56 | 98.94 | 102.83 | 32 |
| uniform_grid_ms | 46.82 | 61.26 | 64.58 | 32 |
| rss_mb | 1375.31 | 1402.12 | 1403.51 | 32 |
| gpu_peak_allocated_mb | 524.41 | 524.41 | 524.41 | 32 |
| gpu_peak_reserved_mb | 670.00 | 670.00 | 670.00 | 32 |

## Definitions and limitations

Own-cell GT: majority of nonignored SemanticKITTI GT labels inside each predicted grid leaf. Common-cell GT: majority label on fixed occupied 5cm support. The latter prevents changing evaluation units from gaming the score. Confusion matrices include an unknown-prediction column.

Elevation MAE/RMSE/P95 compare adaptive means with the raw-scan GT 5cm leaf means on common support; reported summaries macro-average per-frame error statistics. This measures projection/compression error, not independently surveyed terrain accuracy. Min/max errors are in per-frame JSON. Occupancy is observed obstacle-semantic IoU; unobserved space is never scored as free.

Boundary distance is a mixed-GT-cell edge proxy, not annotated curb accuracy. No surveyed curb heights are available. Temporal overlap is ego-compensated nearest-cell matching for consecutive frames only. It is not tracking precision, ID switches or velocity error.

CIs use paired circular moving-block bootstrap (16 evaluated frames, 1,000 draws), accounting partly for temporal correlation. They do not establish independent-sequence generalization. Composition strata are measured GT proportions; urban/highway/residential/weather tags are not invented.

Tracking roadmap: annotate/validate associations against instance IDs with dynamic/static motion GT, implement lifecycle-managed tracks and odometry propagation, then score association precision/recall, ID switches and velocity error. Current boxes are Dynamic-object semantic segmentation, not certified motion tracks.

## UI and deployment

The four views share frame and camera. The voxel pane renders occupied surfaces from an actually allocated 20×20×4m dense 5cm crop; outer space is not claimed as allocated. Adaptive full-cloud counts and leaf bytes are measured independently of rendering caps. Confidence, variance, height span, GT-error and observed/unobserved modes use real arrays. Three challenge crops show prediction and GT side-by-side.

The focus heading now travels browser → validated API → both full/local PRISM builds. Ellipse math matches the engine. A turn response audit is included in the JSON. Browser response shows end-to-end request time, separate from measured grid time.

Trained model download includes two fixed-N TorchScript exports (4096,1024), trained checkpoint, source, class YAML, feature contract and numerical parity results. Batch 1 and 2 parity tested on RTX 2060 Super; no TensorRT/Jetson performance certification.

All evidence: `data/grid_evidence.json`; deployment checks: `data/deployment/manifest.json`.
