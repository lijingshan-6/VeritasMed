# VeritasMed

**English** | [简体中文](README.zh-CN.md)

**Verifiable medical Q&A: conclusions held to the evidence, every sentence auditable.** Ask about
the literature, get a plain-language answer whose conclusion and claims are each bound to an
original sentence, then open an audit that checks every claim against the source and marks what is
unsupported or unchecked.

![Recorded walkthrough: conversation, answer, claim audit](docs/assets/showcase/preview.gif)

**[Open the live replay →](https://lijingshan-6.github.io/medrag-agent/)** (recorded conversations, runs in the browser, no sign-up)

React · FastAPI · LangGraph · BGE-M3 hybrid retrieval · Python 3.12 · Apache-2.0

## The result in one chart

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/experiment-a/tradeoff-dark.png">
  <img alt="On 500 PubMedQA questions, plain RAG is accurate but its conclusions are often unsupported, a strict prompt grounds conclusions but drops to closed-book accuracy, and VeritasMed does both" src="docs/assets/experiment-a/tradeoff-light.png">
</picture>

On all 500 PubMedQA test questions, with the same model and retriever for every method:

- **Plain RAG's yes/no conclusion is uncited or unsupported in 40% of answers; VeritasMed's in 16%**
  (-21.3 pp, 95% CI [-26.6, -16.1]), at the same accuracy (63.6% vs 63.8%).
- **A stricter single prompt grounds conclusions only by withholding them**: accuracy falls to 51.0%,
  the closed-book level.
- **The audit flags 97.9% of planted material errors** and wrongly flags 2.0% of correct sentences.
- The cost: about 1 cent and 50 seconds more per question. An earlier "halved" claim based on
  MiniCheck was withdrawn after calibration. [Full report →](docs/experiment-a.md)

## What it does

- **Holds its conclusion to the evidence.** The answer opens with a one-sentence conclusion, and each
  part of the question is bound to a sentence from a retrieved paper and answered in plain words beside
  it. A missing result is reported as a gap rather than guessed. (On PubMedQA, 84% of its conclusions
  were cited and supported, against 60% for plain RAG; the rest are what the audit is for.)
- **Checks itself before replying.** The agent grades the evidence, rewrites the search when it is weak, and
  reviews its own draft, with at most two retries of each.
- **Lets you audit any answer.** One click checks every claim against the source passages, with
  unresolved quotes, unchecked text and model disagreements left visible.
- **Keeps the conversation.** Follow-up questions, answer versions and their audits are stored in the
  browser and can be exported and imported as one file.

## Try it without an API key

Use the [live replay](https://lijingshan-6.github.io/medrag-agent/), or run it locally. Replay three recorded medical conversations (nine real answers and twelve audits) in the
browser. No model, Python, GPU or database is needed, only Node.js 22.12+:

```sh
git clone https://github.com/lijingshan-6/medrag-agent.git
cd medrag-agent/frontend
npm ci
npm run replay
```

Open http://127.0.0.1:5173, pick a conversation, select a question and press **Audit**.

## Ask your own questions

The live mode searches the three bundled papers (15 original abstract passages, CC0 / CC BY).
It needs Python 3.12 with the full dependencies (several GB, CPU is fine; [uv](https://docs.astral.sh/uv/)
recommended) and an OpenAI-compatible Flash endpoint. From the repository root:

```sh
uv venv --python 3.12      # then activate .venv
uv pip sync requirements.lock --torch-backend cpu
uv pip install --no-deps -e .
cp .env.example .env        # then set OPENHUB_API_KEY (and the endpoint/model if different)
python scripts/run_demo.py  # add --skip-index on later starts
```

Answers can also come from a local model (`LLM_BACKEND=ollama`, `OLLAMA_MODEL=qwen3.5:9b`);
audits always use the Flash endpoint.

## How it works

![System overview](docs/assets/showcase/system-overview.svg)

1. **Resolve** the follow-up against up to six selected earlier turns. Earlier answers help
   interpret "it" or "those results" but are never used as evidence.
2. **Retrieve** with dense and sparse BGE-M3 search, merged with reciprocal rank fusion, then rerank.
   Match the paper the question names before picking passages.
3. **Plan the answer** by binding each requested part to sentence IDs in the retrieved text. Code checks
   that every quotation exists and belongs to the right paper.
4. **Generate and check.** The answer is written in plain words, with the bound source sentences shown
   beside each claim. A model review checks support, completeness and evidence boundaries, and asks
   for targeted repairs.

Details: [how it works](docs/how-it-works.md) · [agent graph source](src/medrag/agent/graph.py).

## What the evaluations showed

| Question | Result | Decision |
|---|---|---|
| Does VeritasMed ground its conclusions better than plain RAG? (500 PubMedQA questions) | Conclusion uncited or unsupported: **40.1% vs 15.8%**; accuracy 63.8% vs 63.6% | The pipeline's measurable value; [report](docs/experiment-a.md) |
| Can one strict prompt do the same? | Grounds conclusions (15.1%) but accuracy drops to **51.0%** | Keep the multi-step generator |
| Does the audit catch errors? | Planted: **187/191** material errors flagged, 4/200 unwarranted flags; it also catches overstatements in real plain-RAG answers | Audit as the second line of defence |
| Paste source sentences verbatim (v0.8) or write in plain words? | Verbatim scores higher only because quotes pass a citation judge and it answers "maybe" less; its answers are lists of quotations | Plain words, sources shown beside them |
| Does the agent answer correctly from the right evidence? | Development questions: 5/15 strict passes in v0.2, 15/15 in v0.4 (pipeline and model changed). Held-out set, run once after freezing: **31/35** | Current answer pipeline |
| How reliable is a model as a claim checker? | On 339 public SciFact pairs, Flash wrongly accepted **6/201** unsupported claims; MiniCheck 14/201 | Flash as the default checker |
| Does a prescribed tool workflow beat simply reading the papers? | 31/40 vs 35/40 for direct reading and for free tool use | Keep the simpler flow |
| Does fine-grained (atomic) auditing keep qualifiers? | Keeps more conditions (101/104 vs 91/104) but completes fewer audits (26/48 vs 47/48) | Direct by default, Atomic v2 optional |

Experiment A is reported in full in [docs/experiment-a.md](docs/experiment-a.md); earlier experiments and
what each version changed are in the [research summary](docs/research.md).

## Limitations

- This is a research demo, not clinical advice. Labels come from public datasets and AI-assisted
  review, not clinicians.
- PubMedQA questions are single-paper yes/no questions; it does not test synthesis across studies.
- The bundled index has three papers, so it cannot answer arbitrary medical questions.
- A green check means a model judged the quoted text to support the claim. It is not a calibrated
  probability, and the audit does not grade study quality or resolve conflicts between papers.
- The web API has no authentication and is intended for local use. History lives in browser
  storage; export anything you want to keep.

## Repository

| Path | Contents |
|---|---|
| `src/medrag/agent/` | LangGraph answer graph, evidence binding, follow-up resolution, model factory |
| `src/medrag/verification/` | Direct and Atomic v2 audits, exact-quote binding, numeric checks |
| `src/medrag/retrieval/`, `index/` | Hybrid retrieval, reranking, Qdrant indexing |
| `src/medrag/api/` | FastAPI app: Ask WebSocket, audit, passages, saved conversations |
| `src/medrag/mcp_server/` | Optional local MCP tools (search, ask, evaluate) |
| `frontend/` | React app: conversations, answers, sources, audit view; `npm run replay` needs no backend |
| `data/demo/conversations/` | Three source papers, corpus, and the recorded conversations |
| `experiments/pubmedqa/` | Experiment A: scripts, registrations and every raw output |

Checks: `python -m pytest -q`, `ruff check src/`, `npm --prefix frontend test`,
`npm --prefix frontend run build`. None of them calls a model.

The research history (datasets, all experiment outputs, version reports) is archived at
[commit 81a1519](https://github.com/lijingshan-6/medrag-agent/tree/81a1519). See the
[changelog](CHANGELOG.md) and the [source attribution](data/demo/conversations/README.md).
