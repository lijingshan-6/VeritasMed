> Historical development document. Some claims and defaults are superseded. For v0.1.0, use the repository README, docs/reports/evaluation_report.md and docs/validation-2026-09-18.md.

# VeritasMed Hard Eval Set — Stage 1 构造与基线报告

> 版本: v1.1 · 日期: 2026-05-08  
> 目的：描述 Hard Set 构造方法，并记录 P4-Agentic v1（优化前基线）在困难查询上的表现
>
> **后续优化（v4 smart-gate）的完整结果见 [`docs/reports/evaluation_report.md`](evaluation_report.md) §3.2 与 §8.4**

---

## 1. Hard Set 构造

### 1.1 构造方法

从 Qdrant 语料（44,768 chunks：1,975 PubMed abstracts + 42,793 PMC full-text）中采样，
以关键词分类器筛选 10 个医学领域，构造四类困难题：

| 类型 | 设计目标 | 触发机制 |
|------|---------|---------|
| **A — 多跳推理** | 需要 ≥2 个来自不同文档的 chunk 才能回答 | grade_relevance 低分 → rewrite_query 展开 |
| **B — 术语歧义** | 口语/缩写 → MeSH 同义词展开才能检索 | 初次检索词汇覆盖不足 → rewrite |
| **C — 否定/反事实** | "X 为何不是一线药物" 等负面结论 | 关键词命中但语义不匹配 → rewrite |
| **D — 跨领域合成** | 欠代表领域（内分泌、传染病、肾脏科等）| 稀有术语 → rewrite |

### 1.2 语料统计

| 指标 | 数值 |
|------|------|
| 采样总 chunks | ~7,000 PMC content + 1,975 PubMed |
| 初选候选集 | A=5, B=25, C=25, D=30 |
| 成功生成题目 | 见下表 |

### 1.3 最终 Hard Set 构成

| 类型 | 目标 | 实际 | 备注 |
|------|------|------|------|
| A — 多跳推理 | 15 | 4 | 语料中跨文档配对稀少；PMC 论文各自独立主题 |
| B — 术语歧义 | 10 | 10 | ✓ 达标 |
| C — 否定/反事实 | 10 | 10 | ✓ 达标 |
| D — 跨领域合成 | 15 | 15 | ✓ 达标 |
| **合计** | **50** | **39** | A 类未达标，见注释 |

> **注**：A 类仅采集到 5 个跨文档配对，最终生成 4 题（1 题 LLM 拒绝）。原因：PMC 语料包含植物学、细菌学等非临床基础研究论文，各篇主题独立，难以构造多文档推理链。后续可在候选筛选阶段加入"患者/临床/治疗"关键词过滤提升数量。

Hard Set SHA-256（Python canonical）：  
`33ee0351a484b103b231f92ab0a0afb5d499189410827e508d9df77d3f7b6092`

---

## 2. Agentic 评测结果（P4-Agentic v1 基线）

> 评测日期：2026-05-08  
> 评测命令见第 3 节。评判模型：`mimo-v2.5-pro`  
> ⚠️ 这是 P4-Agentic **v1（优化前基线）** 的结果。v4 smart-gate 版本（Composite=0.818）见 [`docs/reports/evaluation_report.md`](evaluation_report.md)。

### 2.1 P3 Static vs P4-Agentic（Hard Set，39 题）

| 维度 | P3 Static | P4-Agentic | Δ |
|------|-----------|------------|---|
| Faithfulness | 0.7718 | 0.7564 | −0.015 |
| Relevance | 0.8897 | 0.6987 | −0.191 |
| Correctness | 0.5821 | 0.6000 | **+0.018** |
| **Composite** | **0.7479** | **0.6850** | **−0.063** |

> **关键发现**：P4-Agentic 在 Hard Set 上整体 Composite 低于 P3 Static（−0.063）。Relevance 大幅下滑（−0.191）是主要拖累，原因见第 4 节分析。Correctness 小幅提升（+0.018）说明 rewrite 环路在部分题目上确实改善了答案质量。

### 2.2 Agent 环路统计（P4-Agentic, Hard Set）

| 指标 | Hard Set | Standard Set (50q) | 说明 |
|------|----------|---------------------|------|
| 平均 rewrites/题 | **0.46** | 0.00 | Hard Set 触发更多 rewrite ✓ |
| 触发 rewrite 比例 | **23.1%** | 0.0% | 目标 > 30%，略低于目标 |
| 平均 regen/题 | **0.36** | 0.00 | faithfulness check 触发 |
| Agent faithful% | **76.9%** | 100.0% | 23.1% 未通过内部 faithful 检查 |
| P50 端到端延迟 | **116.8s** | — | vs P3 P50=44.0s（慢 2.7×） |

### 2.3 按题型分解

| 题型 | n | P3 Composite | P4 Composite | Δ | P4 Rewrite% | P4 avg_iter |
|------|---|-------------|-------------|---|-------------|-------------|
| A — 多跳 | 4 | 0.533 | 0.425 | **−0.108** | 100% | 2.00 |
| B — 术语 | 10 | 0.732 | 0.583 | **−0.148** | 20% | 0.40 |
| C — 否定 | 10 | 0.807 | 0.678 | **−0.128** | 20% | 0.40 |
| D — 跨域 | 15 | 0.777 | **0.827** | **+0.050** | 0% | 0.13 |

> **D 类唯一正向增益**：跨域综合题在 P4 下表现更好（+0.050），且几乎不触发 rewrite（iter=0.13）——说明 LangGraph 的 grade/generate 节点对语义清晰、术语明确的问题能稳定输出。

---

## 3. 运行命令

```bash
# P3 静态管道（baseline）
python scripts/09_eval_answer.py \
    --pipeline p3 \
    --golden data/golden/golden_hard.jsonl \
    --output data/eval/p3_hard_eval.json \
    --model mimo-v2.5-pro

# P4 Agentic 管道
python scripts/11_eval_agent.py \
    --golden data/golden/golden_hard.jsonl \
    --output data/eval/agent_eval_hard.json \
    --model mimo-v2.5-pro
```

---

## 4. 关键发现与建议

### 4.1 Agentic 增益

- **整体**：P4-Agentic 在 Hard Set 上未带来整体提升（Composite −0.063），与 Standard Set（100% faithful, 0 rewrites）的对比揭示了**Agent 对困难题的鲁棒性不足**。
- **D 类正向**：跨域综合题获益 +0.050，说明 LangGraph agent 对语义完整问题仍能稳定输出。
- **Correctness 小幅提升**（+0.018）：rewrite 环路在术语/否定类问题上略微改善了答案内容准确性。

### 4.2 主要瓶颈

1. **Relevance 大幅下滑（−0.191）**：P4-Agentic 在多次 rewrite 后生成的答案出现"答非所问"现象（尤其 A/B 类，relevance 低至 0.0）。根因：rewrite 后的查询偏离原始问题意图，导致最终回答 context 与问题脱节。

2. **Type A 多跳推理无法改善**（P4 comp=0.425 < P3 0.533）：即使触发 100% rewrite，correctness 仍只有 0.125。语料中缺乏跨文档推理所需的中间概念连接，rewrite 无法弥补语料覆盖缺口。

3. **Faithfulness 内部检查过严（76.9% pass）**：23.1% 的题目触发 regen，但 regen 后生成质量未必更好（e.g. hard_B03, hard_C05 comp=0.0）。regen 逻辑需要更精细的触发条件。

4. **延迟代价高**：P50 latency 116.8s vs P3 44.0s，慢 2.7×，主要来自 BGE-Reranker CPU 模式（~15s/query）+ 多轮 LLM 调用。

### 4.3 建议后续优化

| 优先级 | 方向 | 具体措施 | 实施状态 |
|--------|------|---------|---------|
| ★★★ | rewrite 质量 | REWRITE_SYSTEM 加入"保留原始问题意图"约束；max_rewrites=1 | ✅ v4 已实施 |
| ★★★ | faithfulness regen 门控 | confidence + citations 作为智能 regen 门控，避免 false positive | ✅ v4 已实施 |
| ★★ | Type A 语料补充 | 在候选筛选阶段加入"患者/临床/治疗"关键词过滤 | ○ 待实施 |
| ★★ | GPU 加速 | RERANKER_DEVICE=cuda，rerank 延迟从 ~15s 降至 ~0.2s | ○ 待验证 |
| ★ | 答案长度控制 | generate 节点增加最小 token 要求 | ○ 待实施 |

v4 优化结果摘要（完整数据见 [`docs/reports/evaluation_report.md`](evaluation_report.md)）：

| 指标 | v1 基线 | v4 smart-gate | Δ | P3 基线 |
|------|---------|--------------|---|---------|
| Composite | 0.685 | **0.818** | +0.133 | 0.748 |
| Faithfulness | 0.756 | **0.951** | +0.195 | 0.772 |
| Insufficient evidence | 8/39 | **1/39** | −7 | — |

---

*VeritasMed Hard Set Report v1.1 — 2026-05-08*
