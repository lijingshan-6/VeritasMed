<div align="center">

<img src="docs/assets/showcase/logo.svg" width="64" height="64" alt="VeritasMed logo">

# VeritasMed

**Verifiable medical Q&A: conclusions held to the evidence, every sentence auditable.**

[![CI](https://github.com/lijingshan-6/medrag-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/lijingshan-6/medrag-agent/actions/workflows/ci.yml)
[![Live demo](https://github.com/lijingshan-6/medrag-agent/actions/workflows/pages.yml/badge.svg)](https://lijingshan-6.github.io/medrag-agent/)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)

[**Live demo**](https://lijingshan-6.github.io/medrag-agent/) · [**Experiment report**](docs/experiment-a.md) · [How it works](docs/how-it-works.md) · [Research log](docs/research.md) · [简体中文](README.zh-CN.md)

</div>

![Walkthrough: a cited answer, question coverage, a reported evidence gap and the claim audit](docs/assets/showcase/preview.gif)

## Why

In a medical answer, the sentence a reader acts on is the conclusion. On 500 PubMedQA questions,
a plain retrieval-augmented model got the facts right but left its yes/no conclusion uncited or
unsupported by its own citation in **40%** of answers - **36%** even when handed the correct
abstract. The problem is not retrieval; it is a model concluding more than its sources say.

VeritasMed binds the conclusion and each claim to original sentences, writes the answer in plain
words beside them, reports missing evidence as a gap, and lets you audit every sentence against the
source in one click.

## Results

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/experiment-a/tradeoff-dark.png">
  <img alt="On 500 PubMedQA questions, plain RAG is accurate but its conclusions are often unsupported, a strict prompt grounds conclusions but drops to closed-book accuracy, and VeritasMed does both" src="docs/assets/experiment-a/tradeoff-light.png">
</picture>

Same model, corpus and retriever for every method; all 500 official PubMedQA test questions.

| | Accuracy | Conclusion cited and supported | Cost / question | Median time |
|---|---|---|---|---|
| Plain RAG | 63.8% | 60% | $0.001 | 10 s |
| Strict-prompt RAG | 51.0% | 85% | $0.002 | 13 s |
| **VeritasMed** | **63.6%** | **84%** | $0.011 | 59 s |

- **Grounded without giving up conclusions.** A stricter prompt grounds conclusions only by answering
  "maybe" far more often, which drops it to closed-book accuracy (52.2%).
- **The audit catches errors.** It flags 187 of 191 planted material errors (97.9%) and wrongly flags
  2.0% of correct sentences; on real plain-RAG answers it catches overstatements a model judge accepts.
- **Honest about what it is not.** It is not more accurate than plain RAG, it costs about 1 cent and
  50 seconds more, and one early result was withdrawn after its automatic judge failed calibration.

Full design, statistics, adjudications and limits: [**Experiment A report**](docs/experiment-a.md).

## Features

- **Conclusion first, bound to evidence.** Each part of the question is bound to a sentence from a
  retrieved paper; a result the sources do not contain is reported as a gap, not guessed.
- **Self-check and repair.** The agent grades the evidence, rewrites weak searches and reviews its
  draft before replying, with at most two retries of each.
- **One-click claim audit.** Every claim is checked against exact source quotes; unresolved quotes,
  unchecked text and "non-significant read as no difference" are flagged, never hidden.
- **Conversations you keep.** Follow-ups, answer versions and audits stay in the browser and export
  as one file.

## Quick start

The replay runs the recorded conversations (nine real answers, twelve audits) in the browser - no
model, API key, Python or GPU. Use the [live demo](https://lijingshan-6.github.io/medrag-agent/), or
with Node.js 22.12+:

```sh
git clone https://github.com/lijingshan-6/medrag-agent.git
cd medrag-agent/frontend && npm ci && npm run replay
```

Open http://127.0.0.1:5173, pick a conversation and open **Claim check**.

<details>
<summary><b>Ask your own questions (live mode)</b></summary>

The live mode searches the three bundled papers (15 original abstract passages, CC0 / CC BY). It
needs Python 3.12 with the full dependencies (several GB, CPU is fine;
[uv](https://docs.astral.sh/uv/) recommended) and an OpenAI-compatible Flash endpoint:

```sh
uv venv --python 3.12      # then activate .venv
uv pip sync requirements.lock --torch-backend cpu
uv pip install --no-deps -e .
cp .env.example .env        # then set OPENHUB_API_KEY (and the endpoint/model if different)
python scripts/run_demo.py  # add --skip-index on later starts
```

Answers can also come from a local model (`LLM_BACKEND=ollama`, `OLLAMA_MODEL=qwen3.5:9b`); audits
always use the Flash endpoint.

</details>

## How it works

![System overview](docs/assets/showcase/system-overview.svg)

1. **Resolve** a follow-up against up to six selected earlier turns. Earlier answers help interpret
   "it" or "those results" but are never used as evidence.
2. **Retrieve** with dense and sparse BGE-M3 search, fused and reranked; match the paper the question
   names before picking passages.
3. **Plan** by binding each requested part to sentence IDs in the retrieved text; code checks that
   every quotation exists and belongs to the right paper.
4. **Generate and check** in plain words, with the bound sentences shown beside each claim; a model
   review checks support, completeness and evidence boundaries and asks for targeted repairs.

More: [how it works](docs/how-it-works.md) · [agent graph](src/medrag/agent/graph.py) ·
[audit code](src/medrag/verification/).

<details>
<summary><b>Earlier experiments</b></summary>

| Question | Result | Decision |
|---|---|---|
| Does the agent answer from the right evidence? | Held-out set, run once after freezing: **31/35** strict passes (5/15 in v0.2) | Current answer pipeline |
| How reliable is a model as a claim checker? | On 339 SciFact pairs Flash wrongly accepted **6/201** unsupported claims, MiniCheck 14/201 | Flash as the checker |
| Does a prescribed tool workflow beat reading the papers? | 31/40 vs 35/40 for direct reading and free tool use | Keep the simpler flow |
| Does fine-grained (atomic) auditing keep qualifiers? | More conditions kept (101/104 vs 91/104), fewer audits completed (26/48 vs 47/48) | Direct by default |
| Paste source sentences verbatim, or write in plain words? | Verbatim scores higher only because quotes pass a citation judge; its answers are lists of quotes | Plain words, sources beside them |

Details in the [research log](docs/research.md).

</details>

## Limitations

- A research demo, not clinical advice. Labels come from public datasets and AI-assisted review,
  not clinicians.
- PubMedQA has single-paper yes/no questions; synthesis across studies is not yet evaluated.
- The bundled index has three papers, so the live mode cannot answer arbitrary medical questions.
- A green check means a model judged the quoted text to support the claim. It is not a calibrated
  probability and does not grade study quality or resolve conflicts between papers.
- The web API has no authentication and is meant for local use; history lives in browser storage.

<details>
<summary><b>Repository layout and checks</b></summary>

| Path | Contents |
|---|---|
| `src/medrag/agent/` | LangGraph answer graph, evidence binding, follow-up resolution, model factory |
| `src/medrag/verification/` | Direct and Atomic v2 audits, exact-quote binding, numeric and significance checks |
| `src/medrag/retrieval/`, `index/` | Hybrid retrieval, reranking, Qdrant indexing |
| `src/medrag/api/` | FastAPI app: Ask WebSocket, audit, passages, saved conversations |
| `src/medrag/mcp_server/` | Optional local MCP tools (search, ask, evaluate) |
| `frontend/` | React app; `npm run replay` needs no backend |
| `data/demo/conversations/` | Three source papers, corpus and recorded conversations |
| `experiments/pubmedqa/` | Experiment A: scripts, registrations and every raw output |

Checks (none calls a model): `python -m pytest -q`, `ruff check src/`, `npm --prefix frontend test`,
`npm --prefix frontend run build`.

Earlier research data is archived at [commit 81a1519](https://github.com/lijingshan-6/medrag-agent/tree/81a1519).
See the [changelog](CHANGELOG.md) and [source attribution](data/demo/conversations/README.md).

</details>

## License

Code: [Apache-2.0](LICENSE). Datasets, papers and model weights keep their own licences; see the
[source attribution](data/demo/conversations/README.md) and the [report](docs/experiment-a.md#1-setup).
