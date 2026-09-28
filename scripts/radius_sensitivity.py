from backend.model.train import BlockDataset,validate
from backend.model.pointnet2.network import PointNet2MSG
from backend.labels import ROOT
from torch.utils.data import DataLoader
import torch,json
checkpoint=torch.load(ROOT/'backend/model/weights/best.ckpt',map_location='cpu',weights_only=True)
torch.set_num_threads(4);loader=DataLoader(BlockDataset('valid'),batch_size=16);results=[]
for scale in [.75,1.0,1.5]:
    config={**checkpoint['model_config'],'radius_scale':scale};model=PointNet2MSG(**config).cuda();model.load_state_dict(checkpoint['state_dict']);score,conf=validate(model,loader,torch.device('cuda'));results.append({'radius_scale':scale,'validation_block_miou':score});print(scale,score,flush=True)
(ROOT/'data/radius_sensitivity.json').write_text(json.dumps({'method':'Inference-time radius sensitivity using the same learned weights; not independently trained architecture trials. Selected training radii remain 0.25/0.5/1.0 m.','results':results},indent=2))
