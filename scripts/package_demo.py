"""Package the offline app, evidence, weights and real demo source scans."""
from pathlib import Path
import sys,json,zipfile,hashlib
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
def main():
    files=[]
    for root in ['backend','frontend','docs','tests','scripts']:
        files.extend(p for p in (ROOT/root).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.zip','.pyc','.tmp') and 'paper_extracts' not in p.parts and (p.suffix!='.ckpt' or p.name in ('best.ckpt','interim.ckpt')))
    for name in ['config.json','START_PRISM.cmd','start.ps1','train.ps1','TRAIN_PRISM_30M.ps1','README.md','requirements.txt','requirements-model.txt','requirements-dev.txt','PROGRESS_LOG.md']:
        if (ROOT/name).exists():files.append(ROOT/name)
    for name in ['semantic-kitti.yaml','pointnet_benchmark.json','pointnet_demo.json','training_run.json','performance_trials.json','expanded_sources.json','dataset_validation.json','theme_verification.json','upload_verification.json','MANIFEST.md','grid_evidence.json','runtime_audit.json','evaluation_sources.json']:
        if (ROOT/'data'/name).exists():files.append(ROOT/'data'/name)
    demo=json.loads((ROOT/'data/pointnet_demo.json').read_text())
    for chunk in demo['chunks']:
        files.extend(ROOT/'data/pointnet_frames'/f'{i:05d}.json' for i in chunk['indices'])
        files.extend(ROOT/'data/dataset/sequences/08/velodyne'/f'{i:06d}.bin' for i in chunk['frame_ids'])
        files.extend(ROOT/'data/dataset/sequences/08/labels'/f'{i:06d}.label' for i in chunk['frame_ids'])
    files.extend(ROOT/'data/dataset/sequences/08'/name for name in ['calib.txt','poses.txt'])
    files.append(ROOT/'vendor/semantic-kitti-LICENSE')
    files.extend(p for p in (ROOT/'data/deployment').rglob('*') if p.is_file() and p.suffix!='.tmp')
    files.extend(p for p in (ROOT/'data/models').rglob('*') if p.is_file() and p.suffix in ('.json','.csv'))
    if (ROOT/'data/model_comparison.json').exists():files.append(ROOT/'data/model_comparison.json')
    files=sorted(set(files));manifest={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    (ROOT/'data/offline_manifest.json').write_text(json.dumps(manifest,indent=2))
    archive=ROOT/'PRISM-offline-demo.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=3) as z:
        for p in files:z.write(p,p.relative_to(ROOT).as_posix())
        z.writestr('data/offline_manifest.json',json.dumps(manifest,indent=2))
        z.writestr('OPEN-ME.txt','Run START_PRISM.cmd using a prepared local Python environment. This is a backend-powered app, not standalone HTML. Python/CUDA dependencies are not bundled. Install them before disconnecting the network. Cached evidence and demo sources are included; full training data is not. See README.md.')
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for name,digest in manifest.items():assert hashlib.sha256(z.read(name)).hexdigest()==digest
    print('Verified',len(files),'files;',archive.stat().st_size,'bytes')
if __name__=='__main__':main()
