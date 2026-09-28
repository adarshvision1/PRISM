# AWS deployment preparation

PRISM is packaged for a future private AWS deployment. Nothing in this guide deploys or publishes the service. The application remains an offline-capable local prototype until a deployment is deliberately configured.

## Deployment shape

- Build a small image containing the API, browser assets, current best checkpoints, and only the validation scans used by the bundled demonstration. Training data and caches stay out of the image.
- Run one API task on an ECS cluster backed by a GPU EC2 instance. One worker owns the model and serializes GPU jobs.
- Store uploaded and completed job results on an encrypted EFS access point mounted at `/app/data/jobs` so task replacement does not erase results.
- Put the service behind a private or authenticated Application Load Balancer. Restrict inbound access, configure TLS, and set `PRISM_ALLOWED_ORIGINS` to the approved dashboard origin.
- Store images in a private ECR repository and configure CloudWatch logs, health checks, autoscaling limits, and alarms before opening access.

AWS ECS supports GPU task placement on GPU-backed EC2 capacity. A successful container build does not prove that the selected instance meets a latency target. Measure cold start, warm inference, GPU memory, and end-to-end latency on the chosen instance before making edge or real-time claims.

## Prepare a minimal image context

From the project root, run:

```powershell
.\.venv\Scripts\python.exe scripts\prepare_aws_context.py
```

This stages only application code, both current best checkpoints, model bundles, report data, and the bundled sequence-08 demo inputs under `.build/aws-container`. It excludes the full SemanticKITTI dataset, training caches, job history, and epoch snapshots. Review `BUILD_CONTEXT.json` before building.

Build and test locally with a CUDA-capable Docker host:

```powershell
docker build -t prism-lidar-api:local .build/aws-container
docker run --rm --gpus all -p 8000:8000 -e PRISM_DEVICE=cuda prism-lidar-api:local
```

Confirm `/api/health`, both model downloads, and a short scan job before pushing an image. The deployment template is `deployment/aws/task-definition.json`; replace every `REPLACE_WITH_...` value and configure the ECS cluster, GPU capacity provider, EFS access point and security groups, ALB authentication, TLS certificate, private ECR, and CloudWatch log group. Keep the task role least-privileged and do not put credentials in the image or source tree.

## Data and operations

The service reads the bundled demo locally and writes runtime uploads/results to `/app/data/jobs`. Mount durable storage at that exact path. Training checkpoints are packaged as model assets; training datasets and caches are not. For model updates, build and tag a new image from reviewed best checkpoints, run a staging task, compare health and benchmark results, then use an ECS rolling deployment with rollback alarms.

The current benchmark is below real-time speed on the development GPU. An AWS GPU instance may improve throughput, but no target speed is promised until measured on that exact instance and full request path. The app is not a safety-certified autonomous driving system.
