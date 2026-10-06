# Changelog

## 0.10.0 — unreleased (Experiment A)

- **Experiment A** on all 500 PubMedQA test questions, five methods plus two registered follow-ups,
  planted-error and natural-error audit studies, and a blinded judge calibration
  ([report](docs/experiment-a.md)). The project is now positioned as verifiable medical Q&A:
  VeritasMed grounds its yes/no conclusions (16% uncited or unsupported vs 40% for plain RAG) without
  losing accuracy; the audit flags 97.9% of planted material errors.
- **Withdrawn:** a MiniCheck-based "unsupported sentences halved" result; MiniCheck failed calibration
  (77.3% vs 94.0% for the Flash judge) and is kept only as a rejected measure.
- **Changed:** answers are written in plain words with the bound source sentences kept beside each
  claim, instead of pasting key facts verbatim (supported by the A3 comparison). Answers open with a
  one-sentence conclusion for yes/no questions. Evidence uses whole abstracts; token usage is metered
  per request.
- **Added:** a "non-significant is not no difference" advisory on audited claims. A text rule flags a
  claim that states no difference or no effect when its quoted evidence reports a non-significant
  result; the relation is never changed. Shown on the claim and counted in the audit summary.
- **Frontend:** the Ask workspace was redesigned around the answer, with sidebar, process view and an
  evidence panel; the replay was re-recorded.

## 0.9.0 — unreleased (consolidation)

The project is now one product: Ask with an audit inside each answer. Research history moved out
of the working tree and is archived at
[commit 81a1519](https://github.com/lijingshan-6/VeritasMed/tree/81a1519) and tag `v0.8.0`.

- **Fixed:** an answer component bound to a source sentence already shown for another component
  lost its own answer (the recorded five-year-mortality omission). Writing instructions such as
  "do not rank them" are no longer reported as missing evidence. Regression tests replay the
  recorded failures, and a new real-model recording of all nine demo questions (run02, now the
  bundled replay) answers both cases correctly on the first attempt.
- **Removed:** the standalone audit/research workspace, Research and Explore pages, the authored
  guided demo, the MiMo backend, the Split / Context / Quote-v2 / Atomic v1 audit methods,
  `/api/search`, `/api/history`, legacy numbered pipelines, benchmark tooling, experiment scripts
  and data, and the unverified Docker / conda / PowerShell launchers. Code went from 37,600 to
  13,500 lines including tests; tracked files from 1,154 to 206.
- **Added:** a backend-free replay build (`npm run replay`, `npm run build:replay`) and a GitHub Pages
  workflow, so the recorded conversations can be opened from a link. Replay no longer needs Python.
- **Changed:** Flash (`openhub`) is the default backend; Ollama remains optional. One live demo
  profile (three papers). Saved audits made with retired methods still display.
- **Docs:** a new README, [how it works](docs/how-it-works.md) and [research summary](docs/research.md),
  each in English and Chinese.

## Earlier versions

Full notes for each version are in the archive (`docs/releases/`, `docs/reports/`).

| Version | Date | Summary |
|---|---|---|
| 0.8.0 | 2026-09-27 | Persistent conversations, explicit follow-up context, per-answer audits, Atomic v2 qualifier anchors, three recorded medical conversations |
| 0.7.1 | 2026-09-27 | Ask restored as the product entry; audit opens inside the answer |
| 0.7.0 | 2026-09-27 | Checker reliability (Flash vs MiniCheck), calibration, and the three-workflow comparison |
| 0.5.0 | 2026-09-26 | Claim-level audit panel with exact answer/source anchors |
| 0.4.0 | 2026-09-23 | Evidence-bound answers; Flash 15/15 development, 31/35 held-out |
| 0.3.0 | 2026-09-22 | Per-study search planning and statistical qualifiers; 10/15 |
| 0.2.0 | 2026-09-21 | VeritasMed 50-question benchmark; 5/15 baseline |
| 0.1.0 | 2026-09-18 | Runnable stack, streaming, cancellation and citation fixes |
