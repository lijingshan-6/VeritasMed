# Research overview: what the evidence establishes

**English** | [简体中文](../research-overview.md)

By v0.8, VeritasMed has runnable literature Q&A, claim auditing and traceable experiments.
**It has not established sufficiently reliable whole-answer medical auditing or superiority
of the prescribed Agent workflow over the same model using tools autonomously.**
Different experiments answer different questions; their scores cannot form one system accuracy.

[Illustrated research](showcase.md) separates fixed claims, tool workflows and condition diagnostics,
with paired intervals and audit failures alongside results.

## Evidence and main findings

| Stage / question | Data and labels | Observation | Supported / unsupported interpretation |
|---|---|---|---|
| Early retrieval/answers | AI-authored 50 questions and 39 hard questions; model evaluation | Historical retrieval hits and answer self-evaluation retained | Engineering diagnostics, not expert gold or new audit reliability |
| v1.1 → v0.4: answer with necessary evidence? | 50 questions: 15 development / 35 then held out; source binding, model challenges, AI adjudication | Flash 15/15 development, 10/10 repeat, first final 31/35 | Performance under that contract; not medical safety or new verifier accuracy; final now exposed |
| v0.5: map checks to source? | 30 SciFact public labels, 48 simple controls, RAGTruth train answers/variants | 25/30 relation agreement; localization and semantic judgments diverge | Quote location and correctness must be separate; AI error review is not independent gold |
| v0.6: fixed claim/source verifier? | SciFact public dev final: 339 pairs / 247 connected groups; separate development/calibration | Flash binary 291/339, MiniCheck 279/339; false accepts 6/201, 14/201 | External labels for fixed evidence, not whole answers, clinical grades or guaranteed unseen training data |
| v0.6: whole answers/calibration? | 36 natural development answers, medical constructions, ablations, repeats | Direct/Split/Atomic complete 34/36, 35/36, 11/36; no eligible threshold | No reason to default to Atomic or show confidence; span overlap is not correct error identification |
| v0.7: why not autonomous tools? | 40 groups, named paper and eight candidate abstracts; same Flash | Read-all/autonomous 35/40 correct accepted; prescribed 31/40; all false accept 2/19 | No demonstrated structural advantage; bounded module is not full Ask or tool capability ceiling |
| v0.8 R1: parent binding? | 167 saved audits / 1,203 facts; offline exact matching | 82 recovered locations, zero regressions, 24 unresolved | Mechanical localization, not new semantic judgments; recovered old items do not become passes |
| v0.8 R2: retain numbers/conditions? | 24 groups × four AI constructions; 12 development / 12 final, plus 12 natural answers and repeats | Final Direct/v2 joint 91/104, 101/104; complete 47/48, 26/48; difference intervals include zero | More inspection, more review burden; no semantic mapping or clinical verification upgrade |
| v0.8 product demo | Three papers, three actual three-turn conversations, 12 saved audits | Missed clarification, false gap for a writing constraint, omitted mortality requirement | Demonstrable product, not an effectiveness evaluation or reference-answer set |

Full explanations: [early evaluation](../reports/evaluation_report.md), [v0.4](../reports/agent-v0.4-flash-report.md),
[v0.5](../releases/v0.5.0.md) (original historical reports),
[v0.6](reports/verification-v0.6-report.md), [v0.7](reports/verification-v0.7-report.md),
[v0.8](reports/verification-v0.8-report.md). The [data catalogue](data-catalogue.md) leads to all records,
not just selected results on this page.

## Report quality and remaining gaps

The stronger parts are retained inputs/sources, fixed contracts, failures, simple comparators
and explicit decisions from negative findings. SciFact has public human labels, but the model
may have seen public data in training. RAGTruth labels are spans rather than exhaustive
semantic adjudication. Medical constructions and AI specific-error review remain development evidence.
The old final medical questions are exposed. Provider metadata cannot prove fixed underlying weights.

## Next research decisions

1. Address omitted requirements, unnecessary gap warnings and missed clarification. Success on
   existing demonstration regressions is not an independent test result.
2. Seek new licensed, traceably labelled external semantic data for whole answers and fix the
   source view beforehand. Preserve the lack of experts rather than disguising AI votes as human labels.
3. With qualified references, compare Direct, native autonomous tools and a specific Agent change
   under the same model/source conditions. Report misses, false accepts, support recall, coverage,
   failures, tokens and latency for one question at a time.
4. Only after auditing detects target errors stably, study targeted retrieval/repair. Preserve
   original answers and evaluate repairs externally. Calibration and literature conflicts stay separate.

The [v0.9 question-coverage plan](plans/v0.9-question-coverage.md) first assesses external paper-Q&A
references, then compares direct review, structured request items and a matched-call control.
It targets completeness without inventing a new medical semantic gold set. Design only is complete;
no paid runs or reserved-set access have started. See [roadmap](verification-roadmap.md) and the
[original Flash decision](../decisions/2026-09-23-flash-research-baseline.md).
