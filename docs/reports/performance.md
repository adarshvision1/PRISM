# PRISM measured performance · 2026-09-27

> **Checkpoint scope:** this performance report measures epoch 30. The current best weights are epoch 36 (78.60% validation-block mIoU); current-checkpoint runtime has not yet been remeasured. Do not attribute the FPS/latency values below to epoch 36.

Hardware: NVIDIA GeForce RTX 2060 SUPER. PyTorch 2.14.0+cu126.
Checkpoint: epoch 30, SHA-256 `76e0e2462fae50175f0aaa9f921685cc765dd8ec4525bbf75c0622987f180f51`.
Runtime: 4096 near-block samples / 1024 far-block samples, batch 16. Far reduction begins only when a whole 10 m block lies beyond 25 m.

## Final confirmation

512 available scans of 4,071 sequence-08 frames; 10 fixed contiguous temporal intervals, sampled coverage (not full-sequence evaluation).

| Policy | Processing FPS | Grid ms | Total measured ms | Mean active cells | mIoU |
|---|---:|---:|---:|---:|---:|
| uniform | 2.220 | 42.34 | 450.44 | 60,553 | 79.73% |
| distance | 2.132 | 60.85 | 468.95 | 47,375 | 79.51% |
| ground | 2.092 | 69.94 | 478.04 | 56,017 | 79.74% |
| semantic | 2.126 | 62.18 | 470.29 | 48,564 | 79.73% |
| prism | 2.081 | 72.44 | 480.54 | 57,269 | 79.73% |

Shared preprocessing + network + reassembly: **408.10 ms/scan**. Peak process RSS: 1386.6 MiB; peak GPU allocated memory: 524.4 MiB.

These processing rates exclude detection, disk I/O, JSON caching and browser drawing. The inference console separately reports elapsed job-wall throughput, which includes those backend costs. Interactive grid Hz excludes neural processing; cached replay is not an inference benchmark.

## Before and after

The previous 512-scan PointNet++ result was 1.243 FPS, 804.61 ms/scan and 74.86% mIoU. The updated checkpoint/runtime measures 2.081 FPS, 480.54 ms/scan and 79.73% mIoU on the same locally available sequence-08 scans. Both training and runtime changed; this before/after comparison is not a causal isolation of a single optimization.

The 30 FPS target requires 33.33 ms/frame. The measured PRISM path still takes 14.4 times that budget before detection/rendering. **30 FPS has not been achieved.**

## Controlled runtime candidate comparison

32 spread validation scans, shared checkpoint per sweep. Fastest measured profile with at most 1.0 percentage point overall mIoU loss and no more than 1.0 point recall loss for any class in 0 to 10 m, compared with 4096-point full-input batch-8 reference. This explicitly protects near-field class recall; exploratory sequence-08 validation, not an independent test.

| Candidate | Near / far samples | FPS | mIoU | Near dynamic-class recall | Mean network points | Preprocess ms | Network ms | Reassembly ms |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| reference | 4096 / 4096 | 1.237 | 81.04% | 89.44% | 386,944 | 82.84 | 515.54 | 132.44 |
| batch16 | 4096 / 4096 | 1.400 | 81.04% | 89.43% | 386,944 | 83.00 | 420.45 | 130.18 |
| foveated1024 | 4096 / 1024 | 1.914 | 80.47% | 89.86% | 179,968 | 55.54 | 285.87 | 101.62 |
| compact2048 | 2048 / 1024 | 2.155 | 80.27% | 87.22% | 124,480 | 48.01 | 249.54 | 88.27 |

Recommended measured candidate: **foveated1024**. Full frame-level data: `data/performance_trials.json`.

Implemented changes: reduced point tensors before neural execution; batch-size comparison; skipped temporal residual construction for a checkpoint not trained on residuals; scalar block grouping keys; elementwise ground-plane evaluation. Full-cloud predictions are reassembled after inference.

No TensorRT, C++ grid rewrite or target-Jetson result is claimed. The supplied DRDO paper measures YOLOv8l camera processing on T4; it is method inspiration, not a directly comparable baseline.

## Storage comparison

First evaluated scan, identical 20 × 20 × 4 m domain: allocated dense 5 cm uint8 3D occupancy = 12,800,000 bytes; sparse occupied 3D int64 keys = 275,080 bytes; PRISM 2.5D leaves = 1,227,870 bytes. These representations carry different attributes. PRISM is not claimed to beat sparse 3D keys.

## Training evidence

1,185 paired training scans; 144,856,208 finite input points validated; 10,000 training blocks. The original 600 validation blocks were preserved. Best validation-block mIoU: 77.74%. Block validation and full-scan mIoU are different measurements.
Sequence 08 selected weights and runtime settings. This is held-out-from-gradient-training validation, not an untouched test set or full 4,071-frame evaluation.
