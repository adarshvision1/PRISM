"""Build human-readable reports from measured local evidence, never target numbers."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
def main():
    b=json.loads((ROOT/'data/pointnet_benchmark.json').read_text())
    trials=json.loads((ROOT/'data/performance_trials.json').read_text())
    train=json.loads((ROOT/'data/training_run.json').read_text())
    dataset=json.loads((ROOT/'data/dataset_validation.json').read_text())
    profile=json.loads((ROOT/'config.json').read_text())
    p=b['modes']['prism'];u=b['modes']['uniform']
    lines=['# PRISM measured performance · 2026-09-27','',
        f"Hardware: {b['hardware']['device']}. PyTorch {b['hardware']['torch']}.",
        f"Checkpoint: epoch {b['model']['epoch']}, SHA-256 `{b['model']['sha256']}`.",
        f"Runtime: {profile['input_points_per_block']} near-block samples / {profile['far_points_per_block']} far-block samples, batch {profile['inference_batch_size']}. Far reduction begins only when a whole 10 m block lies beyond 25 m.",'',
        '## Final confirmation', '', b['coverage'],'',
        '| Policy | Processing FPS | Grid ms | Total measured ms | Mean active cells | mIoU |',
        '|---|---:|---:|---:|---:|---:|']
    for name,v in b['modes'].items():lines.append(f"| {name} | {v['pipeline_fps']:.3f} | {v['grid_ms']:.2f} | {v['pipeline_ms']:.2f} | {v['cells']:,.0f} | {v['miou']*100:.2f}% |")
    lines+=['',f"Shared preprocessing + network + reassembly: **{b['inference_ms']:.2f} ms/scan**. Peak process RSS: {b['peak_rss_mb']:.1f} MiB; peak GPU allocated memory: {b['peak_gpu_mb']:.1f} MiB.",'',
        'These processing rates exclude detection, disk I/O, JSON caching and browser drawing. The inference console separately reports elapsed job-wall throughput, which includes those backend costs. Interactive grid Hz excludes neural processing; cached replay is not an inference benchmark.','',
        '## Before and after','',
        f"The previous 512-scan PointNet++ result was 1.243 FPS, 804.61 ms/scan and 74.86% mIoU. The updated checkpoint/runtime measures {p['pipeline_fps']:.3f} FPS, {p['pipeline_ms']:.2f} ms/scan and {p['miou']*100:.2f}% mIoU on the same locally available sequence-08 scans. Both training and runtime changed; this before/after comparison is not a causal isolation of a single optimization.",'',
        f"The 30 FPS target requires 33.33 ms/frame. The measured PRISM path still takes {p['pipeline_ms']/ (1000/30):.1f} times that budget before detection/rendering. **30 FPS has not been achieved.**",'',
        '## Controlled runtime candidate comparison','',
        f"{len(trials['frames'])} spread validation scans, shared checkpoint per sweep. {trials['selection_rule']}",'',
        '| Candidate | Near / far samples | FPS | mIoU | Near dynamic-class recall | Mean network points | Preprocess ms | Network ms | Reassembly ms |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for name,v in trials['profiles'].items():
        c=v['config'];m=v['mean'];lines.append(f"| {name} | {c['input_points_per_block']} / {c.get('far_points_per_block') or c['input_points_per_block']} | {v['fps']:.3f} | {v['miou']*100:.2f}% | {v['near']['recall'][3]*100:.2f}% | {m['network_points']:,.0f} | {m['preprocess_ms']:.2f} | {m['network_ms']:.2f} | {m['reassemble_ms']:.2f} |")
    lines+=['',f"Recommended measured candidate: **{trials['recommended']}**. Full frame-level data: `data/performance_trials.json`.",'',
        'Implemented changes: reduced point tensors before neural execution; batch-size comparison; skipped temporal residual construction for a checkpoint not trained on residuals; scalar block grouping keys; elementwise ground-plane evaluation. Full-cloud predictions are reassembled after inference.','',
        'No TensorRT, C++ grid rewrite or target-Jetson result is claimed. The supplied DRDO paper measures YOLOv8l camera processing on T4; it is method inspiration, not a directly comparable baseline.','',
        '## Storage comparison','',b['voxel_note'],'',
        '## Training evidence','',
        f"{dataset['paired_training_scans']:,} paired training scans; {dataset['training_points']:,} finite input points validated; {train['train_blocks']:,} training blocks. The original 600 validation blocks were preserved. Best validation-block mIoU: {train['best_val_miou']*100:.2f}%. Block validation and full-scan mIoU are different measurements.",
        'Sequence 08 selected weights and runtime settings. This is held-out-from-gradient-training validation, not an untouched test set or full 4,071-frame evaluation.']
    (ROOT/'docs/reports').mkdir(parents=True,exist_ok=True)
    (ROOT/'docs/reports/performance.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    ab=['# Measured ablations and experiment scope','',
        'The completed experiment compares five grid policies using shared predictions from the final selected checkpoint. The separate runtime sweep measures actual neural input/batch trade-offs. Neither is mislabeled a completed seven-factor Taguchi experiment.','',
        '| Policy | FPS | Leaf storage MiB | Mean cells | mIoU |','|---|---:|---:|---:|---:|']
    for name,v in b['modes'].items():ab.append(f"| {name} | {v['pipeline_fps']:.3f} | {v['bytes']/1048576:.3f} | {v['cells']:,.0f} | {v['miou']*100:.2f}% |")
    ab+=['', '## Distance coverage','', '| Band (m) | PRISM mIoU | Labeled points |','|---|---:|---:|']
    for band,v in zip(['0–10','10–25','25–60','60–100'],p['bands']):
        miou=f"{v['miou']*100:.2f}%" if v['miou'] is not None else 'unavailable'
        ab.append(f"| {band} | {miou} | {v['labeled_points']:,} |")
    ab+=['','Ten heatmap rows represent fixed temporal intervals of sequence 08; row sample counts and absent bands are disclosed in the dashboard.','',
        '## What is and is not justified','',
        f"The measured runtime recommendation is {trials['recommended']}, selected under the reported accuracy constraints. Grid defaults retain the conservative 3 m/5 cm floor and 10/25/60 m distance ceilings; no experiment establishes these as mathematically optimal.",
        'Kaur et al., DOI 10.14429/dsj.21132, section 4.2 reports Taguchi tuning for a camera model. Seven three-level PRISM factors require a suitable verified L18/L27 design, repeated training for optimizer factors, explicit safety constraints and a confirmation run. That broader study remains uncompleted; no fabricated array, S/N result or optimality claim is included.']
    (ROOT/'docs/reports/ablations.md').write_text('\n'.join(ab)+'\n',encoding='utf-8')
    print('Generated docs/reports/performance.md and ablations.md from measured data')
if __name__=='__main__':main()
