import numpy as np
from scipy.spatial import cKDTree
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

def dbscan(points,eps,min_samples):
    """KD-tree DBSCAN without storing dense pairwise distances."""
    n=len(points)
    if not n:return np.empty(0,np.int32)
    tree=cKDTree(points); core=tree.query_ball_point(points,eps,return_length=True)>=min_samples
    core_idx=np.flatnonzero(core); labels=np.full(n,-1,np.int32)
    if not len(core_idx):return labels
    pairs=cKDTree(points[core_idx]).query_pairs(eps,output_type='ndarray')
    graph=coo_matrix((np.ones(len(pairs)),(pairs[:,0],pairs[:,1])),shape=(len(core_idx),len(core_idx)))
    _,cl=connected_components(graph,directed=False);labels[core_idx]=cl
    border=np.flatnonzero(~core)
    if len(border):
        d,idx=cKDTree(points[core_idx]).query(points[border],distance_upper_bound=eps)
        good=np.isfinite(d);labels[border[good]]=cl[idx[good]]
    return labels

def object_boxes(points,classes,confidence):
    boxes=[]
    for cls,eps,minimum in [(2,1.,5),(3,.5,3)]:
        original=np.flatnonzero(classes==cls)
        if not len(original):continue
        # 20cm occupied representatives bound DBSCAN memory; full-resolution
        # counts/coordinates/confidence retained for boxes and sparse fallback.
        keys=np.floor(points[original,:3]/.2).astype(np.int32)
        _,first,inv=np.unique(keys,axis=0,return_index=True,return_inverse=True)
        labels=dbscan(points[original[first],:3],eps,minimum); mapped=labels[inv]
        for label in np.unique(mapped):
            ids=original[mapped==label]
            groups=[ids] if label>=0 else [original[np.flatnonzero(inv==i)] for i in np.flatnonzero(labels<0)]
            for group in groups:
                cloud=points[group,:3]; center=cloud.mean(0); yaw=0.
                if len(cloud)>2:
                    _,vectors=np.linalg.eigh(np.cov(cloud[:,:2].T));axis=vectors[:,-1];yaw=float(np.arctan2(axis[1],axis[0]))
                rotation=np.array([[np.cos(yaw),-np.sin(yaw)],[np.sin(yaw),np.cos(yaw)]])
                local=(cloud[:,:2]-center[:2])@rotation
                lo,hi=local.min(0),local.max(0);center[:2]+=((lo+hi)/2)@rotation.T
                center[2]=(cloud[:,2].min()+cloud[:,2].max())/2
                size=np.maximum([*(hi-lo),np.ptp(cloud[:,2])],[.3,.3,.4] if cls==3 else [.15,.15,.15])
                boxes.append({'class':cls,'center':center.round(4).tolist(),'size':size.round(4).tolist(),'yaw':yaw,'confidence':float(confidence[group].mean()),'points':len(group),'fallback':bool(label<0),'trail':None})
    return boxes

def attach_tracks(boxes,previous_boxes,pose,previous_pose):
    if pose is None or previous_pose is None:return
    transform=np.linalg.inv(pose)@previous_pose;used=set()
    for box in boxes:
        if box['class']!=3 or box['fallback']:continue
        candidates=[]
        for i,old in enumerate(previous_boxes):
            if old['class']!=3 or old['fallback'] or i in used:continue
            p=transform[:3,:3]@np.array(old['center'])+transform[:3,3]
            d=np.linalg.norm(np.array(box['center'])-p)
            if d<2:candidates.append((d,i,p))
        if candidates:
            d,i,p=min(candidates,key=lambda x:x[0]);used.add(i)
            box['trail']=[p.tolist(),box['center']];box['displacement_m']=float(d)
