from pathlib import Path
import re,zipfile,shutil
from .ply_pcd_sequence import load_points
SUPPORTED='.zip of sequential .bin/.ply/.pcd, or a single .bin/.ply/.pcd'
def natural(path):return [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)',str(path))]
def validate_archive(path):
    with zipfile.ZipFile(path) as z:
        if len(z.infolist())>15000:raise ValueError('Archive contains too many entries')
        if sum(i.file_size for i in z.infolist())>2*1024**3:raise ValueError('Expanded archive exceeds 2 GB')
        for i in z.infolist():
            name=i.filename.replace('\\','/')
            if name.startswith('/') or '..' in name.split('/') or ':' in name:raise ValueError('Unsafe archive member path')
            if (i.external_attr>>16)&0o170000==0o120000:raise ValueError('Archive links are not accepted')
def iter_upload(paths,work,limit=300):
    selected=[]
    for path in paths:
        if path.suffix.lower()=='.zip':
            validate_archive(path)
            with zipfile.ZipFile(path) as z:
                names=sorted([n for n in z.namelist() if Path(n).suffix.lower() in {'.bin','.ply','.pcd'}],key=natural)
                if not names:raise ValueError('No supported point-cloud frames in ZIP. Supported: '+SUPPORTED)
                for i,name in enumerate(names[:limit]):
                    dest=work/f'extracted-{len(selected):05d}{Path(name).suffix.lower()}'
                    with z.open(name) as source,dest.open('wb') as target:shutil.copyfileobj(source,target)
                    selected.append((name,dest))
        elif path.suffix.lower() in {'.bin','.ply','.pcd'}:selected.append((path.name,path))
        else:raise ValueError('Supported: '+SUPPORTED)
    for i,(name,path) in enumerate(sorted(selected,key=lambda pair:natural(pair[0]))[:limit]):
        yield {'points':load_points(path),'pose':None,'timestamp':i*.1,'name':name,'domain':'Point cloud; assumes metres, x forward, y left, z up','rgb':None}
