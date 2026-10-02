# Research route: establish auditing before using it to guide answers

**English** | [简体中文](../verification-roadmap.md)

The intended product is a literature workspace with follow-ups and linked questions, answer
versions, claims, original passages and audit records. Incomplete checks and genuine evidence
gaps stay visible. Research measures which checks work, where they fail and which structure
adds value over direct use of the same model. Clinical applicability and cross-paper comparability
require separate studies.

## Current stage

v0.8 has persistent conversations, original-paper demos, version-scoped audits and recomputable
records. Main negative results: the prescribed workflow has not shown an advantage, and better
qualifier localization has not established semantic reliability. Numbers live in the
[research overview](research-overview.md) and [reports](reports/README.md).

Separate three paths: full Ask generates and checks internally; independent Audit checks saved
answers; Research compares tools within fixed paper scope. The last two are not end-to-end Ask scores.

## Next version: v0.9 question coverage

Target “each sentence is cited, but the question is incompletely answered.” Map original request
items to responses and gaps, separately from claim support. Prioritize omissions, false gaps for
writing constraints and missed clarification.

The [implementation plan](plans/v0.9-question-coverage.md) defines feasibility, Direct/structured/
matched-call controls, extraction-cap diagnostics, false accepts/correct accepts, freezes and
conditions for not upgrading. Assess external references first; if unsuitable, deliver development
diagnostics rather than inventing a reliability result.

## Later stages depend on evidence

| Stage | Required finding | Prerequisite |
|---|---|---|
| One targeted answer addition | Better correction of identified omissions than direct re-answering, without new errors | Defined coverage scope; retained original/revision/external references |
| Open retrieval and autonomous tools | Independent benefit of a specific structure under matched information/budgets | Comparable data/tools; legacy JSON adapter is not native-tool ceiling |
| Natural medical semantic reliability | Whole-answer false alarms, misses, false accepts and necessary abstention | New traceable external labels, not AI votes or exposed final questions |
| Clinical grading / literature conflict | Valid populations, causal design and cross-study comparison | Dedicated methodological standards and qualified annotation, not entailment scores |

These are not promised completed v1.0 features. Structures without benefits do not become
default; simple methods may win. Flash/Direct remains default, with no routine Pro judge or
uncalibrated confidence percentage. [Protocols/failures](reports/README.md) · [Reproduction](research-reproduction.md).
