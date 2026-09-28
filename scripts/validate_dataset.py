"""Validate every local training scan/label pair and emit an auditable inventory."""
from pathlib import Path
import sys,json
import argparse
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.labels import config
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--cache-dir',default='data/blocks_cache');args=ap.parse_args()
    rows=[];total=0;points_total=0
    for seq in config()['split']['train']:
        folder=ROOT/f'data/dataset/sequences/{seq:02d}';paths=sorted((folder/'velodyne').glob('*.bin'));count=0;points=0
        for p in paths:
            label=folder/'labels'/f'{p.stem}.label'
            if not label.exists():raise ValueError(f'Missing paired label: {p}')
            if p.stat().st_size%16 or label.stat().st_size%4:raise ValueError(f'Invalid binary length: {p}')
            xyz=np.fromfile(p,np.float32).reshape(-1,4);labels=np.fromfile(label,np.uint32)
            if not len(xyz) or len(labels)!=len(xyz) or not np.isfinite(xyz).all():raise ValueError(f'Invalid scan/labels: {p}')
            count+=1;points+=len(xyz)
        rows.append(dict(sequence=f'{seq:02d}',paired_scans=count,points=points));total+=count;points_total+=points
    cache=Path(args.cache_dir);cache=cache if cache.is_absolute() else ROOT/cache
    meta=json.loads((cache/'manifest.json').read_text())
    report=dict(status='passed',paired_training_scans=total,training_points=points_total,sequences=rows,training_blocks=meta['train']['blocks'],validation_blocks=meta['valid']['blocks'],validation_sequences=meta['valid']['sequences'])
    (ROOT/'data/dataset_validation.json').write_text(json.dumps(report,indent=2))
    text='# SemanticKITTI local inventory\n\nEvery listed training scan was checked for finite XYZ/intensity, binary shape and equal point/label count. Sequence 08 is excluded from training. Source hashes are in expanded_sources.json.\n\n| Training sequence | Paired scans | Points |\n|---|---:|---:|\n'
    text+='\n'.join(f"| {r['sequence']} | {r['paired_scans']:,} | {r['points']:,} |" for r in rows)
    text+=f'\n\nTotal: {total:,} paired training scans, {points_total:,} points. Prepared {meta["train"]["blocks"]:,} training blocks; retained the same {meta["valid"]["blocks"]:,} validation blocks from 08.\n'
    (ROOT/'data/MANIFEST.md').write_text(text,encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k!='sequences'}))
if __name__=='__main__':main()
