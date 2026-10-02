# Documentation

**English** | [简体中文](../README.md)

The published version is v0.8.0. Working-tree maintenance and next-stage plans are recorded in
the shared [CHANGELOG](../../CHANGELOG.md). **Ask is the product entrance, Audit is inside the answer,
and Research is a separate experimental showcase.** Flash / Direct remains default.

## Maintained entry points

| Goal | Documentation |
|---|---|
| Understand the product, Agent, auditing and research in five minutes | [Illustrated v0.8 tour and real operation recording](showcase.md) |
| See system structure, node internals and an actual failure | [Illustrated system and node guide](system-guide.md) |
| Install and demonstrate | [Project README](../../README.md), [Startup/configuration](configuration.md) |
| Multi-turn Ask, persistence, import and per-turn audit | [Conversation guide](conversation-guide.md) |
| Inspect claims/sources and run an audit | [Audit guide](audit-demo.md) |
| Real medical demo / research comparison | [Medical demo](medical-demo.md), [Research demo](research-demo.md) |
| Change code | [Architecture](architecture.md), [Ask workflow](agent-workflow.md), [Script catalogue](script-catalogue.md) |
| Understand established results and gaps | [Research overview](research-overview.md) → [Report index](reports/README.md) |
| Recompute experiments | [Reproduction](research-reproduction.md), [Data catalogue](data-catalogue.md), [MiniCheck](minicheck-research.md) |
| Next direction | [Roadmap](verification-roadmap.md) → [v0.9 question-coverage plan](plans/v0.9-question-coverage.md) |
| Configuration boundaries and attribution | [MCP controls](mcp_security.md), [Research sources](research-sources.md), [Annotation limits](verification-label-policy.md), [Gateway observations](verification-gateway-observations.md) |
| Earlier stages | [History](history.md), [Original archive index](../archive/README.md), [Original v0.8 release note](../releases/v0.8.0.md) |
| Dated cleanup record | [Original milestone review (Chinese)](../milestone-v0.8-review.md) |

## Shared records and bilingual maintenance

Current documentation has paired Chinese and English pages: root `README.md` / `README.zh-CN.md`,
Chinese guides in `docs/`, and English counterparts in `docs/en/`. Each maintained pair provides
a language link. Current main reports v0.6/v0.7/v0.8 and the v0.9 plan are paired too.

Update both members in the same change when behavior, commands, boundaries or results change.
Keep commands, environment/API names, dataset IDs, denominators and numbers identical. English
script/data catalogues correspond to the original directory indexes. Images, recordings, experimental
inputs and outputs are shared; they are not translated or duplicated as another experiment.

Historical plans, release records, decisions, detailed case outputs and worklogs stay in their
original language; links to them identify this status. A translation does not rewrite frozen inputs,
labels, hashes, tags or historical scores. Original paper/answer text remains original, even inside
a Chinese guide. Shared diagram labels and real UI screenshots may be English.

The shared directories are:

- `docs/reports/`: reports, case records and failure analysis, including unfavorable results.
- `docs/plans/`: protocols; v0.5–v0.8 are historical contracts, v0.9 is the next-stage entry.
- `docs/archive/worklogs/`, `docs/archive/plans/`: implementation logs/early plans, not current instructions.
- `docs/releases/`: delivery records; research stages do not necessarily have matching Git tags.
- `docs/decisions/`: lasting scope/product decisions, including Flash default and Ask first.
- `data/`: raw experiments, provenance, frozen manifests and labels.

Maintain functionality in README, the appropriate guide and architecture; derive research numbers
from saved artifacts rather than copying a new “overall score” into many logs. Preserve inputs,
outputs, failures and exposure limits. Exact location is not semantic correctness; model disagreement
is not paper conflict. [Original archive index](../archive/README.md) records earlier file moves.
