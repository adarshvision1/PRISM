"""Full-scan ground fit, fixed metric blocks, optional pose residual."""
import numpy as np
from scipy.spatial import cKDTree
def ground_height(points,seed=53):
    xyz=np.asarray(points[:,:3],np.float64); rng=np.random.default_rng(seed)
    near=xyz[np.linalg.norm(xyz[:,:2],axis=1)<35]
    if len(near)<10: near=xyz
    low=near[near[:,2]<=np.quantile(near[:,2],.35)]
    if len(low)<3: return np.zeros(len(xyz),np.float32),[0,0,0],False
    sample=low[rng.choice(len(low),min(3000,len(low)),replace=False)]
    best=np.zeros(len(sample),bool); plane=np.array([0.,0.,np.median(low[:,2])])
    for _ in range(40):
        triple=sample[rng.choice(len(sample),3,replace=False)]; design=np.c_[triple[:,:2],np.ones(3)]
        if abs(np.linalg.det(design))<1e-5: continue
        candidate=np.linalg.solve(design,triple[:,2])
        if np.linalg.norm(candidate[:2])>.35: continue
        inlier=np.abs(sample[:,2]-(sample[:,0]*candidate[0]+sample[:,1]*candidate[1]+candidate[2]))<.12
        if inlier.sum()>best.sum(): best=inlier; plane=candidate
    if best.sum()>=3: plane=np.linalg.lstsq(np.c_[sample[best,:2],np.ones(best.sum())],sample[best,2],rcond=None)[0]
    return (xyz[:,2]-(xyz[:,0]*plane[0]+xyz[:,1]*plane[1]+plane[2])).astype(np.float32),plane.tolist(),bool(best.sum()>=3)
def pose_residual(points,previous=None,pose=None,previous_pose=None):
    if previous is None or pose is None or previous_pose is None: return np.zeros(len(points),np.float32),False
    transform=np.linalg.inv(pose)@previous_pose
    warped=previous[:,:3]@transform[:3,:3].T+transform[:3,3]
    return np.minimum(cKDTree(warped).query(points[:,:3],workers=1)[0],3).astype(np.float32),True
def features(points,previous=None,pose=None,previous_pose=None):
    height,plane,ok=ground_height(points); residual,temporal=pose_residual(points,previous,pose,previous_pose)
    return np.c_[points[:,:4],height,residual].astype(np.float32),{'ground_plane':plane,'ground_fit_valid':ok,'motion_available':temporal}
def blocks(feature_array,labels=None,seed=53,n=4096,far_n=None):
    rng=np.random.default_rng(seed); xy=np.floor(feature_array[:,:2]/10).astype(np.int32)
    inds=np.flatnonzero(np.isfinite(feature_array).all(1)&(np.linalg.norm(feature_array[:,:2],axis=1)<100))
    # Within the 100m disk block coordinates lie in [-10,9]; scalar keys
    # preserve the previous lexicographic order without structured-array sorting.
    keys=(xy[inds,0].astype(np.int64)+16)*64+xy[inds,1]+16
    _,inv=np.unique(keys,return_inverse=True); order=np.argsort(inv,kind='stable'); sorted_inds=inds[order]
    for group in np.split(sorted_inds,np.flatnonzero(np.diff(inv[order]))+1):
        if len(group)==0: continue
        offset=np.array([*(xy[group[0]]*10),0],np.float32)
        # The entire 10m block must lie beyond 25m before reducing samples.
        nearest=np.maximum(np.maximum(offset[:2],-(offset[:2]+10)),0)
        count=far_n if far_n and np.linalg.norm(nearest)>=25 else n
        chosen=rng.choice(group,count,replace=len(group)<count)
        sample=feature_array[chosen].copy(); sample[:,:3]-=offset
        if len(group)<count:
            _,first=np.unique(chosen,return_index=True); duplicate=np.ones(count,bool); duplicate[first]=False
            noise=rng.normal(0,.002,(duplicate.sum(),3)).astype(np.float32)
            sample[duplicate,:3]+=noise; sample[duplicate,4]+=noise[:,2]
        yield {'features':sample,'labels':None if labels is None else labels[chosen], 'indices':group,'sample_indices':chosen,'offset':offset,'original_count':len(group)}
