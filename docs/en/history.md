# Version history and experimental reading order

**English** | [简体中文](../history.md)

Use the [documentation entrance](README.md) for current behavior. This page separates research
stages, candidates and actual Git tags. “Current” and “final” in old records refer to their dates.
Maintenance does not retag published versions. Linked original historical records retain their language.

| Stage | Delivery | Main records |
|---|---|---|
| v0.1 / v0.2 | Candidate/stage records, no same-name tag | [v0.1](../releases/v0.1.0.md), [v0.2](../releases/v0.2.0.md), [archive](../archive/README.md) |
| v0.3 | v0.3.0 | [Release](../releases/v0.3.0.md), [benchmark v1.1](../reports/benchmark-v1.1-report.md), [results](../reports/agent-v0.3-report.md) |
| v0.4 | v0.4.0; Qwen candidate followed by Flash | [Candidate](../reports/agent-v0.4-report.md), [repair](../reports/agent-v0.4-repaired-report.md), [models](../reports/agent-model-comparison-report.md), [Flash](../reports/agent-v0.4-flash-report.md), [release](../releases/v0.4.0.md) |
| v0.5 | v0.5.0 | [Release](../releases/v0.5.0.md), [whole answers](../reports/verification-v0.5-answer-audit.md), [specific errors](../reports/verification-v0.5-specific-errors.md) |
| v0.6 + v0.7 | Together in v0.7.0; no v0.6.0 tag | [v0.6](reports/verification-v0.6-report.md), [v0.7](reports/verification-v0.7-report.md), [release](../releases/v0.7.0.md) |
| v0.7.1 | Restore Ask-centered product | [Decision](../decisions/2026-09-27-conversation-first-product.md), [release](../releases/v0.7.1.md) |
| v0.8 | v0.8.0: persistent conversations, per-version audit, qualifiers | [Release](../releases/v0.8.0.md), [report](reports/verification-v0.8-report.md), [worklog](../archive/worklogs/development-v0.8-worklog.md) |
| Post-v0.8 maintenance | Working tree; CHANGELOG Unreleased | [Maintenance record](../milestone-v0.8-review.md), [next plan](plans/v0.9-question-coverage.md) |

All v0.4 answers, failures, balance blocks, repeats and first final runs remain in the original
reports and [Flash worklog](../archive/worklogs/agent-v0.4-flash-worklog.md), not a best-result selection.
v0.6/v0.7 protocol revisions are in the [shared log](../archive/worklogs/research-v0.6-v0.7-worklog.md);
first tool failures remain in `data/verification/v07/development-original/`.

Fixed Git versions retain old paths. Current links/generators follow moved documents; historical
JSON paths retain their original identity. See the [archive](../archive/README.md). Do not rewrite
old protocols using today's code or treat exposed final questions as unseen.
