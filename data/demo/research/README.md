# Saved workflow replays

`selection.json` fixes three development cases before their workflow inference. Exported
bundles include the same eight-paper input, the three actual results, their tool traces,
the withheld-during-inference public reference label and input/result hashes.

`results.json` is a compact derivative of the separate 40-query **final** comparison. The
three visible development examples are not scored as that final experiment.

The examples come from the full second development round after the action-contract repair.
The first round and all its failures remain in `data/verification/v07/development-original/`;
this is not a per-example best-of-two selection. The final comparison was run once after the
revised method freeze. See the [study report](../../../docs/verification-v0.7-report.md).

After preparing the source cache, `python scripts/verification/v07_export.py export` rebuilds
these files from the saved results without invoking a model. Replay needs no dataset cache,
API key or model weights. [Walkthrough](../../../docs/research-demo.md).

Full source/tool text is supplied for traceability and retains upstream paper/data terms;
it is not relicensed by this repository. Document IDs are SciFact corpus IDs, not PMIDs.
See [source attribution and transformations](../../../docs/research-sources.md).
