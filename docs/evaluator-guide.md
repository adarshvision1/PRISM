# Reviewer walkthrough

**Live demo:** https://d32vayd84aynlf.cloudfront.net/

This path takes roughly five minutes and separates recorded results from new processing.

1. **Start in Compare.** Look at the same scan in the uniform 5 cm reference and PRISM map. Check near-field agreement, occupied leaves, storage and grid time together. The adaptive map saves some storage but costs more grid construction time.
2. **Change the heading.** Move the focus direction and watch the backend grid allocation respond. Near detail remains protected within 3 m.
3. **Open Process.** Choose **Replay recorded PointNet++ results** for an immediate eight-frame walkthrough. This is saved GPU output and does not execute inference. Inspect the semantic view, elevation view, object proposals and processing stages.
4. **Try a fresh run if time permits.** Choose a preset, select PointNet++ MSG or PointNeXt-S, then choose **Run fresh CPU inference**. The live server runs the selected trained model. An eight-frame preset can take several minutes on CPU. Uploading `.bin`, `.ply`, `.pcd` or `.zip` is also supported within hosted limits.
5. **Open Evidence.** Read the 256-scan grid comparison, distance-band plots, hard cases and runtime scope. Open the model cards for checkpoint provenance and downloadable exports.

## Three questions to ask while reviewing

| Question | Where to look |
|---|---|
| Is this a functioning pipeline or just a visualization? | Start a fresh CPU job. The API returns a job ID and progressive frame results from actual inference. |
| What does adaptation achieve? | Compare uniform and PRISM leaf counts, storage and near common-cell mIoU on the same validation scans. |
| What remains unsolved? | Grid construction is slower, the full path misses real-time deadlines and the vehicle/person semantic class does not establish motion. |

The hosted CPU run is not the source of the GPU training and benchmark numbers. Those measurements, raw reports and limitations are linked from [evidence](evidence.md).
