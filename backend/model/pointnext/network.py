"""PointNeXt-S topology adapted to PRISM's metric LiDAR blocks.

Reference: Qian et al., NeurIPS 2022; OpenPoints PointNextEncoder/Decoder.
S uses [1,1,1,1,1] blocks, width 32, residual SA, strides [1,4,4,4,4].
Unlike the deeper variants, S has no additional inverted residual blocks.
Portable deterministic sampling and radius-kNN replace compiled FPS/ball query.
This is not weight-compatible with official RGB/indoor checkpoints.
"""
import torch
from torch import nn
from ..pointnet2.network import radius_knn, random_centroids
from ..pointnet2.reference_utils import index_points, PointNetFeaturePropagation
from ..height_attention import HeightAttention


class ResidualSetAbstraction(nn.Module):
    def __init__(self, incoming, outgoing, radius):
        super().__init__()
        self.radius = radius
        self.local = nn.Sequential(
            nn.Conv2d(incoming + 3, outgoing // 2, 1, bias=False),
            nn.BatchNorm2d(outgoing // 2), nn.ReLU(),
            nn.Conv2d(outgoing // 2, outgoing, 1, bias=False), nn.BatchNorm2d(outgoing))
        self.skip = nn.Conv1d(incoming, outgoing, 1)

    def forward(self, xyz, features):
        positions = xyz.transpose(1, 2)
        centers = random_centroids(positions, max(1, positions.shape[1] // 4))
        query = index_points(positions, centers)
        neighbors = radius_knn(self.radius, 32, positions, query)
        relative = (index_points(positions, neighbors) - query.unsqueeze(2)) / self.radius
        grouped = index_points(features.transpose(1, 2), neighbors)
        local = self.local(torch.cat((relative, grouped), -1).permute(0, 3, 1, 2)).max(-1).values
        identity = index_points(features.transpose(1, 2), centers).transpose(1, 2)
        return query.transpose(1, 2), torch.relu(local + self.skip(identity))


class PointNeXtSmall(nn.Module):
    architecture = 'pointnext_s'

    def __init__(self, channels=6, radius_scale=1.0, height_attention=True):
        super().__init__()
        self.config = dict(channels=channels, radius_scale=radius_scale, height_attention=height_attention)
        self.stem = nn.Conv1d(channels, 32, 1)
        widths = [32, 64, 128, 256, 512]
        self.encoder = nn.ModuleList([
            ResidualSetAbstraction(widths[i], widths[i+1], .5 * 2**i * radius_scale)
            for i in range(4)])
        self.decoder = nn.ModuleList([
            PointNetFeaturePropagation(widths[i]+widths[i+1], [widths[i], widths[i]])
            for i in range(4)])
        self.attention = HeightAttention(32) if height_attention else None
        self.head = nn.Sequential(nn.Conv1d(32, 32, 1), nn.BatchNorm1d(32), nn.ReLU(),
                                  nn.Dropout(.25), nn.Conv1d(32, 4, 1))

    def forward(self, x):
        positions, features = [x[:, :3]], [self.stem(x)]
        for stage in self.encoder:
            xyz, feat = stage(positions[-1], features[-1])
            positions.append(xyz)
            features.append(feat)
        for i in range(3, -1, -1):
            features[i] = self.decoder[i](positions[i], positions[i+1], features[i], features[i+1])
        out = self.attention(features[0], x) if self.attention is not None else features[0]
        return self.head(out)
