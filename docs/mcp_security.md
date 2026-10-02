# MCP：已经实现的控制与边界

[English](en/mcp_security.md) | **简体中文**

按 v0.8 里程碑整理后的源码说明。**authentication、rate limiting、audit logging 都在仓库中，
但只用于 MCP 工具，不自动保护网页 FastAPI。** 这是本地研究工具，不是公共多用户服务。
早期“5 层安全 / 合规”描述已由本页替代；旧测试报告仅留作历史。

## 请求实际经过什么

`src/medrag/mcp_server/server.py` 的工具执行外围记录结果与耗时；进入工具前依次：

1. `verify_token`：读取 `MEDRAG_LOCAL_TOKEN`，用 `hmac.compare_digest` 比较工具参数。
   变量未设置时明确记录 warning 并关闭认证；设置为空串会拒绝请求，不能当作启用后的有效口令。
2. `check_rate_limit`：进程内令牌桶，所有工具容量 30、每分钟补充 30；`ask_agent`
   另有容量 10、每分钟补充 10。允许初始 burst，并非每个滑动窗口绝不超过 30/10。
3. `redact`：先对查询做常见 PII 正则替换，再交给检索/生成。
4. `sanitise_query`：已知注入模式拒绝、特殊 token 处理、数据边界包装。

实现：[auth.py](../src/medrag/mcp_server/security/auth.py)、
[rate_limit.py](../src/medrag/mcp_server/security/rate_limit.py)、
[pii.py](../src/medrag/mcp_server/security/pii.py)、
[injection_guard.py](../src/medrag/mcp_server/security/injection_guard.py)。
正则有漏报/误报，不保证去除所有身份信息、抵御任意提示注入或满足任何合规要求。
检索到的文献、用户提供的 context_chunks、模型输出也不是靠查询清洗就变成可信内容。

## 工具与会话

| 工具 | 行为 |
|---|---|
| `search_literature` | dense/sparse 检索，可选重排，返回最多十项摘要片段 |
| `ask_agent` | 完整回答图；每次独立 checkpoint；`thread_id` 仅保留调用方标签 |
| `evaluate_query` | 对最多十个给定文本片段评分；分数是模型判断，未校准 |
| `search_visual` | 明确返回 `not_implemented`，不能宣传为已实现图像检索 |

MCP 未接入网页 v0.8 的显式历史指代解释器，不能把重复使用 thread_id 称为多轮记忆。
本轮修复了旧实现复用默认检查点导致 additive 状态继承的问题；网页多轮用浏览器快照。
作为模块加载时不再自动后台加载 BGE；实际调用按需加载。直接执行服务器脚本时仍可预热。

## 日志究竟记录什么

[audit.py](../src/medrag/mcp_server/security/audit.py) 写入
`$MEDRAG_DATA_DIR/logs/audit.jsonl`（默认 `data/logs/audit.jsonl`）：时间、工具名、
原查询 SHA-256 前 16 个十六进制字符、耗时和结果。Ask 在可用时记录模型回调 token 用量；
这不是提供方账单。认证/限流/查询拒绝也记录，视觉占位成功标为 `stub`。

不存原查询字符串或令牌。哈希仍可关联重复查询，不是匿名化保证。文件为普通可改写 JSONL，
没有签名、防篡改、跨进程统一配额、轮转或集中审计；写入失败记录本地错误但不阻止工具执行。
因此不能称为“不可抵赖审计”或整个 Agent 的隐私保证。

## 使用与可复现检查

默认传输是本地 stdio。安装完整依赖后使用现有 `start_mcp.ps1`，或：

```sh
fastmcp dev inspector src/medrag/mcp_server/server.py --with-editable .
```

若需要令牌，在本地服务器环境配置 `MEDRAG_LOCAL_TOKEN`，客户端每次通过 `token` 工具参数传入。
密钥不要写进 Git。网络传输的身份/权限隔离不是本项目已交付的公共部署能力。

离线实现检查：

```sh
python -m pytest -q tests/test_mcp_security.py tests/test_mcp_invocation.py
```

这些检查覆盖规则与独立调用行为，不证明安全攻击全集、真实模型质量或外部 MCP 客户端端到端运行。
网页 API 没有这些 MCP 令牌/限流/日志；网页审计的三槽并发限制仅约束单进程运行数，不是访问控制。
