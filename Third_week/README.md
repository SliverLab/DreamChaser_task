# 第 3 周-MCP + 双层记忆 Agent

    工具不再写死在Agent里：启动时用stdio拉起自己写的MCP Server，list_tools()拿到工具清单，模型决定调用时走call_tool()，工具名、参数、返回值全部落日志。
    记忆分两层：短期只把最近WINDOW_TURNS轮原文发给模型，被挤出窗口的旧对话压成摘要；值得长期留存的信息按日期追加到memory/MEMORY.md，关掉程序再打开还在。

---

## 目录结构

```
Third_week/
├── .env.example            # 配置模板，只写变量名
├── .gitignore
├── requirements.txt
├── README.md
├── mcp_server/
│   ├── server.py           # MCP Server：search/encrypt_file/decrypt_file/github_repo_info
│   ├── test_path_guard.py  # 路径白名单自测（in-process，走真实 MCP 协议分派）
│   └── sandbox/            # 工具唯一允许读写的目录
├── agent/
│   ├── agent.py            # MCP 客户端 + 主循环 + 重试 + USAGE
│   └── memory.py           # 双层记忆：滑动窗口 / 摘要压缩 / MEMORY.md
├── memory/
│   ├── MEMORY.md           # 长期记忆（一条一行，带日期）
│   └── memory.json         # 短期记忆运行时状态（每轮整份重写）
├── logs/
│   ├── week3.log           # Agent 运行日志
│   └── test_guard.log      # 越界路径自测明细
```

---

## 环境要求

- Python 3.10+（本机实测 3.12.9）
- `mcp` 2.x
- 可访问的 OpenAI 兼容接口（示例用 DeepSeek）
- 可选：Node.js 18+（只为了跑 MCP Inspector）
- 可选：`SERPAPI_API_KEY`（`search` 工具需要）

---

## 1. 配置

复制 `.env.example`，重命名为 `.env`，填写密钥：

```ini
LLM_API_KEY=<填入你的大语言模型的API_KEY>
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL_NAME=deepseek-chat
MAX_RETRIES=3
MAX_STEPTS=8
SANDBOX_KEY=<Fernet.generate_key().decode() 生成的密钥>
WINDOW_TURNS=4
TOKEN_BUDGET=3000
SERPAPI_API_KEY=<填入你的serpapi的API_KEY>
```

`SANDBOX_KEY` 用这一行生成，整串复制进 `.env`，不要换行、不要加引号：

```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

`.gitignore` 

```
**/.env
venv/
**/__pycache__/
*.log
.playwright-mcp/

# 短期记忆：运行时状态，每次对话都会整份重写，不纳入版本库
memory/memory.json
```

---

## 2. 安装依赖

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

`requirements.txt`：

```
mcp
pydantic
python-dotenv
tenacity
openai
psutil
cryptography
serpapi
requests
```

---

## 3. 运行

### 3.1 先单独验 MCP Server（MCP Inspector）

在 `Third_week` 目录下、激活虚拟环境后：

```powershell
npx @modelcontextprotocol/inspector python mcp_server/server.py
```

浏览器打开调试页 → **Connect** → **Tools** → **List Tools**，应看到 4 个工具；逐个填参数运行，看返回值。

### 3.2 跑路径白名单自测

```powershell
python mcp_server/test_path_guard.py
```

预期输出：

```
结果：5/5 通过，明细见 D:\...\Third_week\logs\test_guard.log
```

用例覆盖 `../secret.txt`、`../../Windows/win.ini`、`C:\Windows\win.ini`、`decrypt_file` 越界，以及一个"文件名合法但沙箱里没有"的对照组（应报"不存在"而不是"安全拦截"）。退出码 0 表示全过。

### 3.3 跑 Agent

```powershell
python agent/agent.py
```

启动后先握手，再出现输入提示：

```
请输入您的问题
```

试试这三句：

```
帮我查一下 openai/openai-python 这个仓库有多少 star
帮我把 test 文件加密
我的项目代号和截止日期是什么？
```

预期过程（终端）：

```
----第1次调用模型----
----第2次调用模型----
最终回答：已加密完毕。…
```

---

## 4. MCP Server 的 4 个工具

| 工具               | 干什么                                                                   | 安全设计                                                                                      |
| ------------------ | ------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------- |
| `search`           | 用 SerpAPI 走 Google 搜关键词，优先返回答案框 / 知识图谱，其次前两条摘要 | 密钥只在服务端读；结果按 300 / 200 / 500 字符截断，避免一次塞爆上下文                         |
| `encrypt_file`     | 用 Fernet 加密 `sandbox/` 里的文件，**原地覆盖**                         | 路径白名单；`confirm=False` 时只返回 `pending_confirmation`，不写盘；文件不存在抛 `ToolError` |
| `decrypt_file`     | 解密 `sandbox/` 里的文件，**原地覆盖**                                   | 路径白名单；文件不存在抛 `ToolError`；密钥与密文不匹配时由 Fernet 抛 `InvalidToken`           |
| `github_repo_info` | 查公开仓库的 star 数与最后推送时间                                       | URL 模板写死 `api.github.com`；`timeout=5`；超时 / 非法 JSON / 字段缺失都返回结构化错误       |

实现要点：

- 用 `@mcp.tool()` 装饰，参数带类型；**docstring 就是给模型看的工具说明**，所以写清楚干什么、参数是什么。
- `_get_safe_path()` 先 `resolve()` 再 `is_relative_to(SANDBOX_DIR)`，`../`、`..\..\`、`C:\` 都会被拦下。
- 业务失败一律 `raise ToolError("人话错误提示")`，不要 `raise ValueError` —— 普通异常会被 SDK 统一改写成 `Error executing tool xxx`，模型看不到真实原因
- 传输方式固定 `mcp.run(transport="stdio")`，由客户端拉起子进程，不需要监听端口。

---

## 5. Agent 怎么接上 MCP

`agent/agent.py` 的主流程：

```
stdio_client 拉起 server.py
  └─ ClientSession.initialize()          握手
  └─ list_tools()                       把 MCP 工具转成 OpenAI tools 格式
  └─ 主循环：模型 → tool_calls → call_tool() → 结果以 role=tool 回传 → 再问模型
```

- 工具清单**不是写死的**，每次启动都从 `list_tools()` 现取，日志里会打印 `发现4个工具：['search', 'encrypt_file', 'decrypt_file', 'github_repo_info']`。
- 工具报错时，错误原文就在返回文本里（`Error executing tool encrypt_file: 安全拦截…`），会作为 `role=tool` 消息交给模型，模型据此纠正参数；JSON-RPC 层异常则降级成"工具通信异常"。
- 二次确认靠返回值约定：工具返回 `status == "pending_confirmation"` 时，Agent 立刻停止本轮工具循环，把提示复述给用户；用户回"确认"后，下一轮模型才会带 `confirm=true` 再调一次。
- LLM 请求包了 `@retry`：只对超时 / 连接错误 / 429 / 5xx 生效，`wait_exponential(min=2, max=10)`，次数取 `MAX_RETRIES`；每次成功都记一条"第 N 次请求尝试后成功响应"。

---

## 6. 双层记忆在哪

| 机制         | 位置                                       | 行为                                                                                                                        |
| ------------ | ------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------- |
| 滑动窗口     | `memory.py` → `build_messages()`           | 只拼最近 `WINDOW_TURNS`（默认 4）轮原文，加上当前这轮                                                                       |
| 摘要压缩     | `memory.py` → `compress_memory()`          | 旧轮数超出窗口或 token 估算超 `TOKEN_BUDGET` 时，把旧轮交给模型压成一段摘要，放在系统提示后面，然后裁掉旧轮                 |
| Token 估算   | `memory.py` → `estimate_token()`           | 中文按 0.6、其他字符按 0.3 粗估，再乘 1.2 安全系数；只用于判断"要不要压缩"                                                  |
| 长期记忆写入 | `memory.py` → `extract_long_term_memory()` | 每轮结束让模型判断有没有新信息（姓名、偏好、项目代号、约定），有就按 `- YYYY-MM-DD 内容` 追加进 `MEMORY.md`；输出"无"则跳过 |
| 长期记忆加载 | `memory.py` → `__init__()`                 | 启动时读 `MEMORY.md`，拼进系统提示，所以重开程序还记得                                                                      |
| 短期记忆落盘 | `memory.py` → `save()`                     | `memory/memory.json` 结构为 `{"summary": "...", "turns": [[...], [...]]}`，每轮整份重写                                     |

---

## 7. 日志与轨迹

运行日志写在 `Third_week/logs/week3.log`，格式为：

```
时间 - 模块 - 级别 - 内容
```

一次工具调用会留下这几行：

| 行                                  | 含义                             |
| ----------------------------------- | -------------------------------- |
| `----第N次调用模型----`             | 本轮第几步                       |
| `USAGE tokens_in=...`               | 本步输入 / 输出 token 与估算花费 |
| `模型决定调用工具：xxx`             | 工具名 + 参数                    |
| `工具返回结果：...`                 | MCP `call_tool()` 返回的文本     |
| `历史记忆成功压缩，新摘要：...`     | 短期记忆触发压缩                 |
| `成功在MEMORY.md中追加一条长期记忆` | 长期记忆写入                     |

查看最近一段轨迹：

```powershell
Get-Content logs/week3.log -Tail 30
```

用量单价按输入 2 元/百万 token、输出 8 元/百万 token 估算（`agent.py` 内 `cost_rmb`）。

---

## 8. 怎么确认它真的有效

| 验收项         | 怎么复现                                                                                                          | 看什么                                                                   |
| -------------- | ----------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| 记忆跨窗口     | `WINDOW_TURNS=4`，第 1 轮说"我叫小明，项目代号蓝鲸-42，截止 12 月 5 日"，第 2～9 轮聊别的，第 10 轮问代号和截止日 | 第 10 轮答对；`memory.json` 只剩 4 轮，答案来自 `summary` 或 `MEMORY.md` |
| 越界路径被拒绝 | `python mcp_server/test_path_guard.py`                                                                            | `5/5 通过`，`isError = True`，报错含"安全拦截"                           |
| 敏感操作先确认 | 在 Agent 里说"帮我把 test 加密"                                                                                   | 先打印 `即将加密文件 [test]…`，不会直接写盘；回"确认"后才加密            |
| 关掉重开还记得 | 关掉 `agent.py` 再启动，问"我叫什么、项目代号是什么"                                                              | 能答出 `MEMORY.md` 里的内容                                              |
| Inspector 自测 | 见 3.1                                                                                                            | 4 个工具都能列出并调用成功                                               |

---

## 9. 常见问题

| 现象                                                                                   | 原因 / 处理                                                                                                                                          |
| -------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| `请确保LLM_API_KEY，LLM_BASE_URL，LLM_MODEL_NAME存在`                                  | `.env` 没读到，或不在启动目录的上级路径里；确认文件名不是 `.env.txt`                                                                                 |
| `InvalidToken` / Fernet 初始化报 `Fernet key must be 32 url-safe base64-encoded bytes` | `SANDBOX_KEY` 填错、带引号或多复制了空格；用第 1 节那条命令重新生成                                                                                  |
| 启动即 `ValueError: invalid literal for int() with base 10: ''`                        | `.env` 里 `MAX_STEPTS=` 留空；删掉该行或填整数                                                                                                       |
| `MAX_STEPTS` 改了不生效                                                                | 变量名就是 `MAX_STEPTS`（沿用了第 2 周的拼写），大小写与 `.env` 必须完全一致；改完要重启 `agent.py`                                                  |
| `FileNotFoundError: ...server.py`                                                      | `agent.py` 里写死的绝对路径失效；改成相对 `BASE_DIR` 拼路径                                                                                          |
| 客户端只看到 `Error executing tool xxx`                                                | 工具内部 `raise` 了普通异常；改成 `raise ToolError("原因")`（见 `第三周考核.md`）                                                                    |
| `search` 返回 `404 Not Found` 或提示未配置                                             | `SERPAPI_API_KEY` 缺失 / 额度用尽；演示时可改用 `github_repo_info`                                                                                   |
| 加密后 `decrypt_file` 报 `InvalidToken`                                                | 换了 `SANDBOX_KEY`；旧密文只能用旧密钥解，重新放一份明文再加密                                                                                       |
| 一直在问"是否确认"                                                                     | 模型没收到 `confirm=true`；确认时明确说"确认加密"，或直接在 Inspector 里带 `confirm: true` 调用                                                      |
| 记忆好像没生效                                                                         | `memory.json` 只留 4 轮是正常的，答案在 `summary` / `MEMORY.md`；先看日志有没有"已压缩""追加"记录                                                    |
| Inspector 连不上                                                                       | 命令里的 `python` 不是装了 `mcp` 的那个解释器；在激活的 venv 里跑，或写全 `..\venv\Scripts\python.exe`                                               |
| 日志里没有"工具执行报错"前缀                                                           | `agent.py` 检查的是 `getattr(result, "isError")`，而 mcp 2.3.0 的字段名是 `is_error`；错误原文仍在 tool 消息里，把属性名改成 `is_error` 才会加上前缀 |

---

## 10. 说明

- `sandbox/` 是工具唯一允许读写的目录，`encrypt_file` / `decrypt_file` 都是原地覆盖，演示前先备一份明文。
- `github_repo_info` 只走 `api.github.com`，超时 5 秒；超时不会卡死服务，只会返回结构化错误。
- 长期记忆是"追加 + 去重提示"，不是向量检索；重复信息靠提示词里的"已有长期记忆"约束，模型仍可能偶尔重复，属已知限制。
- `.env`、`memory/memory.json`、`*.log` 都不进版本库；`MEMORY.md` 作为交付证据保留。
