> Historical development document. Some claims and defaults are superseded. For v0.1.0, use the repository README, docs/reports/evaluation_report.md and docs/validation-2026-09-18.md.

# VeritasMed 端到端延迟报告

> 版本: v3.1 · 日期: 2026-05-16  
> 对比基准: CPU-only 本地 LLM（Ollama Qwen3-8B）vs MiMo API（CPU Reranker）vs 目标（MiMo API + GPU Reranker）

---

## 1. 测量方法

```python
# scripts/11_eval_agent.py 中的 agent_latency 字段即单次 wall-clock 时间
t0 = time.perf_counter()
result = app.invoke(initial_state, config=config)
agent_latency = time.perf_counter() - t0
```

组件级耗时通过日志 `[retrieve]`、`[rerank]`、`[grade]`、`[generate]`、`[check]` 前缀的时间戳差分获得。

---

## 2. 基线：CPU-only 本地 LLM（Ollama Qwen3-8B）

> 此阶段 `sentence_transformers` 尚未完成迁移，`BGE-M3` 当时以 dense 模式运行。

| 阶段 | P50 延迟 | 备注 |
|------|---------|------|
| BGE-M3 dense 编码 | ~0.3 s | CPU |
| Qdrant 向量检索 | ~0.1 s | 本地 in-memory |
| BGE-Reranker（20 对）| **~20 s** | CPU 瓶颈 |
| route（Qwen3-8B，thinking=OFF）| ~5 s | Ollama 本地推理 |
| grade（Qwen3-8B，thinking=ON）| ~15 s | 含 thinking block |
| generate（Qwen3-8B，thinking=OFF）| ~10 s | Ollama 本地推理 |
| check（Qwen3-8B，thinking=ON）| ~12 s | 含 thinking block |
| **端到端 P50（单次检索，无 rewrite）** | **~64 s** | 实测均值 |

---

## 3. 当前状态：MiMo API + auto-detect Reranker（实测）

> 实测数据来自标准集 50 题评估（`scripts/11_eval_agent.py`，`data/eval/agent_eval.json`）。  
> Reranker 设备：`RERANKER_DEVICE=auto`——有 CUDA 时自动使用 GPU（fp16），否则回退 CPU。评估时实测延迟显示约 15s/20对，表明评估环境中 Reranker 运行在 CPU 上。

| 阶段 | 实测 P50 | 备注 |
|------|---------|------|
| BGE-M3 dense 编码 | ~0.3 s | CPU，sentence_transformers |
| Qdrant 向量检索 | ~0.1 s | 本地 Docker |
| BGE-Reranker（20 对）| **~15 s（CPU）/ ~0.2 s（GPU）** | auto-detect；有 CUDA 自动 GPU fp16 |
| route（MiMo-V2.5 API）| ~1 s | API 调用 |
| grade（MiMo-V2.5-Pro API）| ~2–3 s | API 调用，Pro 含 thinking |
| generate（MiMo-V2.5-Pro API）| ~2–3 s | API 调用 |
| check（MiMo-V2.5-Pro API）| ~2–3 s | API 调用 |
| **P3 端到端 avg（50 题，无 rewrite）** | **35.4 s** | 实测 |
| **P3 端到端 P50** | **34.1 s** | 实测 |
| **P3 端到端 P90** | **46.0 s** | 实测 |
| **P4 端到端 avg（50 题，含 Agent 循环）** | **79.5 s** | 实测（0% rewrite 触发） |
| **P4 端到端 P50** | **77.5 s** | 实测 |
| **P4 端到端 P90** | **93.7 s** | 实测 |

**Hard Set（39 题）**：

| 管道 | avg | P50 | P90 |
|------|-----|-----|-----|
| P3 Static | 43.8 s | 44.0 s | 53.8 s |
| P4-Agentic (v4) | 160.1 s | 116.8 s | 307.6 s |

P4 Hard Set 长尾（P90=307.6s）来自 grade + rewrite + regen 多轮触发，每轮 ~20s grade + ~15s check。

---

## 3.5 修复后实测：MiMo API + GPU Reranker + thinking disabled（2026-05-16）

**根因诊断**：MiMo 推理模型（mimo-v2.5 / mimo-v2.5-pro）默认启用内部 CoT 推理（reasoning_content），在 max_tokens=4096 下会花费 1000–5000+ reasoning tokens 再输出实际内容，导致每次 API 调用 15–27s。budget_tokens 参数在此 API 无效。

**修复**：在所有 ChatOpenAI 调用中注入 `extra_body={"thinking": {"type": "disabled"}}`，同时恢复 fast model 为 `mimo-v2.5`（之前被错误覆写为 `mimo-v2.5-pro`）。

**实测组件延迟**（GPU + isolated call，`bench_grade_isolated.py`，2026-05-16，median）：

| 组件 | 前（thinking=ON）| 后（thinking disabled）| 降幅 |
|------|-----------------|----------------------|------|
| BGE-M3 dense 编码（×1） | ~45 ms | ~45 ms | — |
| BGE-Reranker（20 对，CUDA） | ~132 ms | ~132 ms | — |
| route（mimo-v2.5） | 13,553 ms | **1,168 ms** | **-91%** |
| grade（mimo-v2.5-pro） | 21,203 ms | **2,990 ms** | **-86%** |
| generate（mimo-v2.5） | 5,051 ms | **2,283 ms** | **-55%** |
| check（mimo-v2.5-pro） | 15,650 ms | **1,555 ms** | **-90%** |

**修复后端到端预估（P3 happy-path，无 rewrite）**：

```
route(1168) + retrieve(~500) + rerank(132) + grade(2990) + generate(2283) + check(1555)
≈ 8,628 ms  ≈ 8.6s
```

含 1 次 rewrite：
```
+ rewrite(~2000) + retrieve(500) + rerank(132) + grade(2990)
≈ 14,250 ms  ≈ 14.3s
```

**质量影响**：`mimo-v2.5-pro`（grade/rewrite/check）在 thinking disabled 下仍能输出结构化 JSON 且推理准确。fast 节点（route/generate）使用 `mimo-v2.5` + thinking disabled 同理稳定。待 Qdrant 上线后进行端到端质量回归。

---

## 4. GPU Reranker 场景预估

> `RERANKER_DEVICE=auto` 已内置 CUDA auto-detect。当运行在有 GPU 的机器上时（如 RTX 4060），BGE-Reranker 自动以 fp16 运行，延迟大幅下降。

| 阶段 | 预期延迟 | 改动 |
|------|---------|------|
| BGE-M3 dense 编码 | ~0.3 s | 不变 |
| Qdrant 向量检索 | ~0.1 s | 不变 |
| BGE-Reranker（20 对，CUDA fp16） | **~0.2 s** | `RERANKER_DEVICE=cuda` |
| route（MiMo-V2.5 API）| ~1 s | 不变 |
| grade（MiMo-V2.5-Pro API）| ~2–3 s | 不变 |
| generate（MiMo-V2.5-Pro API）| ~2–3 s | 不变 |
| check（MiMo-V2.5-Pro API）| ~2–3 s | 不变 |
| **P3 端到端 P50（预估）** | **< 10 s** | 目标（Reranker 从 15s → 0.2s） |
| **P4 端到端 P50（预估）** | **< 20 s** | 目标（无 rewrite 场景） |

验证命令（GPU 机器上）：

```bash
# RERANKER_DEVICE=auto 即可，有 CUDA 自动用 GPU
python scripts/11_eval_agent.py --output data/eval/agent_eval_gpu.json
python -c "
import json, statistics
data = json.load(open('data/eval/agent_eval_gpu.json'))
lats = [r['agent_latency_s'] for r in data['results'] if 'agent_latency_s' in r]
print(f'P50={statistics.median(lats):.1f}s  P90={sorted(lats)[int(len(lats)*0.9)]:.1f}s  mean={statistics.mean(lats):.1f}s')
"
```

---

## 5. 延迟优化路径总结

```
阶段 1（基线）: GPU → Qwen3-8B LLM (Ollama, 5.2 GB VRAM 占满)
                CPU → BGE-M3 + BGE-Reranker          P50 ≈ 64s

阶段 2（MiMo API + CPU Reranker，评估环境）:
                API → MiMo V2.5/V2.5-Pro 降低 LLM 延迟
                CPU → BGE-Reranker（主瓶颈）           P50(P3) ≈ 34s
                [问题：MIMO_MODEL_FAST 错误设为 pro，模型内部 CoT 未禁用]

阶段 3（当前，2026-05-16）:
                API → mimo-v2.5 (fast) + mimo-v2.5-pro (think), thinking=disabled
                GPU → BGE-Reranker fp16 (CUDA auto-detect)
                       预估 P50(P3 happy-path) ≈ 8.6s
                       预估 P50(P3 with 1 rewrite) ≈ 14s
```

**当前 P3 延迟主要分解（修复后预估，happy-path）**：
- grade（mimo-v2.5-pro, thinking disabled）：~3.0s（35%）
- generate（mimo-v2.5, thinking disabled）：~2.3s（27%）
- route（mimo-v2.5, thinking disabled）：~1.2s（14%）
- check（mimo-v2.5-pro, thinking disabled）：~1.6s（19%）
- BGE-M3 编码 + Qdrant 检索 + Reranker：~0.7s（8%）

**下一步**：Qdrant 上线后测量端到端真实延迟（`bench_latency.py`，不加 `--skip-qdrant`），并进行质量回归。

---

*VeritasMed Latency Report v3.1 — 2026-05-16*
