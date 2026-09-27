# 启动、模型配置与排错

当前产品主入口是 Ask。首次安装按 [README](../README.md)，对话操作按
[对话指南](conversation-guide.md)。本页合并旧 `PORTS.md` 和 `demo.md` 中仍有效的配置。

## 选择一种启动方式

| 目的 | 命令 | 前端 / 后端 | 需要什么 |
|---|---|---|---|
| 无密钥看真实保存对话 | `python scripts/run_showcase.py` | 5173 / 8000 | 轻量 Python 环境、Node；无模型、索引 |
| 新提问、追问及逐轮审计 | `python scripts/run_demo.py --conversations` | 5173 / 8000 | 完整 Python 依赖、模型、BGE、演示索引 |
| 独立审计 / Research 工作台 | `python scripts/run_audit_demo.py` | 5174 / 8001 | 回放无模型；新审计用 Flash |
| 看手写 UI 示例 | `npm --prefix frontend run dev`，访问 `/?demo=1` | 5173 / 无 | 这是 authored fixture，不是真实推理 |

默认只监听本机。前两种使用相同端口，切换前停止旧服务。启动器等待 API 就绪、设置
Vite 模式和 API 地址，Ctrl+C 停止本次启动的子进程。不要同时让两个完整 API 打开同一个
嵌入式 Qdrant 目录。`--skip-index` 只在对应语料索引已成功建立后使用。

Live 演示使用 `.demo-runtime` 的独立数据目录和索引，不需要修改研究语料。
`--conversations` 使用三篇论文的 15 段摘要；`--medical` 是单篇 GRADE；不带参数的旧模式
使用三段编写的示例。它们都不是完整 PubMed，也不共享旧评测的 44,768 个 chunks。

## 当前 Flash 配置

在仓库根目录复制 `.env.example` 为 `.env` 后编辑。真实密钥只放本机忽略文件。
以下模型标识来自已保存实验；若使用别的兼容网关，填写该网关实际提供的标识。

```dotenv
LLM_BACKEND=openhub
OPENHUB_BASE_URL=https://www.cun.ai/v1
OPENHUB_API_KEY=your-gateway-key
OPENHUB_MODEL=DeepSeek-V4.1-Flash
OPENHUB_REASONING_EFFORT=high
OPENHUB_MAX_TOKENS=32768
LLM_TIMEOUT_SECONDS=240
```

`openhub` 是保留的适配器名，实际端点由配置决定。生成和检查都用 Flash，没有自动 Pro
回退。修改后重启后端；显式 shell 环境变量优先于 `.env`。输出 token 是单次上限，
不是目标消耗或整题预算。模型返回名称只是网关元数据，不证明不同网关底层权重相同。
研究选择和成本边界见 [Flash 决定](decisions/2026-09-23-flash-research-baseline.md)。

## 可选本地模型

```dotenv
LLM_BACKEND=ollama
OLLAMA_HOST=http://127.0.0.1:11434
OLLAMA_MODEL=qwen3.5:9b
LLM_TIMEOUT_SECONDS=240
```

先执行 `ollama pull qwen3.5:9b`。这是可选运行方式，不改写已保存 Flash 实验的模型条件。
服务监听值 `0.0.0.0:11434` 会转换成本机连接地址；显式远程或容器主机保持原配置。
云模型会收到问题及选中的文献段落。MCP 入口另有 [本地控制](mcp_security.md)，不等于
网页 API 已实现公共多用户认证。

## 端口和旧入口

Ask 的 Vite `/api` 和 WebSocket 代理到 8000；独立工作台直连 8001，允许本机 5174 的
浏览器来源。只改前端端口不会同步修改 API 和 CORS。

| 可选入口 | 范围 |
|---|---|
| 6333 | 服务型 Qdrant；标准小演示使用嵌入式 `QDRANT_PATH`，不需要该服务 |
| 11434 | Ollama，仅本地模型需要 |
| `start_dev.ps1` / `start_setup.ps1` | 旧 conda / Docker 完整语料流程，非轻量回放入口 |
| `start_mcp.ps1` | 本地 stdio MCP，不占 Ask HTTP 端口 |
| Docker Compose | 旧完整栈；配置保留，v0.8 未在本机实际演练，不作为已验证启动路径 |

## 常见问题

- **401 / 余额不足：**检查本地模型配置并重启；保存回放仍可使用。
- **端口占用：**停止之前启动的对应服务，再运行启动器。
- **第一次搜索慢：**首次下载、加载 BGE 与建立索引需要时间，之后才是热启动。
- **问的论文不在演示中：**使用对应演示问题或自行导入语料；不能拿旧 benchmark 题测三篇论文索引。
- **超时 / 无效结构化输出：**这是执行失败，不是“原文没有证据”。网页 API 整体期限约 300 秒，
  浏览器后备期限 310 秒；只增加单次模型超时不会延长整条流程。
- **刷新后找不到聊天：**会话保存在当前浏览器源的 IndexedDB；5173 与 5174、不同浏览器不共享。
  跨环境迁移请导出完整会话再导入。

历史实验重算与付费新运行分开说明在 [研究复现](research-reproduction.md)，不再混入启动指南。
