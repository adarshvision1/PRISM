"""KITTI odometry poses converted from camera-0 world poses to LiDAR frame."""
from functools import lru_cache
from pathlib import Path
import numpy as np
from backend.labels import ROOT

@lru_cache(maxsize=2)
def poses(sequence):
    if sequence not in ('00','08'):raise ValueError('Only downloaded sequences 00/08')
    directory=ROOT/f'data/dataset/sequences/{sequence}'
    pose=np.loadtxt(directory/'poses.txt').reshape(-1,3,4)
    world_cam=np.tile(np.eye(4),(len(pose),1,1));world_cam[:,:3,:]=pose
    lines={k:np.fromstring(v,sep=' ') for k,v in (line.split(':',1) for line in (directory/'calib.txt').read_text().splitlines())}
    cam_velo=np.eye(4);cam_velo[:3,:]=lines['Tr'].reshape(3,4)
    return world_cam@cam_velo

def motion(sequence,index):
    """Speed and direction of actual measured frame-to-frame translation.

    KITTI odometry scans are nominally 10 Hz. Velocity is in the prior LiDAR
    frame (valid to first order for a 100 ms step); heading is relative to +x.
    """
    all_poses=poses(sequence)
    if not 0<=index<len(all_poses):raise ValueError('Pose index out of bounds')
    if index==0:return 0.0,0.0
    relative=np.linalg.inv(all_poses[index-1])@all_poses[index]
    delta=relative[:2,3]
    speed=float(np.linalg.norm(delta)/.1)
    heading=float(np.arctan2(delta[1],delta[0])) if speed>.1 else 0.0
    return speed,heading

def world_pose(sequence,index):return poses(sequence)[index]
