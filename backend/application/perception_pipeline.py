import time
import numpy as np
from backend.grid_engine.ndtree import NdTree
from backend.labels import CLASS_NAMES
from backend.detection.clustering import object_boxes,attach_tracks
from backend.detection.curb_fit import terrain_ribbons
def process_frame(predictor,source,previous=None,progress=None):
    start=time.perf_counter();points=source['points'];pose=source.get('pose');previous=previous or {}
    classes,confidence,timing,feat=predictor.predict(points,previous.get('points'),pose,previous.get('pose'),progress)
    speed=heading=0.
    if pose is not None and previous.get('pose') is not None:
        dt=source['timestamp']-previous['timestamp']
        if dt>0:
            delta=(np.linalg.inv(previous['pose'])@pose)[:2,3];speed=float(np.linalg.norm(delta)/dt);heading=float(np.arctan2(delta[1],delta[0]))
    if progress:progress('grid')
    grids={mode:NdTree(mode).build(points,classes,confidence,speed=speed,heading=heading) for mode in ('uniform','prism')}
    if progress:progress('detection')
    tick=time.perf_counter();boxes=object_boxes(points,classes,confidence);ribbons=terrain_ribbons(points,classes,feat[:,4])
    attach_tracks(boxes,previous.get('boxes',[]),pose,previous.get('pose'));detection_ms=(time.perf_counter()-tick)*1000
    dt=source['timestamp']-previous.get('timestamp',source['timestamp'])
    for box in boxes:
        if box.get('trail') and dt>0:box['estimated_speed_mps']=box['displacement_m']/dt
    idx=np.linspace(0,len(points)-1,min(14000,len(points)),dtype=int)
    weightage=[{'name':name,'class':c,'share':float(np.mean(classes==c)),'confidence':float(confidence[classes==c].mean()) if (classes==c).any() else None} for c,name in enumerate(CLASS_NAMES)]
    result={'name':source['name'],'timestamp':source['timestamp'],'domain':source['domain'],'points':np.c_[points[idx,:3],classes[idx],confidence[idx]].round(3).tolist(),'point_count':len(points),'rendered_points':len(idx),'grids':{},'boxes':boxes,'ribbons':ribbons,'weightage':weightage,'speed_mps':speed,'heading':heading,'timing':timing,'uncertain_cells':int((grids['prism'].nodes['class_confidence']<.5).sum()),'uncertain_clusters':sum(b['confidence']<.5 for b in boxes)}
    for mode,g in grids.items():
        n=g.nodes
        # Spatially spread rendering subset only; metrics and classifications use all leaves.
        if len(n)>16000:n=n[np.linspace(0,len(n)-1,16000,dtype=int)]
        cells=np.column_stack((n['x'],n['y'],n['size'],n['dominant_class'],n['mean_z'],n['class_confidence'],n['min_z'],n['max_z'],n['height_variance'])).round(4).tolist()
        result['grids'][mode]={'cells':cells,'active_cells':len(g.nodes),'bytes':g.nodes.nbytes,'grid_ms':g.elapsed_ms,'render_cap':16000}
    result['timing'].update(detection_ms=detection_ms,processing_ms=(time.perf_counter()-start)*1000)
    state={**source,'boxes':boxes,'classes':classes,'confidence':confidence}
    return result,state
