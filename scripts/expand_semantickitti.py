"""Resumable build-time acquisition of paired official training scans only."""
from pathlib import Path
import argparse, json, hashlib, time
from remotezip import RemoteZip
ROOT=Path(__file__).resolve().parents[1]
SOURCES={'velodyne':'https://s3.eu-central-1.amazonaws.com/avg-kitti/data_odometry_velodyne.zip','labels':'https://www.semantic-kitti.org/assets/data_odometry_labels.zip'}
TRAIN=['00','01','02','03','04','05','06','07','09','10']
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--per-sequence',type=int,default=100);ap.add_argument('--evaluation',action='store_true');args=ap.parse_args()
    sequences=['08','11'] if args.evaluation else TRAIN
    manifest='evaluation_sources.json' if args.evaluation else 'expanded_sources.json'
    from concurrent.futures import ThreadPoolExecutor,as_completed
    records=[];added=0;start=time.time()
    def fetch_scene(kind,url,seq):
        found=[];new=0
        with RemoteZip(url,initial_buffer_size=4*1024*1024,timeout=90) as z:
            names=sorted(n for n in z.namelist() if f'sequences/{seq}/{kind}/' in n and n.endswith('.bin' if kind=='velodyne' else '.label'))
            count=min(len(names),args.per_sequence)
            selected=[names[round(i*(len(names)-1)/max(1,count-1))] for i in range(count)]
            for name in selected:
                dest=(ROOT/'data'/name).resolve()
                if not dest.is_relative_to((ROOT/'data/dataset/sequences').resolve()):raise ValueError('Unsafe path')
                dest.parent.mkdir(parents=True,exist_ok=True)
                if not dest.exists() or dest.stat().st_size!=z.getinfo(name).file_size:
                    for attempt in range(3):
                        try:
                            payload=z.read(name)
                            if len(payload)!=z.getinfo(name).file_size:raise ValueError('Truncated member')
                            temp=dest.with_suffix('.download');temp.write_bytes(payload);temp.replace(dest);new+=1;break
                        except Exception:
                            if attempt==2:raise
                found.append(dict(path=dest.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),source=url,bytes=dest.stat().st_size))
        return kind,seq,found,new
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures=[pool.submit(fetch_scene,kind,url,seq) for kind,url in SOURCES.items() for seq in sequences if not (seq=='11' and kind=='labels')]
        for future in as_completed(futures):
            kind,seq,found,new=future.result();records.extend(found);added+=new
            print(kind,seq,len(found),'selected; added files',added,flush=True)
            (ROOT/'data'/manifest).write_text(json.dumps(dict(status='downloading',per_sequence=args.per_sequence,files=records),indent=2))
    pairs={}
    for seq in sequences:
        folder=ROOT/'data/dataset/sequences'/seq
        pairs[seq]=sum((folder/'labels'/f'{p.stem}.label').exists() for p in (folder/'velodyne').glob('*.bin'))
    report=dict(status='complete',per_sequence=args.per_sequence,added_files=added,paired_scans=pairs,elapsed_seconds=time.time()-start,files=records)
    (ROOT/'data'/manifest).write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='files'}),flush=True)
if __name__=='__main__':main()
