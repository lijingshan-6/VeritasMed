# VeritasMed

[English](README.md) | **简体中文**

**可核查的医学问答：结论受证据约束，每句话都能被审计。** 针对文献提问，得到用平实语言写成的回答，
其中的结论和每条陈述都绑定到原文句子；再打开审计，逐条核对每个陈述与来源的关系，标出没有依据或尚未核查的部分。

![录制的操作演示：对话、回答、逐条审计](docs/assets/showcase/preview.gif)

**[打开在线回放 →](https://lijingshan-6.github.io/medrag-agent/)**（录制的真实对话，直接在浏览器运行，无需注册）

React · FastAPI · LangGraph · BGE-M3 混合检索 · Python 3.12 · Apache-2.0

## 一张图看结果

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/experiment-a/tradeoff-dark.png">
  <img alt="在 500 道 PubMedQA 题上，普通 RAG 准确但结论常常无据可查，强提示词让结论有据但准确率降到闭卷水平，VeritasMed 两者兼得" src="docs/assets/experiment-a/tradeoff-light.png">
</picture>

在 PubMedQA 全部 500 道测试题上，所有方法使用同一模型和同一检索器：

- **普通 RAG 的 yes/no 结论有 40% 未引用或不被原文支持，VeritasMed 是 16%**
  （−21.3 个百分点，95% CI [−26.6, −16.1]），准确率持平（63.6% 对 63.8%）。
- **只靠一条更严格的提示词，结论有据的代价是不再下结论**：准确率跌到 51.0%，与闭卷持平。
- **审计检出 97.9% 的植入实质性错误**，误标正确句子 2.0%。
- 代价：每题多花约 1 美分、多约 50 秒。此前基于 MiniCheck 得出的"减半"结论经校准后已撤回。[完整报告 →](docs/experiment-a.zh-CN.md)

## 它能做什么

- **结论受证据约束。** 回答先用一句话给出结论；问题的每个组成部分都绑定到检索论文中的某个句子，
  并用平实语言在旁边作答；缺失的结果明确报告为证据缺口，不靠猜测补齐。（在 PubMedQA 上，84% 的结论
  有引用且被原文支持，普通 RAG 为 60%；剩下的部分交给审计。）
- **回复前先自检。** Agent 先评估证据，证据不足就改写检索，并复核自己的草稿；改写和重写各最多两次。
- **任意回答都能审计。** 一键把每个陈述与来源原文逐条核对；无法定位的引文、未核查的文字和模型分歧都保持可见。
- **对话可以保存。** 追问、答案版本及其审计保存在浏览器中，可以作为一个文件导出、导入。

## 无需 API 密钥即可试用

直接打开 [在线回放](https://lijingshan-6.github.io/medrag-agent/)，或在本地运行：在浏览器中回放三段录制好的医学对话（九个真实回答、十二次审计）。不需要模型、Python、GPU 或数据库，
只需 Node.js 22.12+：

```sh
git clone https://github.com/lijingshan-6/medrag-agent.git
cd medrag-agent/frontend
npm ci
npm run replay
```

打开 http://127.0.0.1:5173，选择一段对话，点选一个问题，再点 **Audit**。

## 问你自己的问题

在线模式检索仓库自带的三篇论文（15 段原始摘要，CC0 / CC BY 许可）。需要 Python 3.12 与完整依赖
（数 GB，CPU 即可，推荐使用 [uv](https://docs.astral.sh/uv/)）和一个 OpenAI 兼容的 Flash 端点。在仓库根目录执行：

```sh
uv venv --python 3.12      # 然后激活 .venv
uv pip sync requirements.lock --torch-backend cpu
uv pip install --no-deps -e .
cp .env.example .env        # 然后填写 OPENHUB_API_KEY（端点或模型不同时一并修改）
python scripts/run_demo.py  # 之后启动可加 --skip-index
```

回答也可以用本地模型生成（`LLM_BACKEND=ollama`、`OLLAMA_MODEL=qwen3.5:9b`），审计始终使用 Flash 端点。

## 工作原理

![系统总览](docs/assets/showcase/system-overview.svg)

1. **理解追问**：结合最多六轮选中的历史对话。旧回答只用于理解“它”“这些结果”指什么，不作为证据。
2. **检索**：BGE-M3 稠密与稀疏检索，经倒数排名融合（RRF）合并后重排；先确认问题点名的是哪篇论文，再挑选段落。
3. **规划回答**：把问题的每个部分绑定到检索文本的句子编号；程序检查每条引文确实存在，且来自正确的论文。
4. **生成与检查**：回答用平实语言撰写，每条陈述旁边展示绑定的原文句子；模型复核支持关系、完整性和证据边界，并要求定向修复。

详见 [工作原理](docs/how-it-works.zh-CN.md) · [Agent 图源码](src/medrag/agent/graph.py)。

## 评测结论

| 问题 | 结果 | 决定 |
|---|---|---|
| VeritasMed 的结论是否比普通 RAG 更有据？（PubMedQA 500 题） | 结论未引用或无依据：**40.1% 对 15.8%**；准确率 63.8% 对 63.6% | 流水线可测量的价值；[报告](docs/experiment-a.zh-CN.md) |
| 一条严格的提示词能否做到同样效果？ | 结论有据（15.1%），但准确率跌到 **51.0%** | 保留多步生成 |
| 审计能否抓到错误？ | 植入错误：实质性错误检出 **187/191**，不当标记 4/200；也能抓到普通 RAG 真实回答中的"说过头" | 审计作为第二道防线 |
| 逐字粘贴原文（v0.8）还是用平实语言？ | 逐字版得分更高，只因引文必然通过引用裁判、且更少回答"maybe"；它的回答是一串引文 | 平实语言，原文句子附在旁边 |
| Agent 能否依据正确证据回答？ | 开发集严格通过：v0.2 为 5/15，v0.4 为 15/15（流程与模型都有变化）。冻结后只跑一次的保留集：**31/35** | 采用当前回答流程 |
| 模型作为陈述核查器有多可靠？ | 在 339 对 SciFact 公开数据上，Flash 错误接受 **6/201** 条无依据陈述，MiniCheck 为 14/201 | Flash 作为默认核查器 |
| 规定的工具流程能否胜过直接阅读论文？ | 31/40，而直接阅读和自主调用工具都是 35/40 | 保留更简单的流程 |
| 细粒度（原子化）审计能否保住限定条件？ | 保住更多条件（101/104 对 91/104），但完成的审计更少（26/48 对 47/48） | 默认 Direct，Atomic v2 可选 |

实验 A 的完整报告见 [docs/experiment-a.zh-CN.md](docs/experiment-a.zh-CN.md)；更早的实验以及每个版本改了什么，见 [研究总结](docs/research.zh-CN.md)。

## 局限

- 这是研究演示，不是临床建议。标签来自公开数据集和 AI 辅助复核，没有临床专家参与。
- PubMedQA 是单篇论文的 yes/no 题，无法检验跨研究的证据综合。
- 自带索引只有三篇论文，无法回答任意医学问题。
- 绿色勾号表示模型判断引用的文本支持该陈述，不是校准过的概率；审计也不评价研究质量，不裁决论文间的冲突。
- 网页 API 没有身份认证，仅供本地使用。历史保存在浏览器存储中，需要保留的内容请导出。

## 仓库结构

| 路径 | 内容 |
|---|---|
| `src/medrag/agent/` | LangGraph 回答图、证据绑定、追问解析、模型工厂 |
| `src/medrag/verification/` | Direct 与 Atomic v2 审计、精确引文绑定、数值检查 |
| `src/medrag/retrieval/`、`index/` | 混合检索、重排、Qdrant 索引 |
| `src/medrag/api/` | FastAPI 应用：Ask WebSocket、审计、原文段落、录制对话 |
| `src/medrag/mcp_server/` | 可选的本地 MCP 工具（检索、问答、评估） |
| `frontend/` | React 应用：对话、回答、来源、审计视图；`npm run replay` 无需后端 |
| `data/demo/conversations/` | 三篇来源论文、语料与录制的对话 |
| `experiments/pubmedqa/` | 实验 A：脚本、预注册文件与全部原始输出 |

检查命令：`python -m pytest -q`、`ruff check src/`、`npm --prefix frontend test`、
`npm --prefix frontend run build`，都不调用模型。

研究历史（数据集、全部实验输出、各版本报告）归档在
[commit 81a1519](https://github.com/lijingshan-6/medrag-agent/tree/81a1519)。另见
[变更记录](CHANGELOG.md) 与 [来源归属](data/demo/conversations/README.md)。
