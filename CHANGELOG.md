# Changelog

## 0.8.0 — 2026-09-27 (persistent conversations and qualifier inspection)

- Keep Ask conversations, selected answer versions, complete source snapshots and per-answer audits
  in browser storage. Support explicit bounded follow-up context, reload recovery and full export/import.
- Add independent experimental Atomic v2 with unique parent-scoped fragment binding and exact
  qualifier anchors. Preserve model judgments, unresolved extraction and source-location failures separately.
- Recover 82 fact locations in an offline replay of 167 historical Atomic audits; retain all old
  judgments and 24 unresolved facts. Location recovery is not semantic verification.
- Bundle three actual three-turn medical conversations, nine Ask responses and twelve audits,
  using original attributed abstracts from three papers. Keep ambiguous references, incomplete
  answers and unnecessary coverage warnings visible; do not replace them with curated retries.
- Add a lightweight, no-key Ask replay at 5173 and a separate full `--conversations` retrieval
  profile. Audit stays inside Ask; standalone audit/research workspaces remain available.
- Keep Direct / Flash as the default. R2 measures constructed qualifier diagnostics with separate
  natural development and repeat runs. Defer R3 because fresh public semantic labels are insufficient.
- Preserve all 348 scheduled R2 audits and 577 model calls. Final target co-presence is 91/104 for
  Direct and 101/104 for v2, while fully completed audits are 47/48 and 26/48 under their differing
  extraction contracts. The mechanical results do not establish semantic improvement.
  See [version notes](docs/releases/v0.8.0.md) and [the research report](docs/verification-v0.8-report.md).

## 0.7.1 — 2026-09-27 (conversation-first product correction)

- Restore Ask as the primary product entry. The lightweight audit/research workspace links back
  to the full application and explains its limited scope.
- Open answer audits inside Ask, retaining the question, complete source passages and composer.
  Returning to the answer preserves its audit; a new question starts a fresh audit context.
- Keep standalone Audit lab / Research as supporting tools. Use client-side navigation so moving
  to the audit lab does not reload the app and erase the current answer. The v0.7.0 tag is unchanged.
- Synchronize the product entry, startup instructions and version metadata. Define the v0.8 plan
  for persistent conversations, contextual follow-ups and measured audit improvements; these remain
  planned work. See [patch notes](docs/releases/v0.7.1.md) and [the v0.8 plan](docs/plans/v0.8-conversation-and-audit.md).

## 0.7.0 — 2026-09-27 (audits measured, workflows compared)

- Add experimental atomic answer audits with parent/fragment bindings, explicit qualification
  slots, unresolved decomposition and independent checker outputs. Keep Direct as the audit default.
- Add an optional pinned MiniCheck adapter and source-grouped fixed-target, medical, natural-answer,
  repeat, calibration and ablation research. Preserve original outputs and a documented constructed-label correction.
- Add a bounded shared-tool workflow study and `/research` replay, public reference labels,
  actual traces, cost/denominator tables and unchanged answer transfer into Audit.
- Bundle six actual Flash audits and 69 local MiniCheck scores across three explicitly distinguished
  GRADE inputs, with standalone startup, actual screenshots, JSON exports and source attribution.
- Complete 339 fixed-pair checks per model, medical/natural-answer diagnostics, calibration,
  ablations and repeats. No eligible MiniCheck acceptance threshold was found; preserve that result.
- Complete the frozen 40-query workflow comparison: direct reading and autonomous tools each make
  35/40 correct accepted binary decisions, versus 31/40 for the structured workflow. False acceptance
  is unchanged. Keep the simple default and publish every final answer, cost and failure.
- Preserve the first development round's action-protocol failures, document the repair before final
  inference and retain both complete development rounds. See the [release notes](docs/releases/v0.7.0.md).

## 0.5.0 — 2026-09-26 (text audit research showcase)

- Bundle a genuine CC0 medical-paper snapshot and its original abstract, an actual Flash Ask → Direct Audit recording, source links and JSON export. The default audit replay needs no key or dataset download; this demo is not an accuracy evaluation.
- Add an isolated `--medical` Ask profile, synchronize version metadata and startup documentation, and separate v0.6 reliability/calibration work from the v0.7 autonomous-tools comparison. See the [release notes](docs/releases/v0.5.0.md).

- Add 33 explicit AI development error reviews separating specific issue identification from incidental span overlap; preserve public annotations and historical scores.
- Add an optional quote-v2 audit with program-derived locations/context and visible repeated/missing quotations. Offline binding-only replay completes 125/126 original outputs versus historical 123/126; never overwrites original failures.
- Complete 36 Flash calls on 8 new sources with separate whole-answer and fixed-target tasks. Whole-answer hits remain 3/5 for both, fixed binary agreement is 8/8 for both including easy copy controls, and repeated whole-answer judgments vary. Keep Direct default; see the [full interpretation](docs/verification-v0.5-specific-errors.md).

- Add an opt-in, one-call Context + meta audit with exact paragraph bindings and separately visible presentation text; preserve the original Direct implementation and default.
- Connect the Ask toolbar to Audit with the unchanged answer, every returned source passage and citation/chunk provenance. No automatic call, truncation or answer replacement; distinguish authored demo transfers.
- Complete 126 preregistered Flash development calls: context/metatext ablations, 24 new source groups and 6 repeated answers. Preserve 123 fully bound audits and all 3 partial failures, unchanged error denominators and a full prior disagreement ledger. Span-metric gains do not establish better semantic verification; Direct remains the default. The 60 official test sources remain unused. See the [context experiment](docs/verification-v0.5-context-audit.md).
- Add independent source-bound text verification, SciFact adaptation and controlled diagnostics; keep all historical v0.4 artifacts intact.
- Add whole-answer direct and extract-then-verify Flash audits, exact answer/source anchors, uncovered text and distinct failure states.
- Freeze a 24-answer RAGTruth training pilot and a metadata-only reserve of 60 test source groups. Count missed and unextracted reference errors in the evaluation denominator.
- Add a real `/audit` panel with saved inference replay, new input, source navigation and JSON export; no uncalibrated confidence percentages.
- Add a lightweight local audit service and launcher without retrieval/GPU dependencies. See the [audit guide](docs/audit-demo.md) and [experiment report](docs/verification-v0.5-answer-audit.md).

## 0.4.0 — 2026-09-23 (published research showcase)

- Add the OpenHub backend with streaming and per-question model selection for the complete Agent.
- Preserve the Pro/Flash development comparison, repeat, all 44 completed answers and source-first assessments; see the [comparison report](docs/agent-model-comparison-report.md).
- Select `deepseek-v4.1-flash` as the continuing research baseline at the user's request because of Pro's token cost, superseding the initial Pro recommendation. Keep the measured results unchanged.
- Make the research runner default to Flash only; paired Pro/Flash runs require explicitly selecting both models. Align configuration examples, workflow and demo guidance with that choice.
- Add a [documentation index](docs/README.md) distinguishing active guidance, experimental records and historical designs.

- Prioritize source identities without rejecting descriptive suffixes; plan and review the whole original question, including evidence gaps.
- Preserve rejected claims through quotation recovery and target unsupported protocol timing and development/validation cohort relationships.
- Render critical factual components from selected source sentences while keeping requested design explanations generative; preserve all development failures and source-first reviews in the [Flash report](docs/agent-v0.4-flash-report.md).
- Retain the fourth development run's five billing errors. Continue with a fresh full run after the user supplied a different compatible Flash gateway; record its exact endpoint/model separately and retain missing usage as unavailable.

- Complete final Flash development (15/15), independent repetition (10/10) and one post-freeze held-out evaluation (31/35), retaining all four test failures and unchanged scoring.
- Record zero execution errors and no observed unsupported material additions in those three runs; preserve the omitted claims/boundaries, one missing endpoint qualifier and coverage disagreements.
- Exercise current Flash Live Ask, source expansion, retrieval/document navigation and Markdown export; add actual screenshots and restore source-page styling and scrolling.
- Publish the milestone on `main` with source tag [`v0.4.0`](https://github.com/lijingshan-6/medrag-agent/tree/v0.4.0), including the full runtime snapshot, offline report commands and [version notes](docs/releases/v0.4.0.md).
- Add fixed-version clone/ZIP instructions and current documentation links. This is a source/tag publication; a separate GitHub Release page is not part of this milestone.

## 0.4.0 repair — 2026-09-22 (unpublished development candidate)

- Preserve full user-derived subquestions before retrieval; match each study before final chunk selection and review its evidence separately.
- Keep development/test roles, actors, null contrasts and method steps in complete source sentences. Preserve cited design explanations separately.
- Separate missing outcome data from missing comparative data. Keep refusal wording tied to the requested outcome.
- Require a structured check for every component and avoid reasoning-only output exhaustion.
- Save two independent Qwen `qwen3.5:9b` focus runs (6/6 and 6/6) and a separate full development run (15/15), with 0 unsupported additions and 0 execution errors in the full run. Preserve all earlier failures.
- Add `recompute_saved_agent.py --version v0.4-repaired`; older version selections retain their meaning.

See [the repair report](docs/agent-v0.4-repaired-report.md). No stable tag, push or held-out test evaluation is implied.

## 0.4.0 — 2026-09-22 (unpublished development candidate)

- Bind each answer component to its requested study, exact source quotation, required details and explicit evidence gap.
- Match study identity before drafting, preserve supported components during targeted repair, and restore omitted numeric details as attributed source quotations.
- Show complete, partial and insufficient evidence coverage with expandable quotations and source navigation. Guided examples remain labelled fixtures.
- Normalize Ollama wildcard listening addresses for Windows client connections; exercise a real partial answer after installing the locked demo in a fresh directory.
- Preserve two independent six-question repetitions (5/6 and 4/6 strict passes) and a separate full development run (9/15, 1 execution error). Publish every answer, source-first decision, log and timing, including failures and the user-requested pause/resume.
- Add `recompute_saved_agent.py --version v0.4`; the existing v0.3 default remains compatible.
- **Quality targets not met:** 3 unsupported or incorrectly scoped additions, 2 missing required qualifiers and only 12/13 answerable questions with all evidence retrieved. No overall answer-quality improvement is claimed. The 35-question test split remains unused.

Implementation and demonstration are available in the candidate branch; no stable v0.4 tag or GitHub publication is implied.

## 0.3.0 — 2026-09-22 (local showcase candidate)

- Plan component searches and retain evidence across requested sources; constrain single-study answers to the leading source.
- Preserve the original question, exact statistical qualifiers and explicitly requested toxicity outcomes throughout answer generation.
- Separate support, completeness and evidence-boundary checks; retry malformed JSON once in place and retain unresolved failures.
- Correct HTML cleanup that could remove statistical inequalities from evidence details.
- Publish a complete 15-question development run, source-first answer decisions and a model-free metric recalculation command. The 35-question test split remains unused.
- Document the current Agent workflow and add a walkthrough of measured answers beside the existing guided UI demo.

## 0.2.0 — 2026-09-21 (local showcase candidate)

- Added the source-disjoint VeritasMed v1.1 benchmark: 50 questions, 44 sources, 20 domains, exact evidence spans, explicit answerability boundaries and zero source or evidence-chunk overlap between development and test.
- Rebuilt the candidate pool with `qwen3.5:9b`, challenged it with `medgemma1.5:4b` and `llama3.1:8b`, and preserved every model finding, output hash and source-first adjudication.
- Ran the production LangGraph Agent on the 15-question development split with local `qwen3.5:9b`, BGE-M3 retrieval and CUDA reranking. The untouched 35-question test split remains reserved for a later declared milestone.
- Recorded 88.5% required-claim Recall@5, 90.0% claim completeness, 100.0% claim-support precision and 5/15 strict answer passes, with per-question failure analysis and curator overrides.
- Changed the active Ollama default from `qwen3:8b` to `qwen3.5:9b`; disabled hidden reasoning for bounded structured responses and restored the full JSON contract during answer regeneration.
- Added production-Agent benchmark runners, deterministic scoring, frozen manifests, an inspectable benchmark report and v0.2.0 release documentation.

No remote GitHub Release or Git tag is implied by this local candidate.

## 0.1.0 — 2026-09-18 (local showcase candidate)

- Added a labelled browser-only guided demo and an isolated live retrieval fixture, with source provenance and desktop/mobile screenshots.
- Added a Python 3.12 CPU dependency lock, clean-environment checks, offline CI and explicit optional Docker/Ollama configurations.
- Corrected WebSocket node starts, terminal error handling, deadlines, cancellation and per-request state isolation.
- Repaired malformed citation handling, backend health reporting and Ollama host selection.
- Removed the ineffective Ask pipeline selector; retained real P2/P3 selection in Explore. Repaired stale stream callbacks, repeated node updates, citation numbering and answer toolbar actions.
- Recomputed historical evaluation summaries with explicit error denominators, corrected Hit@K terminology and immutable input hashes.
- Replaced conflicting release claims with a reproducible quick-start, limitations and validation record.

No new full model benchmark was run. Live model completion, Docker execution and non-Windows execution are not signed off. No remote release or version tag is implied by this entry.
