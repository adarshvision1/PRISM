"""Fetch official label configuration and selected SemanticKITTI scans; never the full archive."""
from pathlib import Path
import argparse, hashlib, json, urllib.request, zipfile, sys

ROOT = Path(__file__).resolve().parents[1]
def download(url, target):
    target = ROOT / target
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        print('Downloading', url, flush=True)
        urllib.request.urlretrieve(url, target)
    return target

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--frames', type=int, default=24)
    p.add_argument('--validation-clips',type=int,default=16)
    p.add_argument('--clip-frames',type=int,default=32)
    p.add_argument('--assets-only', action='store_true')
    args = p.parse_args()
    raw = 'https://raw.githubusercontent.com/'
    download(raw+'PRBonn/semantic-kitti-api/master/config/semantic-kitti.yaml', 'data/semantic-kitti.yaml')
    download(raw+'PRBonn/semantic-kitti-api/master/LICENSE', 'vendor/semantic-kitti-LICENSE')
    if args.assets_only: return
    from remotezip import RemoteZip
    urls = {
        'velodyne': 'https://s3.eu-central-1.amazonaws.com/avg-kitti/data_odometry_velodyne.zip',
        'labels': 'https://www.semantic-kitti.org/assets/data_odometry_labels.zip',
    }
    manifest = []
    for kind, url in urls.items():
        print('Reading remote ZIP index:', kind, flush=True)
        with RemoteZip(url, initial_buffer_size=4*1024*1024, timeout=90) as archive:
            names = archive.namelist()
            for seq in ('00', '08'):
                suffix = '.bin' if kind == 'velodyne' else '.label'
                sequence_files=sorted(n for n in names if f'sequences/{seq}/{kind}/' in n and n.endswith(suffix))
                if seq=='00':selected=sequence_files[:args.frames]
                else:
                    if args.validation_clips*args.clip_frames>len(sequence_files):raise ValueError('Requested more validation frames than available')
                    starts=[round(i*(len(sequence_files)-args.clip_frames)/(args.validation_clips-1)) for i in range(args.validation_clips)] if args.validation_clips>1 else [0]
                    selected=[name for start in starts for name in sequence_files[start:start+args.clip_frames]]
                if not selected: raise RuntimeError(f'No scans found for {seq}/{kind}')
                for name in selected:
                    dest = (ROOT/'data'/name).resolve()
                    if not dest.is_relative_to((ROOT/'data').resolve()): raise ValueError('Unsafe archive path')
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    if not dest.exists(): dest.write_bytes(archive.read(name))
                    manifest.append({'path':str(dest.relative_to(ROOT)).replace('\\','/'), 'source':url, 'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()})
                    print(seq, kind, dest.name, dest.stat().st_size, flush=True)
    (ROOT/'data/source_manifest.json').write_text(json.dumps(manifest, indent=2))
    (ROOT/'data/selection.json').write_text(json.dumps({'sequence_00':'first '+str(args.frames)+' scans','sequence_08':{'total_scans':len(sequence_files),'clips':args.validation_clips,'frames_per_clip':args.clip_frames,'start_indices':starts}},indent=2))

if __name__ == '__main__': main()
