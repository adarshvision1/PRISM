"""Cell votes and common-support comparisons. No point score is called a cell score.

Height reference is raw LiDAR, NOT an independently surveyed surface. Occupancy
is observed obstacle semantics, NOT ray-cast free/occupied space.
"""
import numpy as np
from scipy.spatial import cKDTree
from .metrics import confusion,scores
BANDS=((0,10),(10,25),(25,60),(60,100))

def distribution(values):
    a=np.asarray(values,dtype=float);a=a[np.isfinite(a)]
    return dict(n=len(a),mean=float(a.mean()),p50=float(np.percentile(a,50)),p95=float(np.percentile(a,95)),p99=float(np.percentile(a,99))) if len(a) else dict(n=0,mean=None,p50=None,p95=None,p99=None)

def error_stats(values):
    a=np.asarray(values,dtype=float)
    return {'mae':float(np.abs(a).mean()),'rmse':float(np.sqrt((a*a).mean())),'p95':float(np.percentile(np.abs(a),95))} if len(a) else {'mae':None,'rmse':None,'p95':None}

def quality(points,truth,result,reference):
    n=result.nodes; ids=result.point_cells;valid=(ids>=0)&(truth<4)
    votes=np.bincount(ids[valid]*4+truth[valid],minlength=len(n)*4).reshape(-1,4)
    gt=votes.argmax(1).astype(np.uint8);gt[votes.sum(1)==0]=255
    centers=np.c_[n['x']+n['size']/2,n['y']+n['size']/2]
    radius=np.linalg.norm(centers,axis=1)
    # Common 5cm GT leaf support: avoids rewarding policies merely for changing
    # the number and sizes of their evaluation units.
    fine=reference.nodes; fi=reference.point_cells;usable=(fi>=0)&(ids>=0)
    first=np.full(len(fine),len(points),dtype=np.int64)
    np.minimum.at(first,fi[usable],np.flatnonzero(usable))
    represented=first<len(points); refidx=np.flatnonzero(represented); coarse=ids[first[represented]]
    fr=np.hypot(fine['x'][refidx]+.025,fine['y'][refidx]+.025)
    pred=n['dominant_class'][coarse];target=fine['dominant_class'][refidx]
    # A fine cell can straddle a non-dyadic adaptive boundary only through numeric
    # rounding; all tiers are multiples of .05 and origins are globally aligned.
    dh=n['mean_z'][coarse]-fine['mean_z'][refidx]
    height_span=np.maximum(n['max_z'][coarse]-n['min_z'][coarse],0)
    out=[]
    for lo,hi in BANDS:
        mask=(radius>=lo)&(radius<hi);fmask=(fr>=lo)&(fr<hi)
        cm=confusion(gt,n['dominant_class'],mask); fm=confusion(target,pred,fmask)
        known=fmask&(target<4); t=np.isin(target[known],[2,3]);p=np.isin(pred[known],[2,3]);union=(t|p).sum()
        hist={str(s):int((mask&np.isclose(n['size'],s)).sum()) for s in (.05,.1,.25,.5)}
        area={str(s):float(np.sum(n['size'][mask&np.isclose(n['size'],s)]**2)) for s in (.05,.1,.25,.5)}
        total=sum(area.values())
        out.append({'distance_m':[lo,hi],'cell':scores(cm),'common_5cm_cell':scores(fm),'elevation':error_stats(dh[fmask]),
                    'elevation_min':error_stats(n['min_z'][coarse][fmask]-fine['min_z'][refidx][fmask]),
                    'elevation_max':error_stats(n['max_z'][coarse][fmask]-fine['max_z'][refidx][fmask]),
                    'observed_obstacle_iou':float((t&p).sum()/union) if union else None,
                    'cells':int(mask.sum()),'bytes':int(mask.sum()*n.dtype.itemsize),'histogram':hist,
                    'observed_leaf_area_m2':area,'area_fraction':{k:v/total if total else None for k,v in area.items()},
                    'multi_height_cells':int((height_span[fmask]>.5).sum())})
    # Distance of each mixed-GT cell's contributing points to its nearest edge.
    mixed=(votes>0).sum(1)>1; boundary=usable&mixed[np.maximum(ids,0)]
    xy=points[boundary,:2];bn=n[ids[boundary]]
    edge=np.minimum.reduce([np.abs(xy[:,0]-bn['x']),np.abs(xy[:,0]-bn['x']-bn['size']),np.abs(xy[:,1]-bn['y']),np.abs(xy[:,1]-bn['y']-bn['size'])])
    complex_ref=(fine['height_variance'][refidx]>.025**2)|fine['semantic_complexity'][refidx]
    return {'bands':out,'cells':len(n),'bytes':n.nbytes,'grid_ms':result.elapsed_ms,'refinement_ops':result.refined_nodes,
            'retained_fraction':result.valid_points/max(1,len(points)),'in_range_retained_fraction':float((ids[usable]>=0).mean()) if usable.any() else None,
            'boundary_incell_distance_m':error_stats(edge),'complex_region_mean_cell_m':float(n['size'][coarse][complex_ref].mean()) if complex_ref.any() else None,
            'simple_region_mean_cell_m':float(n['size'][coarse][~complex_ref].mean()) if (~complex_ref).any() else None}

def paired_ci(a,b,seed=53):
    a=np.asarray(a,float);b=np.asarray(b,float);d=b-a;d=d[np.isfinite(d)]
    if not len(d):return None
    # Moving-block bootstrap (16 sequential evaluated frames) limits treating
    # adjacent scans as independent. It does not imply independence of sequences.
    rng=np.random.default_rng(seed);length=min(16,len(d)); draws=[]
    for _ in range(1000):
        starts=rng.integers(0,len(d),size=int(np.ceil(len(d)/length)))
        indices=np.concatenate([(s+np.arange(length))%len(d) for s in starts])[:len(d)]
        draws.append(d[indices].mean())
    return {'delta':float(d.mean()),'low':float(np.percentile(draws,2.5)),'high':float(np.percentile(draws,97.5)),'n':len(d),'method':'paired circular moving-block bootstrap; block=16 evaluated frames; 1000 draws'}

def temporal(previous,current,previous_pose,pose):
    if previous is None or previous_pose is None or pose is None:return None
    old=previous.nodes;new=current.nodes
    xyz=np.c_[old['x']+old['size']/2,old['y']+old['size']/2,old['mean_z']]
    t=np.linalg.inv(pose)@previous_pose; xyz=xyz@t[:3,:3].T+t[:3,3]
    target=np.c_[new['x']+new['size']/2,new['y']+new['size']/2,new['mean_z']]
    if not len(xyz) or not len(target):return None
    dist,idx=cKDTree(xyz).query(target,k=1)
    match=dist<.15
    return {'overlap_fraction':float(match.mean()),'semantic_flicker_rate':float((new['dominant_class'][match]!=old['dominant_class'][idx[match]]).mean()) if match.any() else None,
            'resolution_change_rate':float((new['size'][match]!=old['size'][idx[match]]).mean()) if match.any() else None,
            'height_stability_mae_m':float(np.abs(target[match,2]-xyz[idx[match],2]).mean()) if match.any() else None,
            'scope':'ego-compensated nearest cell centers within 15cm; observed overlap only; moving surfaces not excluded'}
