# VeritasMed 历史评估报告

本报告对应 2026-09-18 里程碑审计的历史工件；历史运行日期未记录。
本报告从已保存的评估逐题结果重新计算；没有运行新的检索、模型或裁判评估。
代码 commit、语料快照与硬件配置未随这些结果文件完整保存，
因此不能把下面的延迟或成绩视为当前版本的实测表现。

## Agent 问答评分

| 历史题集 | 尝试 | 有评分 | 错误 | 成功题 Composite | 错误题按零 Composite |
|---|---:|---:|---:|---:|---:|
| strict 标准集 | 50 | 49 | 1 | 0.671155 | 0.657732 |
| hard 难题集 | 39 | 39 | 0 | 0.817949 | 0.817949 |

Composite 为逐题保存分数的均值。成功题口径只除以有评分题数；
错误题按零口径以全部尝试数为分母。strict 与 hard 题集不同，不能直接比较为版本提升。

| 历史题集 | 成功题 Faithfulness | Relevance | Correctness |
|---|---:|---:|---:|
| strict | 0.9633 | 0.7096 | 0.3406 |
| hard | 0.9513 | 0.8192 | 0.6833 |

历史文件记录的裁判：strict 为 `mimo-v2.5-pro`，hard 为 `mimo-v2.5-pro`。
裁判与系统检查模型属于同一模型家族，评分独立性受限。
Faithfulness 是对检索上下文的评分，不是医学正确率；Correctness 也不是临床验证结果。
没有在同一冻结题集、语料、提示词和裁判条件下与普通 RAG 做配对消融，
所以这些工件不能证明 Agent 优于普通 RAG。

### 历史 Agent 端到端耗时（只含成功题，秒）

| 题集 | n | 均值 | 中位数 | P95（nearest rank） |
|---|---:|---:|---:|---:|
| strict | 49 | 22.04 | 17.09 | 53.88 |
| hard | 39 | 81.92 | 72.49 | 144.82 |

### 错误题

- strict Q031: `'dict' object has no attribute 'strip'`
- hard: 0 条。

## 历史检索结果（标准集，P1/P2/P3）

Hit@5 表示前五个结果至少命中一条标准证据；旧结果文件的 Recall@5 字段使用此定义。
证据 Recall@5 先按每题计算命中证据数 / 标准证据数，再对题目取宏平均。
MRR@20 对首条命中证据的名次取倒数，再对题目取平均；未命中记零。

| 检索方案 | 题数 | Hit@5 | 宏平均证据 Recall@5 | MRR@20 | 历史平均检索耗时 |
|---|---:|---:|---:|---:|---:|
| P1 | 50 | 0.5000 | 0.2667 | 0.3547 | 0.154 秒 |
| P2 | 50 | 0.6000 | 0.2933 | 0.4177 | 0.165 秒 |
| P3 | 50 | 0.7000 | 0.3250 | 0.5134 | 0.423 秒 |

检索耗时只包含历史检索步骤，不能与上面的 Agent 端到端耗时直接比较。
这些逐题排名支持此历史评估中 P2/P3 命中与排序改善的观察，
不构成 Agent 问答收益的证据。

## 可追溯输入

以下 SHA-256 校验文件原始字节。题集 hash 只标识当前保存的题集文件，
历史运行缺少完整语料快照 hash，无法单凭这些文件复原运行环境。

| 输入文件 | SHA-256 |
|---|---|
| `data/eval/agent_eval_hard_v4.json` | `3ab451541670196b0c053bb79a8121384ab69f47f11b963f2d3feeaeb1a1accf` |
| `data/eval/agent_eval_v2_strict.json` | `1f7a0f3bd4429f36f01fadc46dc200ca6cffbf7e1952f064294b047a8467c252` |
| `data/eval/retrieval_eval_v2_gpu.json` | `319e7e0341d7f27e75cce5065628c56393b0d1e60dc7db342455fed2ece9ffb9` |
| `data/golden/golden_dataset.jsonl` | `644748fa6453507f3b87ce87e0e73f0157c886791233034c261d00ef5094ead8` |
| `data/golden/golden_hard.jsonl` | `33ee0351a484b103b231f92ab0a0afb5d499189410827e508d9df77d3f7b6092` |

重新生成：`python scripts/report_release.py`。检查工作树报告是否与输入一致：
`python scripts/report_release.py --check`。两个命令都不会改写历史评估 JSON。
