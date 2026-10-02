# Flash gateway observations: returned identifiers and usage

**English** | [简体中文](../verification-gateway-observations.md)

2026-09-24. Observable API behavior only; no verification of weights or provider identity.

## Observations

The first 30 SciFact pilot requests shared configuration: 29 saved `deepseek-v4.1-flash`, one
`deepseek-v4-flash-0731`. Only the latter retained usage. Complete historical raw streams were
not saved; the layer responsible cannot be reconstructed.

Six identical requests then reused an exposed claim, reading raw OpenAI-compatible SDK chunks.
Flash ID, high reasoning, JSON output and token ceiling stayed fixed, with concurrency at most
three. No identity self-report or hidden reasoning was saved, only character counts and metadata.

All six completed; every chunk reported `deepseek-v4.1-flash`, and all returned usage.
[Raw stream metadata](../../data/verification/gateway_probe/run01/probe.json).
This establishes consistent identifiers for these six calls, not repaired history or fixed weights.

One LangChain `response_model` field does not expose every chunk identifier. New research uses
`FlashGateway` to collect all distinct model names and usage snapshots directly, with the same
configured endpoint and unchanged v0.4 Ask path. This improves observation; it does not establish
LangChain as the cause of missing historical usage.

## Research constraints

- Requested IDs, `/models` and self-description are not proof of weights.
- Retain all identifiers within a request, not only the last.
- Missing usage stays unknown. Use the last cumulative snapshot, not the sum of repeated snapshots.
- Transport retries may incur invisible usage; reported API totals are not billing reconciliation.
- Interleave methods and retain metadata; matching identifiers cannot remove routing confounding.
- Preserve all results if identifiers differ; do not claim a winner from a post-hoc clean subset.

Provider routing needs provider explanation. Cause remains unconfirmed. Development diagnostics
can proceed, but single-model mechanism attribution must retain this limitation.
