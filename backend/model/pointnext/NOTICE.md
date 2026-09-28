# PointNeXt-S adaptation

Architecture reference: Qian et al., *PointNeXt: Revisiting PointNet++ with Improved Training and Scaling Strategies*, NeurIPS 2022.

- Official S configuration: https://github.com/guochengqian/PointNeXt/blob/master/cfgs/s3dis/pointnext-s.yaml
- Encoder/decoder reference: https://github.com/guochengqian/openpoints/blob/master/models/backbone/pointnext.py

PRISM implements stage widths 32/64/128/256/512, residual two-layer set abstraction, four stride-4 downsamplings and four feature-propagation stages. S has no additional InvResMLP blocks; those belong to deeper variants.

Adaptations: six LiDAR features, four classes, 0.5/1/2/4 m grouping radii, optional height attention, deterministic sampled centroids and radius-limited nearest neighbors instead of CUDA FPS/ball-query. This is an outdoor adaptation, not a reproduction of published accuracy or an official pretrained checkpoint. Radii are starting values, not a newly validated optimum.

Feature propagation uses the existing MIT-licensed yanx27 implementation; its LICENSE remains alongside it. The network was implemented for this project from the architecture reference without vendoring OpenPoints or its CUDA dependencies.
