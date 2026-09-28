# PRISM progress log

Read this file first when continuing the project. Workspace: `C:\Users\ADMIN\OneDrive\Desktop\PRISM`.

## 2026-09-26 — Context carried into the new execution brief

Before the latest phased brief, work implemented an offline PointNet++ application under the preceding SemanticKITTI-focused specification: adapted MSG network, height attention, training/checkpoint configuration, adaptive NumPy grid, detections, upload jobs and a local dashboard. CUDA PyTorch is installed for the RTX 2060 SUPER.

Actual training used 5,962 training blocks and 600 validation blocks, completed 12 epochs in about 419 seconds, and retained epoch 12 as best validation-block mIoU (71.55%). These are a short training run's results, not full convergence or IDD training.

The 512-scan sequence-08 benchmark completed before the subsequent pause could interrupt it. It reports full PRISM 1.243 FPS and 74.863% four-class mIoU; its timing excludes detection, serialization, I/O and rendering. Preserve `data/pointnet_benchmark.json`, training logs and checkpoint. Do not present playback FPS as inference FPS.

A previous attempt to archive obsolete files stopped before any source deletion. `docs/legacy-v1.zip` contains only one file and is not an adequate rollback snapshot. No Git repository is present.

## 2026-09-26 — Phase 1: read-only audit completed; awaiting review

### Work completed

- Inspected architecture, source references, routes, dependencies, tests, experiment evidence, supplied-paper extracts and IDD archive inventories.
- Produced `PROJECT_AUDIT.md` with the protected-file map, active/dead/redundant/broken status table, explicit phone/MQTT reference checklist, dataset alignment findings, performance baseline and next-phase blockers.
- Confirmed latest instructions supersede the previous SemanticKITTI-only data scope and retained Record3D upload feature. IDD is now requested; all iPhone paths, including Record3D uploads, are removal targets after review.
- Ran the full test suite without cache/bytecode writes. It fails at collection on three legacy-interface imports. Earlier 20-test focused success is recorded separately and does not satisfy Phase 2's full-suite gate.
- Inspected IDD Primary (13,543 images) and Supplement (8,948 LiDAR arrays). All three scenes contain timestamp tables; frame numbers do not align directly. Candidate scene/timestamp pairing must be validated before any curation.
- Checked official IIITH and NIST sources to distinguish IDD Multimodal from labeled datasets and correct the proposed orthogonal-array design.

### Changes and removals

Only `PROJECT_AUDIT.md` and this progress log were written for Phase 1. No application source, dependencies, models, datasets or fixtures were changed or removed during the audit. No Phase 2 cleanup, Phase 3 extraction, new training, new DoE, performance rewrite or new UI work has started under this brief.

### Findings that remain open

1. **IDD supervision:** no segmentation-label/calibration files were found in the archive inventory. Representative NPY files are float64 Nx5; extra channels resemble ring and reflectance but need source confirmation. The current point-label trainer cannot train on raw aligned arrays alone.
2. **Alignment:** preliminary nearest-camera matching finds 8,890 of 8,948 LiDAR frames within an exploratory 35 ms threshold. No tolerance has been adopted and no frames dropped. Check one-to-one pairing, clock offsets, calibration, duplicates, corrupt files and split leakage before deriving a final manifest.
3. **Tests/cleanup:** three collection errors and stale API tests; phone/MQTT code remains, including the still-active Record3D upload branch. Preserve useful grid/planner test coverage while migrating obsolete imports.
4. **Performance:** PRISM takes 804.61 ms/frame under the 512-scan evaluator's partial pipeline accounting, versus 33.33 ms for 30 FPS. All blocks are processed by the neural network before foveation. Detection and serialization add further work.
5. **DoE:** seven three-level factors need a suitable L18/L27 design, not the suggested L8/L9/L16. Training factors require fresh controlled training; the existing three-radius sensitivity check is not Taguchi evidence.
6. **Citation:** exact DRDO §4.2 and 32.15 FPS paper has not been identified in the supplied PDFs. Do not attribute standards/results without it.
7. **Semantics:** four macro classes cannot support specific pedestrian/pothole softmax labels; geometric hazard proposals and semantic object classes must be distinguished from verified motion and supervised detections.
8. **Distribution:** old offline ZIP, manifest and packaging scripts are stale. A clean-start offline distribution test is required after cleanup.

### Documented assumptions and protection rules

- Treat the latest explicit “stop for review” Phase 1 gate as controlling; do not infer approval to delete from the general request to finish all phases.
- Keep existing labeled SemanticKITTI data, best weights and measured outputs while resolving IDD supervision. New scope does not authorize erasing working evidence.
- Flag disconnected planner/ROS tooling and unused upstream reference sources rather than automatically deleting them; navigation and license provenance remain relevant.
- Public asset-download URLs are build tooling, not application AWS MQTT dependencies.
- Archive originals and verify recoverability before destructive cleanup or dataset curation. The current partial ZIP is insufficient.

### Resume point

Present the audit and stop for review. On authorization to continue Phase 2: create a verified snapshot, apply the audited cleanup/migrations, run the complete suite and record a `CLEANUP_SUMMARY.md`. Do not start Phase 3 until that gate passes. No later phase is marked complete by work done under the previous brief.


## 2026-09-26 — Revised scope: UI first, SemanticKITTI, cleanup authorized

The user explicitly authorized cleanup, dropped IDD implementation, prioritized the specified UI before further data/performance gates, and requested more SemanticKITTI data plus fine-tuning. This supersedes the earlier phase-order hold. IDD source archives remain untouched and excluded from runtime/training/package inputs.

Saved and byte-verified snapshots/before-ui-cleanup-20260926.zip (121 files, including model weights). Removed 35 legacy files only after byte-verifying snapshots/removed-legacy-20260926.zip. Archived streaming, telemetry, obsolete backend/scripts/assets and Record3D fixtures; migrated useful API/model/planner tests. The complete suite passed 26 tests. No claim of a completed Taguchi study.

Implemented dark glass benchmark modes, shared cameras, actual full-cloud grid rebuild endpoint, bounded prediction cache, dense 3D local-volume comparison, inference console, real presets, confidence filtering, detection feed and run evidence summary. New routes /benchmark and /launch are direct-loadable. Browser review is ongoing. Processing rate, grid-only rate and cached replay are separately labeled.

Supplied 21132.pdf is Kaur et al., Defence Science Journal 76(4), DOI 10.14429/dsj.21132. Section 4.2 describes Taguchi tuning for YOLOv8l; 32.15 FPS is camera-image processing on Tesla T4, not a LiDAR baseline or a PointNet++ result.

Additional official training scans are downloading with hashes; sequence 08 remains validation only. Inference experiments compare batch sizes and distance-conditioned point budgets with explicit near-field accuracy constraints. No performance candidate is adopted before measurement.


## 2026-09-27 — Resumed after usage limit; light Aero theme

User requested continuation and a washed light glassmorphism aesthetic without changing functionality. Added aero.css, keeping all HTML controls and all JavaScript behavior identical after normalizing only visual color literals; data/theme_verification.json records both checks passing. Light off-white/blue/green surfaces and muted orange preserve the same benchmark modes, cameras, replay, uploads and confidence controls. Improved text contrast after browser inspection.

Acquisition finished: 1,185 paired training scans across official training sequences. All pairs passed finite-coordinate, binary-shape and point/label-count validation (144,856,208 points). Generated 10,000 training blocks; preserved the exact 600 validation blocks. Fine-tuning is running from the previous best at lr=0.0003, batch=16 with AMP, up to 12 additional epochs / 25 minutes. Best checkpoint retention remains active.

The 32-frame runtime trial selected compact2048 (2,048 near / 1,024 far samples, batch 16) with an exploratory 2.34 FPS versus 1.31 reference and no aggregate accuracy loss. Full confirmation is pending training completion; no 30 FPS claim.

Main server was restarted on port 8000 with current routes. UI browser checks found no console errors; benchmark loaded eight actual cached frames. Legacy code/evidence/weights are recoverably archived, not mixed into current claims. Active README, architecture, attribution, walkthrough and future-work documentation were rewritten.

Fine-tuning completed 12 additional epochs (24 total logged) in 725.14 seconds. Best epoch 22 achieved 77.0396% validation-block mIoU; epoch 24 was lower and did not replace it. Post-training runtime selection and 512-scan confirmation are next.


## 2026-09-27 — Finalist evidence and presentation pass

Latest user request adds grid-level validation, synchronized four-panel views, real heading propagation, distributional runtime evidence and a model download. Before changes, snapshotted source and root evidence to snapshots/finalist-polish-before.zip. User-permitted cosmetic metrics/mocks are not used as measured evidence; missing capabilities remain explicitly unvalidated.

Implemented browser → validated heading field → full/local grid propagation. The rendered ellipse now uses the same rotation, offset and elongation formulas as the backend; a pending rebuild keeps the last completed geometry. Added a regression for actual heading-dependent allocation. Replaced a tiny 2D BLAS operation with equivalent elementwise arithmetic.

Five policies now have distinct definitions: uniform, distance, height-aware, semantic-aware, full PRISM. The historical four-policy report retains its original definitions. The new evaluation separately reports own-leaf GT votes and common 5cm occupied-cell support, per-class metrics and confusion matrices, raw-scan elevation compression errors, observed obstacle-semantic IoU, histograms, boundary proxy, refinement counts and temporal overlap proxies. No ray-cast free-space or surveyed curb truth is claimed.

A frozen selection of 924 paired sequence-08 scans is being evaluated (additional downloads continue independently). All official sequence-11 scans are being acquired for untouched runtime-only evaluation; its GT is private. No available weather/lighting or verified urban/highway/residential annotations were found; composition strata are labeled as such. Paired confidence intervals use circular moving-block bootstrap, not independent-frame claims.

New light glass dashboard retains prior routes/jobs/controls and adds four linked views, allocation bars, focus-heading slider, actual changed-leaf count, confidence/variance/height-span/GT-error/unobserved modes and three GT-audited challenge crops. Dark blue-grey map backgrounds improve contrast while outer surfaces stay washed off-white/blue/green. Centimetre geometry remains metrically scaled; zoom reveals details. Rendering caps are disclosed.

TorchScript exports for 4096/1024 points pass exact FP32 logit parity at batch 1 and 2 on RTX 2060 Super. The download contains the checkpoint, tensor/feature contract and preprocessing source. TensorRT/Jetson validation remains unimplemented. Runtime is explicitly an offline demonstrator, not a production real-time autonomous system.

Initial complete suite: 30 tests passed. Full evidence run, production-runtime distribution audit, upload regressions and final packaging are in progress.

## 2026-09-27 — Current checkpoint, deployment and problem-fit update

Supersedes the earlier runtime-candidate note above: a corrected selection rule now protects all four near-field class recalls within one percentage point. Under that safety-oriented rule, foveated1024 is the fastest eligible candidate; compact2048 is rejected because near dynamic-class recall drops to 87.22% from 89.44%. The active config remains 4,096 near / 1,024 wholly-far points, batch 16.

Fine-tuning resumed from best epoch 22 and improved held-out block mIoU from 77.04% to 77.74% at epoch 30. Epochs 31–32 did not replace the best checkpoint. Fixed duplicate epoch logging on resume and added regression coverage. The latest checkpoint hash is shared by the training record, benchmark, demo manifest, grid evaluation and model bundle.

Refreshed benchmark: 512 spread sequence-08 scans at 79.73% point mIoU; cell-level grid report: 256 spread scans, with equal 80.81% near common-cell mIoU, 5.44% fewer cells for PRISM, but slower grid construction (70.80 vs 42.11 ms). The dashboard now emphasizes 93.10% near and 7.87% horizon dynamic-semantic cell recall, with evaluated cell counts and a clear no-tracking caveat. Full process total latency is 990/1,157/1,200 ms at P50/P95/P99 over 32 scans. Sequence 11 is runtime-only, currently 64 consecutive scans.

Rebuilt CPU-traced fixed-shape TorchScript artifacts with exact CPU/CUDA batch-1/2 parity. ONNX/TensorRT/Jetson remains unvalidated; the legacy ONNX probe did not meet logit parity. Added deployment and SIH problem-fit docs, updated generated evidence reports, and preserved the existing modular layout and recoverable snapshots. Full suite: 33 tests passed; JS syntax and modified Python compilation passed.

## 2026-09-27 — Expanded SemanticKITTI fine-tune preparation

User requested more official training data, inference optimization toward 30 FPS, and a three-hour local training command rather than waiting in chat. Download completed with 3,839 paired scans / 468,885,444 points across the 10 official training sequences; validation sequence 08 was excluded. The resumable source manifest records SHA-256 for downloaded members and reports 5,308 newly added files.

Training now accepts an explicit block-cache directory and uses pinned host batches/nonblocking CUDA transfers without adding Windows multiprocessing fragility. `scripts/prepare_blocks.py` can prepare an expanded cache separately while copying the existing 600 sequence-08 validation blocks exactly; it writes into a `.building` staging folder and only promotes on completion, protecting the current cache. The initial launcher was set to 180 minutes; after the user's run was interrupted, it was replaced by `TRAIN_PRISM_30M.ps1` with a 30-minute cap. `docs/TRAINING_30M.md` contains the current commands and evidence-refresh steps.

Prepared and validated 20,000 training blocks plus the unchanged 600 sequence-08 validation blocks; 32 random blocks passed loader shape/finiteness/label checks. Windows denied `Path.replace` for the completed staging directory, so it was safely promoted with `Path.rename`; the builder now uses this tested Windows-compatible promotion. The RTX 2060 Super is visible with PyTorch CUDA, but this environment has no Triton package or discovered CUDA compiler. Existing measured end-to-end performance remains about 2 FPS; the PointNet++ neighborhood path dominates over grid construction. A C++ grid-only rewrite cannot justify a 30 FPS claim, so no unmeasured native rewrite or TensorRT claim was introduced. ONNX/TensorRT is documented as the NVIDIA edge deployment target only after parity and target-device profiling; verified TorchScript remains the current portable artifact. Modified Python files compile and the full suite passes (33 tests, 1 upstream deprecation warning).

## 2026-09-27 — Graceful stop and 30-minute fine-tune

User interrupted the 180-minute run with Ctrl+C during the next epoch. Five complete epochs (33–37) were logged; the best checkpoint correctly remained epoch 36 at 78.6044% validation-block mIoU, while epoch 37 was lower. The traceback was an unhandled interrupt, not a model/data exception; a trailing `\` was also entered at the PowerShell prompt and is not part of any command. Repaired `training_run.json` to record the interruption and verified the checkpoint metadata.

Changed the launcher to `TRAIN_PRISM_30M.ps1` with `--minutes 30`. Trainer now handles SIGINT as a graceful stop, finishes a safe validation/checkpoint boundary, persists interrupted status, and keeps best-validation promotion. Docs now state that the 30-minute run is expected to fit roughly 10–12 epochs at the observed rate but does not guarantee another metric gain or 30 FPS. The prior ~2 FPS report belongs to epoch 30; epoch 36 needs fresh runtime evaluation before quoting.


## 2026-09-27 — Dual architecture model workspace

Added a PointNeXt-S outdoor adaptation following the official small topology (width 32, residual SA, four stride-4 stages and symmetric decoder). Six LiDAR channels, four classes, height attention, outdoor radii and portable centroid/radius-kNN sampling are documented adaptations; no published accuracy or speed is inherited. No PointNeXt training was run during implementation.

Centralized architecture and artifact identity in backend/model/registry.py; inference now lives in backend/model/inference.py with a compatibility import for older tools. Each model has independent weights, logs, exports and validation selection. Jobs freeze the selected checkpoint; demo grid experiments cannot replace a job's selected model. A process lock prevents concurrent trainers; OOM probing releases failed allocations and restores pre-probe BatchNorm state.

Added model cards and selection in the existing Aero dashboard, per-model download readiness tied to checkpoint hashes, and queued same-scan comparison through the shared GPU worker. CLI and UI call the same evaluator. It records full-scan/distance-band semantics, object-class recall, stage P50/P95/P99, memory, cold start, checkpoint/input provenance and paired frame-bootstrap intervals. Missing results stay unavailable. PointNet++ best at inspection: epoch 48, 79.0034% block-validation mIoU; its current CPU/CUDA parity-checked bundle was rebuilt. PointNeXt downloads become available only after real training and export.

Moved five root reports into docs/reports and docs/history; updated report generators and packaging. Archived obsolete exporter and duplicate deployment README in snapshots/before-model-catalog-cleanup-20260927.zip before removing them. Cleared generated test caches. README.md is the single project-owned README; environment dependency documentation, licenses, datasets, checkpoints and rollback snapshots remain protected. New deployment bundles use MODEL_CARD.md.

Verification: complete suite 37 passed; focused model/API suite 8 passed after follow-up integration fixes. PointNeXt forward/backward at 1024 points, forward at 4096 points, and fixed-shape trace parity checked; current PointNet++ CPU/CUDA export parity passed. JavaScript syntax and browser model selection checked. Fixed a catalog-loading UI race found in browser verification. No production certification, PointNeXt quality result, or 30 FPS claim is made. Commands are in README.md; train.ps1 defaults to 30 minutes, with final validation/checkpoint boundary overhead disclosed.

## 2026-09-28 — Restore the single-page evaluator flow

Reassembled the comparison dashboard, project overview, trained-model comparison, training record and inference console as one continuous page. The top navigation now scrolls among Compare maps, Compare trained models and Process a scan without swapping or hiding sections. Model comparison and the evidence panels start open. Kept the model selector, two downloads, camera/grid controls, scan uploader, replay and detailed benchmark evidence intact.

Made the map comparison the first stop, placed the project overview directly in that flow, and kept both trained architectures and the same-scan comparison prominent immediately below the maps. Retained only the high-value opening metrics: near-field cell agreement, controlled pre-network point reduction, grid storage/cell count and full-backend P50. The slower adaptive-grid timing remains plainly described in detailed evidence. Removed the stale epoch-30 point-level table that duplicated and conflicted with newer cell-level evidence.

Reorganized frontend assets into `app/`, `features/` and `styles/`, updated local asset references and the doctor check, and replaced the root README with a single detailed project/architecture/evidence guide. Removed superseded hand-written setup and pitch documents only after saving `snapshots/docs-before-readme-consolidation-20260928.zip`; preserved generated class mapping, training log, model cards, reports, source attributions and rollback material.

During browser verification, removing the old ablation card exposed an unconditional renderer write to an element that no longer exists; added a null-safe render path, eliminating the false “Local service unavailable” state. Corrected the API regression check so it enforces separate provenance for the epoch-30 full-scan report and epoch-48 cell-grid report instead of expecting them to share a checkpoint. Full test suite: 37 passed. The offline doctor reports the epoch-48 checkpoint and RTX 2060 SUPER. Browser confirms the comparison dashboard, project overview, both model download links, expanded evidence and expanded processing console render together. No training, score alteration or GitHub upload was performed.

## 2026-09-28 — Final single-page cleanup

Removed the duplicate top header so the dashboard has one compact navigation row. Kept map comparison first, with the overview card, both trained models and their downloads, detailed evidence, and scan processing all mounted on the same page. Navigation was checked across map comparison, model comparison, and scan processing; all sections stay present and the trained-model comparison starts expanded.

Removed empty 3D-storage and zero-valued heatmap panels where they implied evidence that was not measured. The ten sequence-08 intervals now state their measured tie on shared 5 cm cells at displayed precision and are explicitly described as intervals from one sequence. Map-stability rows without enough pose pairs now explain the gap in plain language while retaining the measured focus-turn grid rebuild result. The run summary now emphasizes processing rate, median frame time and elapsed time; it no longer counts repeated cluster observations as unique detections. Per-run memory is omitted when unavailable instead of showing a dash.

Verification: JavaScript syntax checks passed, browser navigation confirmed all three page sections remain visible and the two trained-model downloads remain available, and the complete test suite passed (37 tests; 6 upstream warnings). No measured model or performance values were changed.

## 2026-09-28 — One simultaneous dashboard layout

Replaced the section-jump navigation with one responsive dashboard grid. The map comparison is the primary card, with the project overview and decisive measured metrics inside it; the PointNet++ / PointNeXt-S comparison and both model downloads sit alongside it. Scan processing and the expanded detailed-evidence panels remain in the same dashboard below. Legacy URL hashes no longer move the viewport or switch focus between separate sections. Existing map modes, model selection/comparison, uploads, playback and benchmark controls remain mounted.

Browser verification at the running local app confirmed the map comparison, overview, two trained models and downloads, processing console, detection feed and expanded evidence are all present together, including when opened with the former `#/compare` hash. JavaScript syntax checks passed. Full suite: 37 passed (6 upstream warnings). No model metrics or checkpoint data were changed.

## 2026-09-28 — Repair evaluation charts and text legibility

Fixed the evaluation graph layout so chart coordinates are computed from each panel's real width and a stable height; this prevents oversized axis labels, overlapping policy names, and graphs spilling into adjacent cards. The evidence area now stays a three-chart comparison on wide displays and adapts to two columns or one column on smaller screens. The five-policy efficiency plot uses measured active-cell counts (thousands) against measured model-plus-grid FPS with a clear, data-bounded axis; policy names sit in a legend and individual points retain hover values. Allocation and distance-accuracy remain the main evidence; the heatmap is omitted when all ten intervals tie at displayed precision.

Raised chart labels, evidence captions, and benchmark-table type to readable sizes with darker contrast while preserving the glass Frutiger Aero theme. The allocation timeline now labels scan positions (1, midpoint, final scan), avoiding repeated rounded timestamp labels. No model scores or benchmark values were altered. Browser layout check confirmed three separate 549px charts with 210px SVGs, 14px chart labels, 14px evidence-table cells, and distinct readable axes at the current desktop width; evidence content is no longer forced into block layout. JavaScript syntax checks passed; full suite: 37 passed, 6 upstream warnings.

## 2026-09-28 — Enlarge and rebalance the inference viewer

Reduced the inference controls to a compact left rail and gave the synchronized map the remaining desktop width. Removed the old fixed-height clipping behavior and made the primary viewer a tall, responsive canvas (500–720 px on desktop, viewport-scaled on smaller screens). Reorganized pipeline stages, class confidence, runtime metrics, and latency chart into a labeled three-column instrumentation row; it collapses cleanly at narrower widths. Existing inference, replay, and model-selection behavior remains unchanged.

Validation: browser computed styles confirmed the compact control rail, expanded map region, and unclipped viewer screen; JavaScript syntax checks had passed before this CSS-only refinement. Updated the asset version so the browser loads the latest layout.

## 2026-09-28 — Rebalance the inference console columns

Moved the pipeline and live metrics into the space directly below the run controls, creating one continuous left rail. The map and run evidence now occupy the full right column across both left-rail rows, so the controls no longer leave a tall empty strip beside the viewer. Increased the map canvas height slightly and kept the detection feed full width. Tablet and mobile layouts still stack the sections for readable controls.

Validation: refreshed the local single-page dashboard with the updated asset version; the page retained working mode, replay, model, upload, and evidence controls. CSS-only layout change; no inference behavior or measurements changed.

## 2026-09-28 — Align processing, pipeline, and detections

Recomposed the process card into a true two-column workspace: run controls, pipeline metrics, and a compact detection feed form a stacked left rail; the map and run evidence occupy the broad right canvas. The detection feed now follows the pipeline directly. Reduced the supporting process-memory chart to a short strip and slightly tightened the latency chart so measured processing and the map remain visually dominant. Narrow screens return to a readable stacked layout.

Validation: refreshed the local dashboard after updating asset versions. This is a presentation-only change; processing behavior, model selection, and displayed measurements are unchanged.

## 2026-09-28 — Clarify the run summary and pair runtime charts

Shortened map guidance to the essentials: class legend, distance-to-cell-size zones, one line explaining refinement, and a concise cached-replay label. The run summary now uses three clear measures (processing rate, median time per scan, total time) and places processing latency beside process memory in two balanced chart cards. Both plots use the full right-column width and a readable height; on narrow screens they stack. The live latency plot returns to the pipeline rail when a new job starts. No model or runtime values were changed.

Validation: JavaScript syntax checks passed for the dashboard and evidence scripts; local page refreshed with the updated assets.

## 2026-09-28 — Give runtime graphs a balanced reading size

The run summary now pairs processing latency and process RSS in two equal chart cards when both measurements exist; a single available chart uses the full row. Medium-width screens give the viewer and charts more horizontal room, while mobile keeps the plots stacked. Simplified map notes to the resolution zones, one refinement sentence, and a short cached-replay label. Processing rate, median scan time, total duration and all source measurements are preserved.

Validation: dashboard and evidence JavaScript syntax checks passed. Refreshed the local browser and confirmed concise map copy and the latency chart are present; RSS is shown only when the completed run contains measured memory samples.

## 2026-09-28 — Use the launch rail space for intervals and detections

- Expanded the preset interval list so more real held-out sequence intervals are visible without scrolling.
- Let the input, pipeline, and detection cards stretch alongside the map instead of leaving unused space below them.
- Increased the detection feed's visible height and improved row alignment/readability while keeping it scrollable.
- Kept the update CSS-only, so model, inference, and navigation behavior are unchanged.


## 2026-09-28 — Make dashboard scrolling easier to navigate

- Added a fixed glass section navigator for Compare, Models, Process, and Evidence, with a live page-progress line and a one-tap return to the top.
- Added scroll-aware active-section highlighting and reduced-motion support; navigation scrolls to the start of each card.
- Pointed the hero actions at the matching dashboard cards. The card layout and inference behavior are unchanged.


## 2026-09-28 — Simplify the first-read comparison

- Rewrote the comparison heading, checkpoint note, metric captions, and project overview in short plain language.
- Removed the repeated explanation under the metrics while keeping the separate-test and checkpoint caveats visible.
- Increased contrast and font sizes on the comparison labels and explanatory text.
- Left all measured values and dashboard behavior unchanged.

## 2026-09-28 — Organize the backend and prepare a deployment package

- Moved grid, scan pipeline, scene orchestration, odometry, planning, and API modules into named backend packages; updated Python imports, launch scripts, tests, and project documentation.
- Added a minimal Docker image definition, a guarded build-context packager, an ECS GPU task template, and AWS preparation notes. No AWS resources were created and no deployment was started.
- Kept the SemanticKITTI dataset, training caches, upload history, both best-validation checkpoints, export bundles, and rollback snapshots in place.
- Excluded generated caches, bulky training-only data, historic snapshots, and old epoch checkpoints from source-control and release packaging. Removed recreated Python/test cache folders only.
- Kept the workspace directory named `PRISM` so existing launch paths and active local sessions remain valid.
- Removed only empty legacy placeholder directories after confirming they contained no files and had no active code references.
- Validation: `pytest -q` passed all 37 tests. The deployment packager produced a context with both current best checkpoints and 78 demo scans; the temporary context was removed after inspection.

