# VeritasMed

[English](README.md) | **简体中文**

**一个会出示证据的医学文献问答 Agent。** 针对论文提问，回答里的每句话都引用原文句子；
再打开审计，逐条核对每个陈述与来源的关系，标出没有依据或尚未核查的部分。

![录制的操作演示：对话、回答、逐条审计](docs/assets/showcase/preview.gif)

React · FastAPI · LangGraph · BGE-M3 混合检索 · Python 3.12 · Apache-2.0

## 它能做什么

- **回答引用到具体原句。** 问题的每个组成部分都绑定到检索论文中的某个句子；缺失的结果明确报告为证据缺口，
  不靠猜测补齐。
- **回复前先自检。** Agent 先评估证据，证据不足就改写检索，并复核自己的草稿；改写和重写各最多两次。
- **任意回答都能审计。** 一键把每个陈述与来源原文逐条核对；无法定位的引文、未核查的文字和模型分歧都保持可见。
- **对话可以保存。** 追问、答案版本及其审计保存在浏览器中，可以作为一个文件导出、导入。

## 无需 API 密钥即可试用

回放三段录制好的医学对话（九个真实回答、十二次审计），不需要模型、GPU 或数据库。
安装 [uv](https://docs.astral.sh/uv/) 和 Node.js 22.12+ 后：

```sh
git clone https://github.com/lijingshan-6/medrag-agent.git
cd medrag-agent
uv venv --python 3.12
uv pip install -r requirements-audit.txt
uv pip install --no-deps -e .
```

激活环境（Windows 用 `.venv\Scripts\Activate.ps1`，其他系统用 `source .venv/bin/activate`），
然后运行 `python scripts/run_showcase.py`。打开 http://127.0.0.1:5173，选择一段对话，
点选一个问题，再点 **Audit**。

## 问你自己的问题

在线模式检索仓库自带的三篇论文（15 段原始摘要，CC0 / CC BY 许可）。需要完整依赖（数 GB，CPU 即可）
和一个 OpenAI 兼容的 Flash 端点：

```sh
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
4. **生成与检查**：关键数字逐字引用原文；模型复核支持关系、完整性和证据边界，并要求定向修复。

详见 [工作原理](docs/how-it-works.zh-CN.md) · [Agent 图源码](src/medrag/agent/graph.py)。

## 评测结论

| 问题 | 结果 | 决定 |
|---|---|---|
| Agent 能否依据正确证据回答？ | 开发集严格通过：v0.2 为 5/15，v0.4 为 15/15（流程与模型都有变化）。冻结后只跑一次的保留集：**31/35** | 采用当前回答流程 |
| 模型作为陈述核查器有多可靠？ | 在 339 对 SciFact 公开数据上，Flash 错误接受 **6/201** 条无依据陈述，MiniCheck 为 14/201 | Flash 作为默认核查器 |
| 规定的工具流程能否胜过直接阅读论文？ | 31/40，而直接阅读和自主调用工具都是 35/40 | 保留更简单的流程 |
| 细粒度（原子化）审计能否保住限定条件？ | 保住更多条件（101/104 对 91/104），但完成的审计更少（26/48 对 47/48） | 默认 Direct，Atomic v2 可选 |

完整数字、置信区间以及每个版本改了什么，见 [研究总结](docs/research.zh-CN.md)。

## 局限

- 这是研究演示，不是临床建议。标签来自公开数据集和 AI 辅助复核，没有临床专家参与。
- 自带索引只有三篇论文，无法回答任意医学问题。
- 绿色勾号表示模型判断引用的文本支持该陈述，不是校准过的概率；审计也不评价研究质量，不裁决论文间的冲突。
- 网页 API 没有身份认证，仅供本地使用。历史保存在浏览器存储中，需要保留的内容请导出。

## 仓库结构

| 路径 | 内容 |
|---|---|
| `src/medrag/agent/` | LangGraph 回答图、证据绑定、追问解析、模型工厂 |
| `src/medrag/verification/` | Direct 与 Atomic v2 审计、精确引文绑定、数值检查 |
| `src/medrag/retrieval/`、`index/` | 混合检索、重排、Qdrant 索引 |
| `src/medrag/api/` | FastAPI 应用（`app.py`）与无密钥回放（`replay_app.py`） |
| `src/medrag/mcp_server/` | 可选的本地 MCP 工具（检索、问答、评估） |
| `frontend/` | React 应用：对话、回答、来源、审计视图 |
| `data/demo/conversations/` | 三篇来源论文、语料与录制的对话 |

检查命令：`python -m pytest -q`、`ruff check src/`、`npm --prefix frontend test`、
`npm --prefix frontend run build`，都不调用模型。

研究历史（数据集、全部实验输出、各版本报告）归档在
[commit 81a1519](https://github.com/lijingshan-6/medrag-agent/tree/81a1519)。另见
[变更记录](CHANGELOG.md) 与 [来源归属](data/demo/conversations/README.md)。
