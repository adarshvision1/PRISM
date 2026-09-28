import numpy as np
from scipy.spatial import cKDTree
from .clustering import dbscan
def terrain_ribbons(points,classes,height):
    road=points[classes==0,:3]; ids=np.flatnonzero((classes==1)&(height>.03)&(height<.5))
    if not len(road) or not len(ids):return []
    near=cKDTree(road[:,:2]).query(points[ids,:2])[0]<.8;ids=ids[near]
    if not len(ids):return []
    _,first=np.unique(np.floor(points[ids,:3]/.12).astype(int),axis=0,return_index=True)
    cloud=points[ids[first],:3];labels=dbscan(cloud,1.,5);ribbons=[]
    for label in np.unique(labels):
        if label<0:continue
        p=cloud[labels==label]
        if len(p)<5:continue
        center=p.mean(0);_,axis=np.linalg.eigh(np.cov(p[:,:2].T));rot=axis[:,::-1];local=(p[:,:2]-center[:2])@rot
        keep=np.ones(len(p),bool)
        for _ in range(2):
            coef=np.polyfit(local[keep,0],local[keep,1],2)
            residual=np.abs(local[:,1]-np.polyval(coef,local[:,0]))/np.sqrt(1+np.polyval(np.polyder(coef),local[:,0])**2)
            keep=residual<.2
            if keep.sum()<5:break
        if keep.sum()<5:continue
        u=np.linspace(local[keep,0].min(),local[keep,0].max(),24);xy=np.c_[u,np.polyval(coef,u)]@rot.T+center[:2]
        ribbons.append(np.c_[xy,np.full(24,center[2])].round(3).tolist())
    return ribbons
