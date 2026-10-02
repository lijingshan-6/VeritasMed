# Data, experiments and historical artifacts

**English** | [简体中文](../../data/README.md)

Materials have different dates and label provenance. `golden` does not mean expert truth;
`final` does not mean still unexposed. Start with [research overview](research-overview.md).
Directory-specific source cards and raw records remain in their original language.

## Directory roles

| Directory | Content and evidence status | Explanation |
|---|---|---|
| [golden](../../data/golden) | Earlier AI-generated 50 questions / 39 hard questions; historical, not current verifier reliability evidence | Original [evaluation](../reports/evaluation_report.md) |
| [eval](../../data/eval) | Earlier retrieval/answer/Agent outputs, candidates, hashes and reports | Original [v0.1 review](https://github.com/lijingshan-6/medrag-agent/blob/v0.8.0/docs/release-review.md) |
| [benchmark/veritasmed_v1](../../data/benchmark/veritasmed_v1) | First source-bound dataset, generation/selection/model review and baseline | Original [data card](../../data/benchmark/veritasmed_v1/dataset_card.md) |
| [benchmark/veritasmed_v1_1](../../data/benchmark/veritasmed_v1_1) | 50 questions, 15 development / 35 then reserved; anchors, model challenges, AI development adjudication; no expert medical gold | Original [card](../../data/benchmark/veritasmed_v1_1/dataset_card.md), [Flash report](../reports/agent-v0.4-flash-report.md) |
| `benchmark/veritasmed_v1_1/v04_*`, `deepseek_*` | Qwen/Flash/Pro rounds, failures/balance blocks/repeats/first final; `runtime_code/` snapshots | [History](history.md) |
| [verification/scifact_pilot](../../data/verification/scifact_pilot) | 30 public-label adaptation pairs | Original [pilot](../reports/verification-v0.5-pilot.md) |
| [verification/controlled_v1](../../data/verification/controlled_v1) | 48 simple constructed controls, multiple verifiers | Original [diagnostics](../reports/verification-v0.5-diagnostics.md) |
| [verification/ragtruth_v1](../../data/verification/ragtruth_v1) | 24 train natural answers, Direct/Split, 60 official test reserved-source metadata | Original [whole-answer report](../reports/verification-v0.5-answer-audit.md) |
| [verification/context_v1](../../data/verification/context_v1) | 126 Context/metatext development, ablation and repeat calls | Original [context report](../reports/verification-v0.5-context-audit.md) |
| [verification/quote_v2](../../data/verification/quote_v2), [specific_error_v2](../../data/verification/specific_error_v2) | Exact-location replay, 36 calls, AI specific-error review; not independent gold | Original [specific-error report](../reports/verification-v0.5-specific-errors.md) |
| [verification/gateway_probe](../../data/verification/gateway_probe) | Provider identity/token observations, not underlying-weight authentication | [Gateway observations](verification-gateway-observations.md) |
| [verification/v06](../../data/verification/v06) | Fixed SciFact targets, MiniCheck, calibration, medical constructions, natural answers, repeats/ablations, label sensitivity | [v0.6 report](reports/verification-v0.6-report.md), original [artifact index](../../data/verification/v06/README.md) |
| [verification/v07](../../data/verification/v07) | Two 20-query development rounds / 40 final; three-arm named-paper tools | [v0.7 report](reports/verification-v0.7-report.md), original [artifact index](../../data/verification/v07/README.md) |
| [verification/v08](../../data/verification/v08) | Exposure snapshot, R1 location replay, 348 R2 audits, context development | [v0.8 report](reports/verification-v0.8-report.md), original [artifact index](../../data/verification/v08/README.md) |
| [demo](../../data/demo) | Authored UI fixtures and actual saved inference are labelled separately; excluded from reliability scores | Original [conversation](../../data/demo/conversations/README.md), [medical](../../data/demo/medical/README.md) cards |

## Reading an experiment

Read protocol/manifest (planned items and labels) → freeze/environment (then-current method/settings)
→ predictions/raw/attempts (actual outputs and failures) → metrics/summary → report.
Earlier work does not always have the later artifact format; do not invent a retrospective
“frozen before calls” timestamp. Missing historical information stays missing rather than inferred
from today's configuration.

Repeats, constructions from one paper and different model calls are not independent samples.
Failures stay in original denominators. Public human labels, author source-based constructions,
AI development review, pure location and model self-evaluation are separate evidence types.

## Preservation and reproduction

- Do not alter raw outputs/failures/old labels/historical code/publisher XML bytes. Errata belong
  in separate explanations and sensitivity analyses.
- `summary.json`, `*-metrics.json` and some Markdown are recomputable derivatives.
  See [reproduction](research-reproduction.md); do not manually polish numbers.
- New experiments need new run directories. Exposed historical final sets now support repeats/regressions only.
- 60 RAGTruth official test sources remain unused as of v0.8; later use needs a new protocol.
- `.benchmark-runtime/`, `.demo-runtime/`, large raw corpora, indexes, weights, credentials and
  user conversations are not distributed by Git. Old v1.1 full retrieval needs its original
  corpus; the current three-paper demo rebuilds from repository snapshots. Distinguish these scopes.
- Apache-2.0 code licensing does not relicense papers/datasets; see [attribution](research-sources.md).

At the v0.8 review, saved research texts dominated tracked artifact sizes: v08 about 22 MiB,
v06 12.5 MiB, v1.1 11.3 MiB. Keeping inspectable evidence is more useful than deleting it for
a flattering table; originals were not compressed or rewritten to reduce size.
