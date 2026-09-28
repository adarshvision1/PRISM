# Macro-class mapping

Generated from official SemanticKITTI YAML learning IDs. Macro grouping is an explicit project policy, not a property contained in the YAML. Ignored classes retain 255. Vehicle/person categories are conservative taxonomy, not measured motion.

| Raw ID | Official label | Learning ID | Macro class |
|---|---|---|---|
| 0 | unlabeled | 0 | ignored |
| 1 | outlier | 0 | ignored |
| 10 | car | 1 | dynamic-object |
| 11 | bicycle | 2 | dynamic-object |
| 13 | bus | 5 | dynamic-object |
| 15 | motorcycle | 3 | dynamic-object |
| 16 | on-rails | 5 | dynamic-object |
| 18 | truck | 4 | dynamic-object |
| 20 | other-vehicle | 5 | dynamic-object |
| 30 | person | 6 | dynamic-object |
| 31 | bicyclist | 7 | dynamic-object |
| 32 | motorcyclist | 8 | dynamic-object |
| 40 | road | 9 | drivable |
| 44 | parking | 10 | drivable |
| 48 | sidewalk | 11 | non-drivable-terrain |
| 49 | other-ground | 12 | non-drivable-terrain |
| 50 | building | 13 | static-obstacle |
| 51 | fence | 14 | static-obstacle |
| 52 | other-structure | 0 | ignored |
| 60 | lane-marking | 9 | drivable |
| 70 | vegetation | 15 | static-obstacle |
| 71 | trunk | 16 | static-obstacle |
| 72 | terrain | 17 | non-drivable-terrain |
| 80 | pole | 18 | static-obstacle |
| 81 | traffic-sign | 19 | static-obstacle |
| 99 | other-object | 0 | ignored |
| 252 | moving-car | 1 | dynamic-object |
| 253 | moving-bicyclist | 7 | dynamic-object |
| 254 | moving-person | 6 | dynamic-object |
| 255 | moving-motorcyclist | 8 | dynamic-object |
| 256 | moving-on-rails | 5 | dynamic-object |
| 257 | moving-bus | 5 | dynamic-object |
| 258 | moving-truck | 4 | dynamic-object |
| 259 | moving-other-vehicle | 5 | dynamic-object |