"""Paired full-scan comparison on identical held-out SemanticKITTI frames."""
import argparse, gc, hashlib, json, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import numpy as np
import psutil
import torch
from backend.model.registry import MODELS
from backend.model.inference import SegmentationPredictor
from backend.labels import read_scan, read_truth
from backend.eval.metrics import confusion, scores
from backend.application.perception_pipeline import process_frame


def compare_models(frames=32, progress=None):
    if frames < 2:raise ValueError('Use at least two paired frames')
    root = ROOT/'data/dataset/sequences/08'
    scans = [p for p in sorted((root/'velodyne').glob('*.bin')) if (root/'labels'/f'{p.stem}.label').exists()]
    scans = [scans[i] for i in np.linspace(0, len(scans)-1, min(frames, len(scans)), dtype=int)]
    if len(scans) < 2:raise RuntimeError('At least two labeled sequence-08 scans are required')
    # Validate both checkpoints before doing any expensive evaluation.
    from backend.application.model_service import require_ready
    for architecture in MODELS:require_ready(architecture)
    report = {'scope': 'Paired validation scans from sequence 08; not an untouched test. Speed includes both grids and detections; browser rendering and disk cache are excluded.',
              'frame_ids': [p.stem for p in scans], 'models': [], 'bands_m': [[0,10],[10,25],[25,60],[60,100]],
              'input_sha256': {p.stem: hashlib.sha256(p.read_bytes()).hexdigest() for p in scans}}
    for architecture in MODELS:
        tick = time.perf_counter()
        predictor = SegmentationPredictor(architecture=architecture, freeze=True)
        load_ms = (time.perf_counter()-tick)*1000
        records, matrices = [], [np.zeros((4,5),np.int64) for _ in range(4)]
        first_source = dict(points=read_scan(scans[0]),name=scans[0].stem,domain='SemanticKITTI validation 08',timestamp=0.)
        tick = time.perf_counter();process_frame(predictor, first_source);cold_ms = (time.perf_counter()-tick)*1000
        if predictor.device.type == 'cuda':torch.cuda.reset_peak_memory_stats()
        for path in scans:
            points = read_scan(path)
            source = dict(points=points,name=path.stem,domain='SemanticKITTI validation 08',timestamp=int(path.stem)*.1)
            result, state = process_frame(predictor, source)
            truth = read_truth(root/'labels'/f'{path.stem}.label')
            distance = np.linalg.norm(points[:,:2],axis=1)
            frame_matrix = confusion(truth,state['classes'],distance<100)
            for matrix, (lo, hi) in zip(matrices, report['bands_m']):
                matrix += confusion(truth,state['classes'],(distance>=lo)&(distance<hi))
            tick = time.perf_counter();json.dumps(result);serialization_ms=(time.perf_counter()-tick)*1000
            grid = result['grids']['prism']
            records.append({'frame':path.stem,'miou':scores(frame_matrix)['miou'],
                'network_ms':result['timing']['network_ms'],'reassembly_ms':result['timing']['reassemble_ms'],
                'grid_ms':grid['grid_ms'],'detection_ms':result['timing']['detection_ms'],
                'serialization_ms':serialization_ms,'total_ms':result['timing']['processing_ms']+serialization_ms,
                'cells':grid['active_cells'],'bytes':grid['bytes'],'rss_mib':psutil.Process().memory_info().rss/1048576})
            if progress:progress(architecture,len(records),len(scans))
        timing = {key:dict(zip(['p50','p95','p99'],map(float,np.percentile([r[key] for r in records],[50,95,99]))))
                  for key in ('network_ms','reassembly_ms','grid_ms','detection_ms','serialization_ms','total_ms','rss_mib')}
        report['models'].append({'architecture':architecture,'checkpoint_sha256':predictor.metadata['sha256'],
            'epoch':predictor.metadata['epoch'],'device':str(predictor.device),'runtime':predictor.metadata['runtime'],
            'model_load_ms':load_ms,'cold_first_frame_ms':cold_ms,'timing':timing,
            'warm_fps':1000/np.mean([r['total_ms'] for r in records]),
            'semantics':scores(sum(matrices)), 'by_distance':[scores(m) for m in matrices],
            'mean_cells':float(np.mean([r['cells'] for r in records])),
            'mean_grid_mib':float(np.mean([r['bytes'] for r in records])/1048576),
            'gpu_peak_allocated_mib':torch.cuda.max_memory_allocated()/1048576 if predictor.device.type=='cuda' else None,
            'frames':records})
        print(f'{architecture}: {len(records)} paired frames measured',flush=True)
        del predictor;gc.collect()
        if torch.cuda.is_available():torch.cuda.empty_cache()
    delta = np.array([r['miou'] for r in report['models'][1]['frames']])-np.array([r['miou'] for r in report['models'][0]['frames']])
    rng=np.random.default_rng(53);boot=rng.choice(delta,(2000,len(delta)),replace=True).mean(1)
    report['paired_miou_difference']={'pointnext_minus_pointnet':float(delta.mean()),'ci95':np.percentile(boot,[2.5,97.5]).tolist(),
        'method':'Paired frame bootstrap; correlated driving frames limit independence.'}
    target=ROOT/'data/model_comparison.json';temporary=target.with_suffix('.tmp')
    temporary.write_text(json.dumps(report,indent=2));temporary.replace(target)
    print(f'Saved {target}')
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--frames', type=int, default=32)
    args = parser.parse_args()
    compare_models(args.frames)


if __name__ == '__main__':main()
