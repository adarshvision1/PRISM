"""Conservative, ROS OccupancyGrid-shaped output for an operator/planner bridge."""
import numpy as np

# KITTI's roof-mounted Velodyne sees its own hood/body. A vehicle footprint
# exclusion is necessary before a scan-local obstacle decision. Dimensions are
# conservative defaults for this KITTI demonstration, not universal calibration.
EGO_NOSE_M=2.8
EGO_HALF_WIDTH_M=1.25
EGO_TAIL_M=-3.0

def occupancy_grid(points,classes,extent_m=20.0,resolution=.2):
    points=np.asarray(points,float);classes=np.asarray(classes,np.uint8)
    if len(points)!=len(classes):raise ValueError('Point/class mismatch')
    width=int(round(extent_m/resolution));half=extent_m/2
    if width<=0 or width>1024:raise ValueError('Invalid map geometry')
    grid=np.full((width,width),-1,np.int8)
    xyz=points[:,:3]
    finite=np.isfinite(xyz).all(1)
    self_return=finite&(xyz[:,0]>=EGO_TAIL_M)&(xyz[:,0]<=EGO_NOSE_M)&(np.abs(xyz[:,1])<=EGO_HALF_WIDTH_M)&(xyz[:,2]>=-1.5)&(xyz[:,2]<=.5)
    near=finite&~self_return&(np.abs(xyz[:,0])<half)&(np.abs(xyz[:,1])<half)
    if not np.any(near):return _message(grid,resolution,half,'REVIEW',None,'No observed points')
    # Scan-local ground reference is used only as an independent geometry alarm;
    # it does not turn unknown cells into free space. Across slopes this can
    # over-block, which is conservative and reported as a limitation.
    core=near&(np.linalg.norm(xyz[:,:2],axis=1)<6)&(classes<=1)
    base=float(np.percentile(xyz[core,2] if np.any(core) else xyz[near,2],15))
    ix=np.floor((xyz[near,0]+half)/resolution).astype(int)
    iy=np.floor((xyz[near,1]+half)/resolution).astype(int)
    ix=np.clip(ix,0,width-1);iy=np.clip(iy,0,width-1)
    p=xyz[near];c=classes[near]
    # Estimate a ground height by local x/y tile, so sloped roads do not look
    # like obstacles merely because they are above the scan-wide minimum.
    tile_x=np.floor(p[:,0]).astype(np.int32)
    tile_y=np.floor(p[:,1]/1.5).astype(np.int32)
    tile_key=(tile_x.astype(np.int64)+1024)*2048+tile_y+1024
    local_base=np.full(len(p),base,np.float32)
    ground=(c<=1)
    ground_key=tile_key[ground]
    if len(ground_key):
        order=np.argsort(ground_key,kind='stable')
        ordered_key=ground_key[order]
        ordered_z=p[ground,2][order]
        unique,start,count=np.unique(ordered_key,return_index=True,return_counts=True)
        levels=np.full(len(unique),base,np.float32)
        for index in np.flatnonzero(count>=10):
            levels[index]=np.percentile(ordered_z[start[index]:start[index]+count[index]],15)
        position=np.searchsorted(unique,tile_key)
        found=position<len(unique)
        found[found]&=unique[position[found]]==tile_key[found]
        local_base[found]=levels[position[found]]
    blocked=(((c==2)|(c==3))&(p[:,2]>local_base+.10))|(p[:,2]>local_base+.22)
    # Cast observed ground beams through the local map. Their traversed cells
    # are free evidence, while unknown sectors stay unknown. Nearest obstacle
    # in each azimuth bin truncates the ray; occupied endpoints are overlaid
    # afterwards. The 2-D projection still cannot resolve overhangs.
    radius=np.linalg.norm(p[:,:2],axis=1)
    azimuth=np.mod(np.arctan2(p[:,1],p[:,0])+np.pi,2*np.pi)
    bins=np.floor(azimuth/(2*np.pi)*720).astype(np.int32)
    nearest=np.full(720,np.inf,np.float32)
    np.minimum.at(nearest,bins[blocked],radius[blocked])
    traversable=(c==0)|(c==1)
    admissible=traversable&(radius<nearest[bins]-.1)
    farthest=np.zeros(720,np.float32)
    np.maximum.at(farthest,bins[admissible],radius[admissible])
    for sector in np.flatnonzero(farthest>.3):
        distance=np.arange(0,float(farthest[sector]),resolution/2)
        angle=(sector+.5)*(2*np.pi/720)-np.pi
        ray_x=np.floor((distance*np.cos(angle)+half)/resolution).astype(int)
        ray_y=np.floor((distance*np.sin(angle)+half)/resolution).astype(int)
        inside=(ray_x>=0)&(ray_x<width)&(ray_y>=0)&(ray_y<width)
        grid[ray_y[inside],ray_x[inside]]=0
    grid[iy[traversable],ix[traversable]]=0
    grid[iy[blocked],ix[blocked]]=100
    corridor=(p[:,0]>EGO_NOSE_M)&(p[:,0]<EGO_NOSE_M+3)&(np.abs(p[:,1])<1.5)&blocked
    closest=float(np.min(p[corridor,0]-EGO_NOSE_M)) if np.any(corridor) else None
    # A local decision aid, not a vehicle-command certification.
    if closest is not None:status,reason='STOP','Observed obstruction within 3 m ahead of vehicle nose'
    else:
        y0=max(0,int(np.floor((-1.5+half)/resolution)));y1=min(width,int(np.ceil((1.5+half)/resolution)))
        x0=max(0,int(np.floor((EGO_NOSE_M+half)/resolution)));x1=min(width,int(np.ceil((EGO_NOSE_M+3+half)/resolution)))
        corridor_cells=grid[y0:y1,x0:x1]
        if np.mean(corridor_cells>=0)<.7:status,reason='REVIEW','Forward corridor lacks sufficient observed free cells'
        else:status,reason='CLEAR','No obstruction observed in the checked corridor'
    result=_message(grid,resolution,half,status,closest,reason)
    result['self_filter']={'x_m':[EGO_TAIL_M,EGO_NOSE_M],'abs_y_max_m':EGO_HALF_WIDTH_M,'z_m':[-1.5,.5]}
    return result

def _message(grid,resolution,half,status,closest,reason):
    height,width=grid.shape
    return {'type':'nav_msgs/msg/OccupancyGrid','header':{'frame_id':'velodyne'},'info':{'resolution':resolution,'width':width,'height':height,'origin':{'position':{'x':-half,'y':-half,'z':0},'orientation':{'x':0,'y':0,'z':0,'w':1}}},'data':grid.ravel().astype(int).tolist(),'operator_status':status,'reason':reason,'nearest_obstruction_m':closest,'counts':{'free':int(np.count_nonzero(grid==0)),'occupied':int(np.count_nonzero(grid==100)),'unknown':int(np.count_nonzero(grid==-1))}}
