# 真实回答审计面板

当前为 v0.5 开发功能，入口 `/audit`。它接收一份完整回答和 1–4 份来源文本，
逐条展示模型判定、回答原文范围、来源原文范围和未覆盖文本。
只判断提供文本的支持关系，不自动搜索、修复回答或判定临床证据等级。

## 轻量启动

在包含本功能的开发分支运行以下命令；`v0.4.0` 标签不包含它。
需要 Python 3.12、Node.js 22.12+ 和 uv，不需要 Ollama、Qdrant 或 GPU。
已有完整项目环境可以直接使用，省略安装步骤。

```sh
uv venv --python 3.12
uv pip install -r requirements-audit.txt
uv pip install --no-deps -e .
```

激活环境：PowerShell 用 `.\.venv\Scripts\Activate.ps1`，macOS/Linux 用
`source .venv/bin/activate`。随后从仓库根目录运行：

```sh
python scripts/verification/answer_benchmark.py download
python scripts/run_audit_demo.py
```

打开 **http://127.0.0.1:5174/audit**。启动器会在缺少 `frontend/node_modules` 时执行
`npm ci`，然后开启前端与端口 8001 的轻量 API。Ctrl+C 停止两者。两个端口须空闲。
若不能激活 PowerShell 环境，用 `.\.venv\Scripts\python.exe` 替代命令中的 `python`。

下载步骤取得约 37 MB 的固定版 RAGTruth 数据，只放在忽略的 `.benchmark-runtime/ragtruth/`。
面板用这份缓存恢复来源全文；仓库保存的模型判断不是编写的演示答案。
首次下载及依赖安装需网络；此后保存记录回放无需模型密钥、模型请求或 GPU。
缺少缓存、缓存内容变化、记录与输入哈希不符时显示错误，不拼凑来源。

轻量服务只提供审计功能，因此启动器隐藏 Ask/Explore 导航。完整 FastAPI 应用也注册了
相同 `/api/audit` 路由；原本的 Ask、Explore 和 Guided demo 使用原有启动方式。
审计还没有自动接入 Ask 的生成/修复流程，可复制完整答案和对应来源文本进行独立核查。

## 演示流程

1. 在 **Real saved runs** 选择 RAGTruth 回答和 Direct / Extract → verify 方法。
   标记 **SAVED INFERENCE** 的记录是既有真实模型调用，不是即时生成。
2. 点击回答中带下划线的陈述，展开相应 claim；点引文的 **Locate in full source**，
   在完整来源中定位。点击来源里被标记的文字也能选中对应 claim。
3. 查看 **Uncovered answer text**。灰色未绑定字符、无效引文和请求失败不能被算成通过。
4. 展开 **Run provenance & execution** 查看实际调用、耗时、模型响应标识和用量。
5. 点击 **Export audit JSON** 下载输入、原文位置、判断和执行记录。

截图是实际保存的 `RAGTruth #296 / direct` 运行：“已经退休”被判定为与原文
“即将退休”冲突。这个例子用于展示定位功能，不是可靠性证明。

![实际保存记录与原文定位](assets/v05-answer-audit.png)

## 审计自己的回答

在本地忽略的 `.env` 中配置与项目 README 相同的 Flash profile：

```dotenv
LLM_BACKEND=openhub
OPENHUB_BASE_URL=https://www.cun.ai/v1
OPENHUB_API_KEY=your-gateway-key
OPENHUB_MODEL=DeepSeek-V4.1-Flash
OPENHUB_REASONING_EFFORT=high
OPENHUB_MAX_TOKENS=32768
LLM_TIMEOUT_SECONDS=240
```

点击 **Audit your own answer**，填入回答、来源标题和原文，再点 **Run new audit**。
每个来源最多 50,000 字符、合计最多 80,000，回答最多 12,000；最多提取 24 条 claim。
达到 claim 上限会显示提示。来源只能判断你粘贴的范围，摘要不能当成全文证据。

Direct 发出一次审计调用。Split 先提取，再对每条陈述发出一次调用，可能耗时数分钟且
花费更多 token；本轮比较没有假定拆分一定更好。请求期间显示等待状态，完成后显示实际结果。
**NEW INFERENCE** 是新模型调用；文本发送至本地配置的网关。服务不落盘保存自有文本，
需要保留时主动导出 JSON。完整错误记录也会返回，不能把失败当作“信息不足”。

2026-09-24 已实际提交一个两句操作示例：来源说明样本数为 20、未报告成功率；回答多写了
95% 成功率。新调用在 11.6 秒返回 1 条 Supported、1 条 Insufficient evidence，
并完成 [JSON 导出](assets/v05-live-audit.json)。输入是自拟功能示例，判断来自实际 Flash 调用，
不属于 RAGTruth 评测或独立质量分数。

轻量服务默认绑定本机，是个人研究工具；此 HTTP 入口未增加身份认证，不属于已有 MCP 安全层。

## 状态含义

| 显示 | 含义 |
|---|---|
| Supported | 模型认为给定来源支持所选陈述；并非专家确认 |
| Contradicted | 模型指出与所选陈述不相容的来源文字 |
| Insufficient evidence | 给定文本不足以支持；不代表全世界没有证据 |
| Unresolved quote | 模型的引文或回答范围不能精确绑定，不计为完成核查 |
| Execution failed / Invalid model output | 调用或结构失败，保留原始执行状态 |
| Not checked | 已抽取但未完成核查 |

字符覆盖计数只反映多少非空白字符被有效定位的判断覆盖，不是语义完整性或正确率。
界面不提供未经校准的置信度百分比，也不自动把来源差异升级成文献冲突。

研究结果与限制见 [整段回答审计报告](verification-v0.5-answer-audit.md)；
运行与重算命令见 [工件说明](../data/verification/ragtruth_v1/README.md)。
