# Architecture and execution path

## One scan through the system

1. [`backend/api/server.py`](../backend/api/server.py) accepts a preset or validates an upload. [`backend/ingest/`](../backend/ingest/) parses supported scan formats and registers a background job.
2. [`backend/model/preprocess.py`](../backend/model/preprocess.py) estimates ground-relative height and forms metric blocks. Each point has local coordinates, intensity, height above ground and a currently zero motion-residual channel for the selected checkpoints.
3. The selected implementation in [`backend/model/pointnet2/`](../backend/model/pointnet2/) or [`backend/model/pointnext/`](../backend/model/pointnext/) produces four-class point predictions. The pipeline reassembles them in scan coordinates.
4. [`backend/grid_engine/ndtree.py`](../backend/grid_engine/ndtree.py) builds the adaptive 2.5D map. Distance and heading define resolution ceilings; semantic composition and height variation can trigger local subdivision. A uniform 5 cm reference is built for comparison.
5. [`backend/detection/`](../backend/detection/) derives geometric clusters, boxes and terrain proposals. These are not tracked motion estimates.
6. [`backend/application/`](../backend/application/) composes frame results, stores completed jobs and serves comparison/evidence data. [`frontend/assets/`](../frontend/assets/) renders maps and charts.

## Runtime boundaries

The local app uses FastAPI and one process with serial inference work. The public demo serves that backend on EC2 CPU behind nginx and CloudFront. S3 stores private recovery archives. The public site may replay recorded GPU results instantly or start a real CPU job. The UI identifies which path was used.

Training, evaluation and exports are separate from serving. [`scripts/`](../scripts/) holds preparation and evaluation commands; [`backend/eval/`](../backend/eval/) records metric definitions. [`tests/`](../tests/) checks input handling, model contracts, grid invariants and evidence behavior.

For the complete implementation narrative and research references, see the [technical guide](technical-guide.md).
