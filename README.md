# VeritasMed

**Ask a medical-literature question. Inspect each claim. Follow it back to the source.**

VeritasMed is a React + FastAPI + LangGraph research showcase with literature retrieval,
cited answers and claim auditing within the question-and-answer workspace. The panel exposes exact answer/source
passages, unsupported statements, unresolved quotations and unchecked text. It is not a
clinically validated assistant.

**v0.8.0 — Persistent conversations with an audit attached to each answer.**

Ask follow-up questions, revisit answer versions, inspect exact source passages and keep the
original audit records. Direct / Flash remains the default. Atomic v2 exposes qualifier anchors
and unresolved interpretation; it is an experiment, not a demonstrated upgrade in clinical reliability.

Python 3.12 · Node.js 22.12+ · Apache-2.0 code · [Source attribution](docs/research-sources.md)

[Use the app](docs/conversation-guide.md) · [Current code map](docs/architecture.md) ·
[What the research establishes](docs/research-overview.md) · [Data catalogue](data/README.md) ·
[Version history](docs/history.md)

![Actual saved GRADE conversation, with turn history and original source passages](docs/assets/v08-conversation.png)

Actual saved inference from the three-paper demonstration; no clinical accuracy is implied.

## Start with Ask: real recorded conversations, no key

Install [uv](https://docs.astral.sh/uv/) and Node.js 22.12+, then:

```sh
git clone --branch v0.8.0 https://github.com/lijingshan-6/medrag-agent.git
cd medrag-agent
uv venv --python 3.12
uv pip install -r requirements-audit.txt
uv pip install --no-deps -e .
```

Or download the [v0.8.0 source ZIP](https://github.com/lijingshan-6/medrag-agent/archive/refs/tags/v0.8.0.zip).
Activate the environment:

| Shell | Command |
|---|---|
| Windows PowerShell | `.\.venv\Scripts\Activate.ps1` |
| macOS / Linux | `source .venv/bin/activate` |

```sh
python scripts/run_showcase.py
```

Open **http://127.0.0.1:5173/**. The launcher installs frontend dependencies if needed;
ports **8000 and 5173** must be free. Ctrl+C stops both services. If PowerShell blocks activation,
use `.\.venv\Scripts\python.exe scripts/run_showcase.py` directly.

Choose a **SAVED INFERENCE** conversation. Three real medical papers support three recorded
conversations of three questions each. Select a turn, inspect its complete answer and sources,
then click **Audit** and switch **Saved runs**. **Back to answer** keeps the conversation.
Export/import preserves questions, versions, source snapshots, traces and all attached audits.

Replay needs **no model key, GPU, Qdrant or dataset download** after dependency installation.
It reads actual saved output, including refusals, partial answers and incomplete judgments. It accepts no
new questions or model calls. To ask your own questions, use the full setup below.

[Conversation guide](docs/conversation-guide.md) ·
[Original papers, licenses and fixed questions](data/demo/conversations/README.md) ·
[v0.8 results and limits](docs/reports/verification-v0.8-report.md)

## Optional standalone audit and research workspace

```sh
python scripts/run_audit_demo.py
```

Open **http://127.0.0.1:5174/audit** (API **8001**). This separate workspace replays the earlier
GRADE audits, constructed error controls, MiniCheck diagnostics and controlled research comparisons.
It also permits new audits after configuring Flash. Ask at **5173** remains the main product;
Audit lab and Research are supporting tools. Neither page replaces conversational Ask.

[Audit guide](docs/audit-demo.md) · [Historical research walkthrough](docs/research-demo.md)

Optional: download pinned RAGTruth texts for the nonmedical development replays:

```sh
python scripts/verification/answer_benchmark.py download
```

## Run a new audit

Copy `.env.example` to `.env` and configure a compatible gateway. All current research roles
use **Flash**; there is no automatic Pro fallback:

```dotenv
LLM_BACKEND=openhub
OPENHUB_BASE_URL=https://www.cun.ai/v1
OPENHUB_API_KEY=your-gateway-key
OPENHUB_MODEL=DeepSeek-V4.1-Flash
OPENHUB_REASONING_EFFORT=high
OPENHUB_MAX_TOKENS=32768
LLM_TIMEOUT_SECONDS=240
```

Keep real keys in the ignored local `.env`. Availability and model names depend on your provider.
In **Audit your own answer**, enter an answer and its sources, then choose **Run new audit**.
This sends those texts to the configured endpoint. The audit service does not save submissions;
use **Export audit JSON** to retain a result. Do not submit personal health information.

**Direct Flash remains the default.** Atomic v1/v2, Split, Context + meta and Exact quotes v2 are experimental
alternatives. Their existence does not establish better semantic accuracy. Unique text binding
proves where a quote occurs; it cannot prove a judgment is correct.

## Compare three research workflows

Open **http://127.0.0.1:5174/research** in the same lightweight service. Three seeded development
examples replay **Read all documents**, **Autonomous tools** and **Structured workflow** with
their actual answers, tool traces, citations and usage. The final result table uses a separate
40-query comparison, not the three showcase examples. Export all traces or transfer an unchanged
answer and its candidate sources into Audit; transfer alone makes no model call.

The task is narrowly defined: does a **named paper** support a claim, within eight fixed candidate
abstracts? The autonomous and structured methods share search/read/verify tools and a six-model-call
limit, including calls inside verification. The autonomous method uses an application-level JSON
action protocol. This experiment does not establish an advantage for the full medical Ask graph.

[Workflow walkthrough](docs/research-demo.md) · [Research reproduction](docs/research-reproduction.md) ·
[Scope decision](docs/decisions/2026-09-26-v07-research-scope.md)

## Run the full medical Ask → Audit flow

The complete retrieval stack needs several GB of dependencies and BGE model downloads.
From the root, install it into the same Python 3.12 environment (or a fresh one):

```sh
uv pip sync requirements.lock --torch-backend cpu
uv pip install --no-deps -e .
python scripts/run_demo.py --conversations
```

Stop the replay launcher first, keep the Flash configuration above, then open
**http://127.0.0.1:5173/**. This runs BGE-M3 retrieval, reranking and the actual LangGraph Agent
on **15 original abstract sections from three papers**. You can ask new questions or use the
fixed questions in the [demo protocol](data/demo/conversations/protocol.json).

Keep **Use selected history** enabled for follow-ups. The resolver uses up to six whole prior
turns to understand references; every answer retrieves evidence anew. Select an older turn to
continue from it. **Re-run** appends an answer version, and **Run audit** appends a separate audit
for that exact version. Refresh restores browser history. A new question retains earlier answers.

The launcher uses `.demo-runtime/conversation-qdrant` and `medrag_conversation_demo`, separate
from research indexes. Later starts can use `python scripts/run_demo.py --conversations --skip-index`.
The first question includes local model loading and may take longer. Only abstracts are indexed;
this tiny collection does not supply evidence for arbitrary medical questions.

The earlier one-paper GRADE setup remains available with `python scripts/run_demo.py --medical`.
See the [source manifest and rebuild recipe](data/demo/conversations/README.md) for attribution,
text normalization and preserved XML snapshots.

The earlier three-summary fixture remains available with `python scripts/run_demo.py`.
For a browser-only authored UI example: `cd frontend`, `npm ci`, `npm run dev`, then open
`http://127.0.0.1:5173/?demo=1`. Guided answers and animated steps are written fixtures,
not actual inference. [Runtime configuration](docs/configuration.md)

## What this version delivers

- **Persistent conversations:** bounded contextual follow-ups, ambiguity clarification, local history,
  answer versions, per-answer audits and complete conversation export/import.
- **Literature Ask:** dense/sparse retrieval, reranking, requested-study matching, source-bound
  answer components, citations, explicit gaps and bounded answer repair from v0.4.
- **Answer audit within Ask:** claim extraction and supported / contradicted / insufficient
  judgments against supplied text, with answer/source navigation and original-paper links.
- **Experimental Atomic v2:** unique parent-scoped fragment binding, exact qualifier anchors,
  literal numeric omissions, duplicates and compound/uncertain facts retained for review.
  The original Atomic v1 and its historical results remain available.
- **Visible failure boundaries:** missing/ambiguous quotes, request failures, uncovered text and
  extracted-claim limits stay visible. No uncalibrated confidence percentage in the audit panel.
- **Inspectable records:** actual model outputs, source fingerprints, invocation metadata,
  unchanged Ask transfers, saved replay and JSON export.
- **Research with retained failures:** public annotated data, controlled diagnostics, ablations,
  repeat runs and concrete-error review. Reports include negative findings.
- **Comparable tool workflows:** shared bounded tools, a direct-reading baseline, actual traces,
  externally labelled task results and all planned cases in the denominator.

```mermaid
flowchart LR
  Q[Question] --> R[Retrieve and rerank]
  R --> A[Generate cited answer and review gaps]
  A --> H[Open Audit within the current answer]
  H --> V[Check the unchanged answer and returned sources]
  V --> U[Claims, original passages, failures and JSON export]
  U --> Q
```

[Actual Agent workflow](docs/agent-workflow.md) · [Research route](docs/verification-roadmap.md)

## What we measured

v0.8 separates mechanical localization, constructed qualifier diagnostics and natural development
answers. The offline parent-binding replay recovers 82 fact locations across 167 saved audits,
with zero binding regressions; it adds no semantic judgment. Source-use inventory leaves too few
fresh public labels for a new semantic generalization comparison. Direct stays the default.

All **348 scheduled R2 audits** are saved (577 model calls). On the final 12 source groups /
48 constructed answers:

| Method | Fully completed audits | Targets with all anchors in one claim | Number + target conditions retained |
|---|---|---|---|
| Direct | 47/48 | 91/104 | 83/96 |
| Atomic v1 | 26/48 | 81/104 | 71/96 |
| Atomic v2 | 26/48 | 101/104 | 93/96 |

These are mechanical diagnostics on AI-authored constructions, **not semantic accuracy**.
V2 makes conditions more inspectable but adds review burden; source-group intervals for its
co-presence and numeric-retention differences include zero. In the separate 12-answer natural
development sample, Direct / v2 complete 12/12 and 3/12, with the same 8/12 annotated error spans
overlapped by warnings. Completion contracts differ; span overlap does not establish specific-error detection.

See the [v0.8 report](docs/reports/verification-v0.8-report.md), [localization results](docs/reports/verification-v0.8-localization.md)
and [source inventory](docs/reports/verification-v0.8-exposure.md).

<details>
<summary>Preserved v0.4–v0.7 measurements and their separate evaluation contracts</summary>

The following figures are the preserved **v0.6/v0.7** research results, not v0.8 re-evaluations.

The completed fixed-claim study uses **339 pairs from 247 connected source groups** in SciFact's
public development set. Inputs, methods and thresholds were frozen before this evaluation;
this is not the dataset's private test or a clinical validation.

| Fixed verifier | Completed | Correct binary decisions | Non-support accepted | Supported recalled |
|---|---|---|---|---|
| Flash | 339/339 | 291/339 | 6/201 | 96/138 |
| MiniCheck-Flan-T5-Large | 339/339 | 279/339 | 14/201 | 92/138 |

MiniCheck's false-acceptance rate minus Flash's was **+3.98 percentage points**, with a paired
source-group 95% interval of **+0.49 to +8.11**. The support-recall difference was −2.90 points
with an interval of −12.16 to +6.02. Its faster local scoring did not establish a better verifier.
The independently chosen calibration policy had **no eligible acceptance threshold**. Final
scores are not used to choose a replacement threshold or a displayed confidence percentage.

For 36 natural development answers, Direct / Split / Atomic fully completed **34/36, 35/36 and
11/36** answers. Atomic exposes useful structure, but also ambiguous fragments, uncertain splits
and qualifier omissions. Repeated calls changed whether an answer received an alarm on 2/12
sources for Direct and 4/12 for Atomic. Error-span overlap is not semantic verification accuracy.
**Direct remains the default.**

The separate frozen **40-query workflow comparison** found:

| Workflow | Completed | Correct accepted binary decisions | Non-support accepted | Supported recalled | Model calls / query |
|---|---|---|---|---|---|
| Read all documents | 40/40 | 35/40 | 2/19 | 18/21 | 1.0 |
| Autonomous tools | 40/40 | 35/40 | 2/19 | 18/21 | 3.4 |
| Structured workflow | 36/40 | 31/40 | 2/19 | 15/21 | 2.0 |

**The structured verification step did not improve this comparison.** It retained four original
answers for review: three correctly supported claims, and one genuine contradicted/insufficient
disagreement that was already correct under the binary score. Its draft score was 35/40. It used
fewer reported tokens than direct reading, but took longer and retained fewer correct supports.
The first development run exposed a broken action protocol; all its records remain available,
and the repaired autonomous baseline was frozen before these final questions were run.

[Audit reliability report](docs/reports/verification-v0.6-report.md) ·
[Workflow results and all 40 cases](docs/reports/verification-v0.7-report.md)

Earlier v0.5 observations remain available for context:

| Historical development experiment | Observation | Interpretation |
|---|---|---|
| SciFact pilot, 30 fixed pairs | 25/30 label agreement | Small public-label adaptation pilot |
| 48 constructed diagnostics, three variants | All 48/48; structured calls used more tokens | No demonstrated gain; not expert gold |
| RAGTruth pilot, 24 answers | Direct / Split overlapped 14/15 errors; warnings on 9/12 and 7/12 unmarked answers | Span hits coexist with substantial disagreements |
| Context experiment, 126 calls | 123 complete; broader spans raised some hit metrics | No established semantic verification gain |
| Quote-v2 experiment, 36 calls | Both whole-answer methods hit 3/5 errors; fixed binary targets 8/8, including four easy controls | Binding improved; whole-answer judgments still vary |

Tasks and denominators differ; do not pool these into an accuracy percentage. The 33-error
specific-issue review is **AI development review**, not independent expert validation.
The 60 reserved RAGTruth test source groups remain unused. No calibrated reliability, clinical
evidence grading or advantage over a strong model with the same autonomous tools is claimed.

[Historical v0.5 interpretation](docs/releases/v0.5.0.md) · [Quote-v2 results](docs/reports/verification-v0.5-specific-errors.md)

The historical **v0.4** medical answer evaluation achieved development 15/15, declared repeats
10/10 and first held-out test **31/35** under its own contract. Those 35 questions are now exposed;
the scores do not measure this new audit panel. Four failures and AI-review limitations
remain in the [v0.4 report](docs/reports/agent-v0.4-flash-report.md).

</details>

## Practical limits and repository map

Services bind to loopback. The web API has no public-user authentication or multi-tenant
isolation; keep it as a local showcase. Full Ask checkpoints can retain questions and answers.
The Ask request deadline is 300 seconds; a synchronous model call already in flight may
finish after Stop. Responses can omit qualifiers or misinterpret a source despite a green check.

Windows is the local demonstration platform. GitHub Actions runs the existing Ubuntu checks;
Docker and macOS/Linux browser use have not been exercised on the release host. Research
corpora, weights, local indexes and credentials are excluded. The bundled medical XML snapshots retain their
CC0 or CC BY attribution. Small SciFact excerpts, bundled candidate abstracts and actual source/tool
responses are also retained for inspection; they keep their [upstream licenses](docs/research-sources.md).

| Path | Purpose |
|---|---|
| `src/medrag/agent/` | Question-answer graph, evidence binding and model backends |
| `src/medrag/verification/` | Independent fixed-evidence and whole-answer auditors |
| `src/medrag/api/`, `frontend/` | API and interactive audit/Ask interface |
| `data/demo/conversations/` | Three-paper corpus, fixed questions, raw streams and complete conversation exports |
| `data/demo/medical/` | Original source, actual Ask stream and exported audit |
| `data/demo/reliability/`, `data/demo/research/` | Saved atomic medical audits and shared-tool comparisons |
| `data/verification/` | Frozen audit experiments and offline reports |
| `data/benchmark/veritasmed_v1_1/` | Historical medical benchmark and saved reviews |
| `docs/` | Startup, research limits, plans and release notes |

Existing offline checks: `python -m pytest -q`, `ruff check src/`, `npm --prefix frontend test`,
`npm --prefix frontend run build`. They make no paid model calls. Live tests require `--run-live`.

[Documentation index](docs/README.md) · [Medical demo](docs/medical-demo.md) ·
[v0.8 release](docs/releases/v0.8.0.md) · [Next: v0.9 question coverage](docs/plans/v0.9-question-coverage.md) · [Changelog](CHANGELOG.md) · [License](LICENSE)
