"""Preflight for the offline PointNet++ application."""
from pathlib import Path
import json,sys,hashlib
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
def main():
    required=['config.json','data/semantic-kitti.yaml','backend/model/pointnet2/reference_utils.py','frontend/index.html','frontend/assets/app/dashboard.js','frontend/assets/styles/base.css','frontend/assets/styles/visualization.css','frontend/assets/styles/theme_aero.css','frontend/assets/features/benchmark_evidence.js','frontend/assets/styles/dashboard.css']
    cfg=json.loads((ROOT/'config.json').read_text())
    required.append(cfg['checkpoint'] if (ROOT/cfg['checkpoint']).exists() else cfg['interim_checkpoint'])
    missing=[name for name in required if not (ROOT/name).exists()]
    if missing:print('Missing local assets:',', '.join(missing));return 1
    import torch,numpy,fastapi,open3d
    checkpoint=torch.load(ROOT/required[-1],map_location='cpu',weights_only=True)
    print('PRISM offline ready |',checkpoint['status'],'| epoch',checkpoint['epoch'])
    print('Compute:',torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU (slower processing, same replay)')
    print('Checkpoint SHA256:',hashlib.sha256((ROOT/required[-1]).read_bytes()).hexdigest()[:16])
    return 0
if __name__=='__main__':raise SystemExit(main())
