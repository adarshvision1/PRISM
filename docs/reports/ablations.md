# Measured ablations and experiment scope

The completed experiment compares five grid policies using shared predictions from the final selected checkpoint. The separate runtime sweep measures actual neural input/batch trade-offs. Neither is mislabeled a completed seven-factor Taguchi experiment.

| Policy | FPS | Leaf storage MiB | Mean cells | mIoU |
|---|---:|---:|---:|---:|
| uniform | 2.220 | 2.425 | 60,553 | 79.73% |
| distance | 2.132 | 1.898 | 47,375 | 79.51% |
| ground | 2.092 | 2.244 | 56,017 | 79.74% |
| semantic | 2.126 | 1.945 | 48,564 | 79.73% |
| prism | 2.081 | 2.294 | 57,269 | 79.73% |

## Distance coverage

| Band (m) | PRISM mIoU | Labeled points |
|---|---:|---:|
| 0–10 | 80.03% | 37,148,279 |
| 10–25 | 79.34% | 18,254,815 |
| 25–60 | 73.06% | 4,473,789 |
| 60–100 | 31.01% | 10,228 |

Ten heatmap rows represent fixed temporal intervals of sequence 08; row sample counts and absent bands are disclosed in the dashboard.

## What is and is not justified

The measured runtime recommendation is foveated1024, selected under the reported accuracy constraints. Grid defaults retain the conservative 3 m/5 cm floor and 10/25/60 m distance ceilings; no experiment establishes these as mathematically optimal.
Kaur et al., DOI 10.14429/dsj.21132, section 4.2 reports Taguchi tuning for a camera model. Seven three-level PRISM factors require a suitable verified L18/L27 design, repeated training for optimizer factors, explicit safety constraints and a confirmation run. That broader study remains uncompleted; no fabricated array, S/N result or optimality claim is included.
