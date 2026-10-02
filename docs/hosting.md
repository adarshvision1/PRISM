# Public prototype hosting

**Reviewer URL:** https://d32vayd84aynlf.cloudfront.net/

CloudFront provides HTTPS. It forwards to nginx and the FastAPI service on a CPU EC2 instance. Private S3 archives hold recoverable deployment files. The hosted service uses the same inference and grid code as the local prototype, with tighter public resource limits: **64 MB and 16 frames** per upload job.

Recorded GPU results are immediately available for review. New jobs run genuine inference on the AWS CPU. The page labels recorded replay and fresh inference distinctly; hosted CPU completion time is not represented by the earlier GPU benchmark. Uploaded jobs run serially, so a longer preset may take several minutes.

The CUDA Dockerfile and [`deployment/aws/task-definition.json`](../deployment/aws/task-definition.json) are GPU deployment preparation. They are not the current EC2 CPU deployment. Do not cite them as proof of GPU cloud operation.

The public URL depends on retaining its CloudFront distribution. Site uptime, AWS credits and resource charges require ongoing account monitoring. Technical AWS recovery details are kept outside this reviewer-facing repository.
