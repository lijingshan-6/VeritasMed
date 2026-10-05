Planted-error study: 200 items, 200 audited (0 invalid plants, 0 errors); cost $4.74

| Error type | n | Detected (planted flagged) | Contradicted | False alarm (same sentence, clean) | Target not covered (planted) |
|---|---|---|---|---|---|
| number | 50 | 100% [93, 100] | 96% [87, 99] | 8% [3, 19] | 0 |
| direction | 50 | 100% [93, 100] | 96% [87, 99] | 14% [7, 26] | 0 |
| population | 50 | 96% [87, 99] | 82% [69, 90] | 6% [2, 16] | 1 |
| overreach | 50 | 78% [65, 87] | 8% [3, 19] | 12% [6, 24] | 0 |
| all | 200 | 94% [89, 96] | 70% [64, 76] | 10% [7, 15] | 1 |

Audit statuses (clean, planted): {('ok', 'ok'): 187, ('partial_error', 'ok'): 6, ('ok', 'partial_error'): 5, ('partial_error', 'partial_error'): 2}
Flagged = an audit claim overlapping the target sentence is contradicted or insufficient; 95% Wilson intervals.

Newly flagged after planting (targets accepted when clean): 167/180 = 92.8% [88, 96]

After manual adjudication (labels and reasons in adjudication.json; adjudicator: Claude, not a blinded expert):
- clean-sentence flags: {'audit_wrong': 2, 'audit_right': 13, 'source_artifact': 1, 'audit_right_strict': 3, 'debatable': 1} -> unwarranted flags 4/200 = 2.0% [1, 5]; the rest point at content the cited passages do not state
- misses: {'plant_weak': 5, 'plant_invalid': 4, 'true_miss': 4} -> detection of valid plants 187/196 = 95.4%; of material errors 187/191 = 97.9% [95, 99]
