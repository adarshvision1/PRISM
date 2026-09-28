from pathlib import Path
import sys,json,argparse,hashlib,shutil
import numpy as np
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from backend.labels import config,read_scan,read_truth,macro_lut,CLASS_NAMES
from backend.model.preprocess import features,blocks
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--target',type=int,default=10000);ap.add_argument('--keep-validation',action='store_true');ap.add_argument('--cache-dir',default='data/blocks_cache');ap.add_argument('--validation-cache-dir',default='data/blocks_cache'); args=ap.parse_args()
    cache=Path(args.cache_dir); cache=cache if cache.is_absolute() else ROOT/cache
    source=Path(args.validation_cache_dir); source=source if source.is_absolute() else ROOT/source
    cache=cache.resolve(); source=source.resolve()
    # Build in a fresh directory so an interrupted larger preparation cannot
    # damage the known-good cache or leave a plausible-looking partial manifest.
    cache.parent.mkdir(parents=True,exist_ok=True)
    staging=cache.with_name(cache.name+'.building')
    if cache.exists(): raise FileExistsError(f'{cache} already exists; choose a new --cache-dir to preserve existing data')
    if staging.exists(): raise FileExistsError(f'{staging} exists from an earlier interrupted build; inspect it before removing it')
    staging.mkdir(); cache=staging
    rng=np.random.default_rng(53); report={}
    for split,limit in [('train',args.target),('valid',600)]:
        if split=='valid' and args.keep_validation:
            source_manifest=json.loads((source/'manifest.json').read_text())
            report['valid']=source_manifest['valid']
            for name in ('valid_x.npy','valid_y.npy'):
                shutil.copy2(source/name,cache/name)
            report['validation_source_cache']=str(source.relative_to(ROOT)) if source.is_relative_to(ROOT) else str(source)
            print('Preserved identical validation blocks',report['valid']['blocks'],flush=True);continue
        paths=[]
        for seq in config()['split'][split]:
            paths.extend(sorted((ROOT/f'data/dataset/sequences/{seq:02d}/velodyne').glob('*.bin')))
        rng.shuffle(paths); records=[]
        x=np.lib.format.open_memmap(cache/f'{split}_x.npy',mode='w+',dtype='float32',shape=(limit,4096,6))
        y=np.lib.format.open_memmap(cache/f'{split}_y.npy',mode='w+',dtype='uint8',shape=(limit,4096))
        # Per-scan cap distributes blocks across scenes; no scan appears in both splits.
        per_scan=max(1,int(np.ceil(limit/max(len(paths),1))))
        for scan_index,path in enumerate(paths,1):
            truth_path=path.parent.parent/'labels'/f'{path.stem}.label'
            if not truth_path.exists(): continue
            points=read_scan(path); truth=read_truth(truth_path)
            feat,_=features(points); candidates=list(blocks(feat,truth,seed=int(path.stem)+53))
            candidates=[b for b in candidates if (b['labels']<4).sum()>32 and b['original_count']>=32]
            rng.shuffle(candidates)
            for b in candidates[:per_scan]:
                i=len(records)
                if i>=limit: break
                x[i]=b['features']; y[i]=b['labels']
                records.append({'sequence':path.parent.parent.name,'frame':int(path.stem),'offset':b['offset'].tolist(),'original_points':b['original_count']})
            if len(records)>=limit: break
            if scan_index%100==0:
                print(split,'scans',scan_index,'/',len(paths),'blocks',len(records),flush=True)
        x.flush(); y.flush(); report[split]={'blocks':len(records),'scans_available':len(paths),'sequences':sorted(set(r['sequence'] for r in records)),'records':records}
        print(split,len(records),'blocks',flush=True)
    cfg=config(); lut=macro_lut(); lines=['# Macro-class mapping','', 'Generated from official SemanticKITTI YAML learning IDs. Macro grouping is an explicit project policy, not a property contained in the YAML. Ignored classes retain 255. Vehicle/person categories are conservative taxonomy, not measured motion.','', '| Raw ID | Official label | Learning ID | Macro class |','|---|---|---|---|']
    for raw,name in cfg['labels'].items(): lines.append(f'| {raw} | {name} | {cfg["learning_map"][raw]} | {CLASS_NAMES[lut[raw]] if lut[raw]<4 else "ignored"} |')
    (ROOT/'docs/class_mapping.md').write_text('\n'.join(lines))
    report['yaml_sha256']=hashlib.sha256((ROOT/'data/semantic-kitti.yaml').read_bytes()).hexdigest()
    (cache/'manifest.json').write_text(json.dumps(report,indent=2))
    final=cache.with_name(cache.name.removesuffix('.building'))
    # pathlib.Path.replace maps to Windows ReplaceFile semantics, which can
    # reject renaming a directory even when the destination does not exist.
    # The destination was refused above, so rename is the correct promotion.
    cache.rename(final)
    print('Cache ready:',final,flush=True)
if __name__=='__main__':main()
