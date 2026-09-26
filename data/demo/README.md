# Demonstration corpus

v0.5 also includes an **original-paper medical corpus and actual inference recording** in
[`medical/`](medical/README.md), under its own CC0 source terms. Run `python scripts/run_demo.py --medical`
to use it; the separate collection is `medrag_medical_demo`. The older fixture below is unchanged.

These three short passages are **authored summaries for software demonstration**, not copied abstracts, original article text, clinical guidance, or a benchmark dataset. The UI titles retain this label. They were checked against these sources on 2026-09-18:

- [fastMRI dataset paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC6996599/) — two summaries, dataset purpose and access. Actual imaging data have a separate sharing agreement; no images or k-space data are redistributed here.
- [fastMRI+ paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC8983757/) — one summary, expert annotations.

The authored fixture text is provided under this repository's Apache-2.0 license. That license does not apply to the linked papers or their datasets. The PMID/PMC citation links identify the underlying sources, while the evidence panel displays the labelled summaries actually indexed.

Without `--medical`, `bootstrap_demo.py` upserts stable IDs into **medrag_demo**. Neither demo profile
deletes a collection or writes to `medrag_text`. Do not mix research data into these reserved collections.
