# Original medical paper demonstration

Source: Seaquist ER, Phillips LS, Ghosh A, et al., for the GRADE Research Group (2024).
**Glycemia reduction in type 2 diabetes—Hypoglycemia outcomes: A randomized clinical trial.**
PLOS ONE 19(11): e0309907. [Publisher](https://doi.org/10.1371/journal.pone.0309907) ·
[PMC11567630](https://pmc.ncbi.nlm.nih.gov/articles/PMC11567630/) · PMID 39546502.

The publisher explicitly dedicates this article to **CC0 1.0**, including unrestricted
reproduction and modification. [License](https://creativecommons.org/publicdomain/zero/1.0/).
This source material retains CC0; the repository's Apache-2.0 license applies to its code.
The paper is used to demonstrate textual attribution, not to recommend a medication.

## Files and provenance

- `article.xml`: unmodified publisher JATS download on 2026-09-26, retained byte-for-byte.
- `manifest.json`: DOI, identifiers, download URL, license statement, XML/text hashes and
  the demonstration question selected before running Ask.
- `corpus.jsonl`: all five abstract sections, in original order. XML tags are removed,
  whitespace within each paragraph is collapsed, paragraphs separated by two newlines.
  No paraphrases, corrections or synthetic evidence. The article body is not indexed.
- `ask-events.json`: actual browser WebSocket events, including the final Agent answer and
  all five retrieved passages. One Ask run, no candidate selection across retries.
- `audit.json`: actual **Export audit JSON** download after Ask → Audit, Direct strategy,
  no input edits. One audit run. Original live-mode metadata is preserved in this file;
  the replay API labels its delivery saved and supplies the medical provenance note.

There are no gold labels here. A model judgment is not an independently validated medical
fact. The answer preserves source sentences and the auditor grouped a compound results
sentence into one claim; four Supported labels do not mean every atomic fact was independently tested.
Claim locations refer to normalized supplied text, not XML byte positions or PDF coordinates.

Recreate the corpus offline from the bundled publisher XML:

```sh
python scripts/prepare_medical_demo.py
```

Replay without a key: follow the root README and run `python scripts/run_audit_demo.py`.
New full-chain inference: install the full environment and configure Flash, then run
`python scripts/run_demo.py --medical`. Each new run can differ from this saved record.

[Walkthrough and actual screenshots](../../../docs/medical-demo.md).
