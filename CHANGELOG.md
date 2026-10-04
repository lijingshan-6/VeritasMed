# Changelog

## 0.9.0 — unreleased (consolidation)

The project is now one product: Ask with an audit inside each answer. Research history moved out
of the working tree and is archived at
[commit 81a1519](https://github.com/lijingshan-6/medrag-agent/tree/81a1519) and tag `v0.8.0`.

- **Fixed:** an answer component bound to a source sentence already shown for another component
  lost its own answer (the recorded five-year-mortality omission). Writing instructions such as
  "do not rank them" are no longer reported as missing evidence. Regression tests replay the
  recorded failures; the prompt change has not yet been re-measured with model calls.
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
