# SemanticKITTI local inventory

Every listed training scan was checked for finite XYZ/intensity, binary shape and equal point/label count. Sequence 08 is excluded from training. Source hashes are in expanded_sources.json.

| Training sequence | Paired scans | Points |
|---|---:|---:|
| 00 | 434 | 52,777,150 |
| 01 | 384 | 40,636,339 |
| 02 | 412 | 51,787,338 |
| 03 | 386 | 47,872,786 |
| 04 | 271 | 34,069,557 |
| 05 | 408 | 51,045,055 |
| 06 | 384 | 46,987,852 |
| 07 | 384 | 46,577,360 |
| 09 | 380 | 47,257,364 |
| 10 | 396 | 49,874,643 |

Total: 3,839 paired training scans, 468,885,444 points. Prepared 20,000 training blocks; retained the same 600 validation blocks from 08.
