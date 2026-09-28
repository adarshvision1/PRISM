"""Download official small KITTI pose/calibration archives only (00 and 08)."""
from pathlib import Path
import urllib.request,zipfile,hashlib,json
from backend.labels import ROOT

def main():
    manifest=[]
    for kind in ('poses','calib'):
        url=f'https://s3.eu-central-1.amazonaws.com/avg-kitti/data_odometry_{kind}.zip'
        target=ROOT/f'data/data_odometry_{kind}.zip'
        if not target.exists():urllib.request.urlretrieve(url,target)
        with zipfile.ZipFile(target) as z:
            for seq in ('00','08'):
                names=[n for n in z.namelist() if n.endswith(f'/{seq}.txt') or n.endswith(f'/{seq}/calib.txt')]
                if kind=='poses':names=[n for n in names if 'poses' in n]
                else:names=[n for n in names if 'sequences' in n or 'calib' in n]
                if len(names)!=1:raise RuntimeError(f'Ambiguous {kind}/{seq}: {names}')
                dest=ROOT/f'data/dataset/sequences/{seq}/{kind}.txt'
                dest.parent.mkdir(parents=True,exist_ok=True)
                dest.write_bytes(z.read(names[0]))
                manifest.append({'path':str(dest.relative_to(ROOT)).replace('\\','/'),'url':url,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()})
                print(kind,seq,len(dest.read_bytes()),flush=True)
    (ROOT/'data/odometry_manifest.json').write_text(json.dumps(manifest,indent=2))

if __name__=='__main__':main()
