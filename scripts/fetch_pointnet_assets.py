"""Build-time downloads only; runtime is entirely offline."""
from pathlib import Path
import json, hashlib, urllib.request
from remotezip import RemoteZip
ROOT = Path(__file__).resolve().parents[1]
def main():
    base='https://raw.githubusercontent.com/yanx27/Pointnet_Pointnet2_pytorch/master/'
    folder=ROOT/'backend/model/pointnet2'; folder.mkdir(parents=True,exist_ok=True)
    for remote,local in [('models/pointnet2_utils.py','reference_utils.py'),('models/pointnet2_sem_seg_msg.py','reference_model.py'),('LICENSE','LICENSE')]:
        urllib.request.urlretrieve(base+remote,folder/local)
    entries=[]
    # 20 separated scans from every official training sequence; no validation used.
    for kind,url in [('velodyne','https://s3.eu-central-1.amazonaws.com/avg-kitti/data_odometry_velodyne.zip'),('labels','https://www.semantic-kitti.org/assets/data_odometry_labels.zip')]:
        with RemoteZip(url,initial_buffer_size=4*1024*1024,timeout=90) as archive:
            for seq in ['00','01','02','03','04','05','06','07','09','10']:
                names=sorted(n for n in archive.namelist() if f'sequences/{seq}/{kind}/' in n and n.endswith('.bin' if kind=='velodyne' else '.label'))
                chosen=[names[round(i*(len(names)-1)/19)] for i in range(20)]
                for name in chosen:
                    dest=(ROOT/'data'/name).resolve()
                    if not dest.is_relative_to((ROOT/'data').resolve()): raise ValueError('Unsafe source path')
                    dest.parent.mkdir(parents=True,exist_ok=True)
                    if not dest.exists(): dest.write_bytes(archive.read(name))
                    entries.append({'path':str(dest.relative_to(ROOT)).replace('\\','/'),'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'source':url})
                print(kind,seq,len(chosen),flush=True)
    (ROOT/'data/pointnet_sources.json').write_text(json.dumps(entries,indent=2))
if __name__=='__main__': main()
