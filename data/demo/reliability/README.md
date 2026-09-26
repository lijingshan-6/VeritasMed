# GRADE audit diagnostics

Source and original Agent output: [`../medical/`](../medical/README.md),
Seaquist et al. (2024), PMC11567630, CC0. This directory holds new audits of the same
actual answer plus two explicitly authored controls. It has no independent gold labels.

- `protocol.json`: input hashes and both methods frozen before these audits.
- `grade-original-*`: unchanged original Ask answer and supplied passages.
- `grade-arm-swap-*`: only the first severe-hypoglycemia arm values are swapped.
- `grade-evidence-gap-*`: original answer, only the supplied background passage retained.
- `*-direct.json` / `*-atomic_v1.json`: actual calls, raw outputs, bindings and failures.
- `*-minicheck.json`: separately recorded local scoring of normalized facts; the
  original Flash record is unchanged. Input hashes link each supplemental result.
- `catalogue.json`: actual available methods and recorded statuses for UI replay.

| Saved input | Direct | Atomic |
|---|---|---|
| Unchanged Agent answer | 4 supported | 13 supported, 9 unchecked/unresolved |
| Constructed arm swap | 4 supported, 1 contradicted | 14 supported, 1 contradicted, 9 unchecked/unresolved |
| Constructed evidence gap | 3 supported, 9 insufficient | 12 insufficient, 11 unchecked/unresolved |

MiniCheck completed 22, 24 and 23 supplementary fact checks respectively. Both constructed
inputs contain two checker disagreements. Different extraction granularity makes supported
counts incomparable as an accuracy measure; unresolved facts stay in the saved records.

MiniCheck compares standalone parsed facts with the supplied texts. Flash's contextual
audit also reads the whole answer. Their disagreement is a review signal, not a vote,
calibrated probability or strict same-task model comparison. The controlled same-target
comparison is separately recorded under `data/verification/v06/ablations`.

These are demonstrations. A constructed arm swap/evidence gap is not a natural Agent error
rate. The unchanged answer's successful labels do not establish exhaustive extraction or
clinical validity. See [the walkthrough](../../../docs/research-demo.md).
