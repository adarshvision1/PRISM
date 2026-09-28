import torch
from torch import nn
from . import reference_utils as reference
from ..height_attention import HeightAttention

def random_centroids(xyz,npoint):
    # Input is randomly resampled before grouping; deterministic indices at eval.
    b,n,_=xyz.shape
    return torch.linspace(0,n-1,npoint,device=xyz.device).long()[None].expand(b,-1)
def stable_distance(src,dst):
    with torch.autocast(device_type=src.device.type,enabled=False):
        return torch.cdist(src.float(),dst.float()).square()
def radius_knn(radius,nsample,xyz,new_xyz):
    distance=stable_distance(new_xyz,xyz)
    d,idx=distance.topk(min(nsample,xyz.shape[1]),largest=False,sorted=True)
    return torch.where(d<=radius*radius,idx,idx[...,:1])
# Windows fallback explicitly substitutes sampling/grouping only; SA/FP from source.
reference.farthest_point_sample=random_centroids
reference.query_ball_point=radius_knn
reference.square_distance=stable_distance

class PointNet2MSG(nn.Module):
    def __init__(self,channels=6,radius_scale=1.0,height_attention=True):
        super().__init__(); self.channels=channels
        self.config={'channels':channels,'radius_scale':radius_scale,'height_attention':height_attention}
        sa=reference.PointNetSetAbstractionMsg; fp=reference.PointNetFeaturePropagation
        def layer(n,scale,cin,cout):
            return sa(n,[r*scale*radius_scale for r in [.25,.5,1.0]],[12,16,24],cin,[[cout,cout]]*3)
        self.sa1=layer(512,1,channels,16); self.sa2=layer(128,2,48,32)
        self.sa3=layer(32,4,96,64); self.sa4=layer(8,8,192,96)
        self.fp4=fp(480,[128,128]); self.fp3=fp(224,[96,96])
        self.fp2=fp(144,[64,64]); self.fp1=fp(64+channels,[64,64])
        self.attention=HeightAttention(64) if height_attention else None
        self.head=nn.Sequential(nn.Conv1d(64,64,1),nn.BatchNorm1d(64),nn.ReLU(),nn.Dropout(.25),nn.Conv1d(64,4,1))
    def forward(self,x):
        xyz=x[:,:3]; p1,f1=self.sa1(xyz,x); p2,f2=self.sa2(p1,f1)
        p3,f3=self.sa3(p2,f2); p4,f4=self.sa4(p3,f3)
        f3=self.fp4(p3,p4,f3,f4); f2=self.fp3(p2,p3,f2,f3)
        f1=self.fp2(p1,p2,f1,f2); f0=self.fp1(xyz,p1,x,f1)
        if self.attention is not None: f0=self.attention(f0,x)
        return self.head(f0)
