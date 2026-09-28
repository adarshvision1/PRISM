import torch
from torch import nn
class HeightAttention(nn.Module):
    """Point-feature height emphasis; not CurbNet's sparse MSCA."""
    def __init__(self,channels):
        super().__init__(); self.gate=nn.Conv1d(2,channels,1)
    def forward(self,features,inputs):
        return features*torch.sigmoid(self.gate(inputs[:,[2,4],:]))
