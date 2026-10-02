# Illustrated system and node guide

**English** | [简体中文](../system-guide.md)

Read this guide directly on GitHub: move from modules to node internals, then compare an actual execution.
Diagrams explain current code and saved records. Product entry points, Agent behavior and research scores
remain unchanged.

## 1. Separate three workflows first

![Conversation, retrieval answers, independent audit and research comparison](../assets/showcase/system-overview.svg)

| Workflow | Input and responsibility | Relationship |
|---|---|---|
| Ask | Question and explicitly selected history; fresh retrieval, answer generation and bounded internal checking/repair | Conversational entrance producing answer versions and sources |
| Independent Audit | One version's unchanged answer and supplied sources; claim verification, exact locations and unresolved judgments | Opened inside an answer; currently does not control Ask repair |
| Research | Same model, eight candidate abstracts and a named-paper question; three tool workflows | Separate bounded experiment; transfers original answers/sources to Audit, without running the full Ask graph |

Models, local retrieval and program rules have different responsibilities. The browser retains conversations
and versions; compatible checkpoint history is a separate mechanism. See [architecture](architecture.md)
and the [claim illustration](showcase.md#what-a-claim-audit-checks).

## 2. How nodes connect

![Complete Ask nodes and bounded loops read from current source](../assets/system-guide/nodes-en.svg)

The diagram contains all 11 nodes and branches registered in `graph.py`, plus START / END. The API resolves
follow-ups before entering the graph; clarification bypasses retrieval. Colors indicate responsibilities.
A mixed node may contain several model/program steps.

The main path plans, retrieves, reranks and binds answer components. Retrieval rewriting is on the right;
targeted repair and history helpers are below. Both loops have budgets. AST supplies connections,
thresholds, budgets and source locations; explanatory text is maintained manually.

### Two decision points

| Decision | Current program condition | Result |
|---|---|---|
| `grade` | `relevance_score` meets type threshold: factual 0.6 / synthesis 0.75 / multihop 0.8; unknown type defaults to 0.75 | Enter `generate` |
| `grade` | Threshold missed and `iterations < 2` | `rewrite → retrieve`; otherwise best-effort generation |
| `check` | `faithful = true` | Enter `append_history` |
| `check` | `faithful = false` and `regen_count < 2` | `inc_regen → generate` |
| `check` | Failed judgment and exhausted repair budget | Preserve issues, enter `append_history`, then exit or follow the history-summary branch |

Relevance and self-check labels combine model judgments and narrow rules, not calibrated medical confidence.
See [branch source](../../src/medrag/agent/graph.py) and [budget constants](../../src/medrag/agent/nodes/constants.py).

## 3. What happens inside key nodes

![grade, generate and check: inputs, model steps, program steps, outputs and branches](../assets/system-guide/node-logic-en.svg)

These nodes connect retrieved papers to an answer with attributable evidence:

- `grade` turns user requirements into components. The model selects sentence IDs; program binding resolves original quotes and retains gaps.
- `generate` writes cited claims by component. Program rules constrain source/component identities and preserve or recover key details.
- `check` reads the question, outline, answer and sources to review support, completeness and boundaries. Additional narrow numeric checks and repair targets govern the next round.

Exact binding establishes where a sentence occurs, not whether it supports a conclusion. Reusing the same
model across stages does not make self-check independent expert validation. [Ask workflow](agent-workflow.md)
details generation constraints and failures.

### Nodes and state fields at a glance

| Node | Main output / responsibility | Source |
|---|---|---|
| `route` | `query_type`, `search_queries`, study scope; preserve original question | [planning.py](../../src/medrag/agent/nodes/planning.py) |
| `retrieve` | `retrieved_chunks`, `retrieval_groups`; hybrid candidates | [retrieval.py](../../src/medrag/agent/nodes/retrieval.py) |
| `rerank` | Reranked candidates, `selected_sources`, unmatched source requests | [retrieval.py](../../src/medrag/agent/nodes/retrieval.py) |
| `grade` | `answer_components`, `relevance_score`, gaps and rewrite hints | [grading.py](../../src/medrag/agent/nodes/grading.py) |
| `rewrite` | New query, `iterations` and accumulated rewrites | [planning.py](../../src/medrag/agent/nodes/planning.py) |
| `generate` | `answer`, `citations`, `answer_claims`, coverage and binding issues | [generation.py](../../src/medrag/agent/nodes/generation.py) |
| `check` | `faithful`, `faithfulness_issues`, `repair_component_ids` | [checking.py](../../src/medrag/agent/nodes/checking.py) |
| `inc_regen` | Increment `regen_count`, without a model call | [checking.py](../../src/medrag/agent/nodes/checking.py) |
| `append_history` | Append original question and answer to graph history | [memory.py](../../src/medrag/agent/nodes/memory.py) |
| `summarize_gate` | No-op before a history-length branch | [graph.py](../../src/medrag/agent/graph.py) |
| `summarize` | Update rolling graph summary | [memory.py](../../src/medrag/agent/nodes/memory.py) |

[AgentState](../../src/medrag/agent/state.py) defines fields. Each web request uses a fresh checkpoint;
browser follow-ups use explicitly selected snapshots. Graph summaries retain compatibility for callers
explicitly reusing a checkpoint.

## 4. An actual execution is more informative than an ideal flow

![Saved medical follow-up: three generations/checks, ending with an omission](../assets/system-guide/execution-en.svg)

The diagram reads Evidence limits turn three's original WS events, preserving execution order, repeated
occurrences, event-receipt durations and check fields. The original question requests two things: quote
the glucose-duration sentence and state whether it supplies a five-year mortality result. Three generations
and checks occur; the final check still reports the second requirement missing, then the answer is retained.

```mermaid
sequenceDiagram
    participant U as User requirements
    participant G as generate
    participant C as check
    participant H as append_history
    U->>G: Quote duration + answer whether mortality evidence exists
    G->>C: First generation
    C-->>G: faithful=false, recorded omission
    G->>C: Second generation
    C-->>G: faithful=false, issue remains
    G->>C: Third generation
    C->>H: faithful=false, retain unresolved issues
    Note over G,H: Counter helpers omitted by original WS; observed steps only
```

**A repair chain can exist without repairing the answer.** The checker reports a model judgment; this
diagram does not re-adjudicate its medical semantics. Final fields contain `faithful=false` and
`regen_count=2`; they cannot fill in complete intermediate state for earlier steps.

Original [events](../../data/demo/conversations/run01/v08-evidence-limits-turn-3-events.jsonl),
[importable conversation](../../data/demo/conversations/v08-evidence-limits.json),
[cases and known failures](../../data/demo/conversations/README.md). Use README's no-key route to inspect
the original answer in existing Ask.

### What is missing from the record

Events contain no full node inputs, prompts, successive complete outlines or full drafts; some route fields
are empty. They cannot reconstruct complete internal reasoning or infer historical grade thresholds when
question type is absent. Counter/summary helpers were not emitted as historical events. The node map describes
current source; the execution figure describes observed history. Candidate excerpts contain at most 200
characters; final results retain complete passages. Durations include scheduling/transport.

## 5. Reading and maintenance

Read [architecture](architecture.md) and [Ask workflow](agent-workflow.md) for implementation;
[illustrated showcase](showcase.md) for product/auditing; [research overview](research-overview.md) for results.
Demo cases and node diagrams do not prove an Agent advantage over a strong model using tools; separate
comparative experiments address that question.

Each new figure has Chinese/English SVG versions for Markdown. Source structure supplies the graph,
original records supply the execution, and the script maintains node explanations. Rebuild figures and
[source records](../assets/system-guide/source-records.json) with:

```sh
python scripts/render_system_docs.py
```

Only Python's standard library is required. Rebuild both languages after changing nodes, constants or
explanations; adjust layout positions when adding nodes. This generates documentation assets without
starting the product, downloading models or rerunning experiments. Source fingerprints use SHA256 of
normalized UTF-8 / LF text; event fingerprints use original file bytes. Fixed `v0.8.0` and research results
remain unchanged.
