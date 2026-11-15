# Dresm 工作室 · 第 2 周-轻量可观测 Agent

          模型先思考，再执行行动、调用工具；工具返回的结果作为观察信息回传给模型，模型基于上一轮得到的观察继续思考，循环往复，直到收集到足够信息，再输出最终答案。
        每轮都留下 Thought / Action / Observation 轨迹，带 Schema 校验、解析失败重试、指数退避、步数上限和 Token 用量统计。

---

## 目录结构

```
second_week/
├── .env                 # 本地密钥与配置（不要提交）
├── .env.example         # 配置模板，只写变量名
├── .gitignore
├── requirements.txt
├── README.md
├── scheme.py            # Pydantic Schema：Step / FinalAnswer / 工具入参
├── tools.py             # 本地工具：get_weather、search
└── agent.py             # 系统提示 + 主循环 + 退避 + USAGE
```

---

## 环境要求

- Python 3.10+
- 可访问的 OpenAI 兼容接口（示例用 DeepSeek）
- 可选：SERPAPI_API_KEY（`search` 工具需要）

---

## 1. 配置

```ini
复制 .env.example，重命名为 .env，填写密钥：
LLM_API_KEY=<填入你的大语言模型的API_KEY>
LLM_MODEL_NAME=<填入你的模型名称>
LLM_BASE_URL=https://api.deepseek.com
MAX_RETRIES=5
MAX_STEPTS=3
SERPAPI_API_KEY=<填入你的serpapi的API_KEY>
```

**不要把 `.env` 提交到仓库**，`.gitignore` 里应包含：

```
.env
__pycache__/
*.log
venv/
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
openai
pydantic
python-dotenv
tenacity
serpapi
```

---

## 3. 运行

```powershell
python agent.py
```

启动后输入问题，例如：

```
上海今天适合户外跑步吗？结合天气给建议
```

预期过程（终端）：

```
----第1次调用大模型----
----第2次调用大模型----
Final Answer:适合跑步。上海今天 24.5℃、多云、东南风 3 级、湿度 68%……
```

---

## 4. 日志与轨迹

运行日志写在当前目录的 `agent1.log`，格式为：

```
时间 - 模块 - 级别 - 内容
```

每轮包含四个关键行：

| 行              | 含义                                     |
| -------------- | -------------------------------------- |
| `Thought:`     | 模型这一步的意图                               |
| `Action:`      | 调用了哪个工具、参数是什么（或 `Finish`）              |
| `Observation:` | 工具返回的 JSON                             |
| `USAGE`        | 本步 `tokens_in` / `tokens_out` / `cost` |

查看最近一条完整轨迹：

```powershell
Get-Content agent1.log -Tail 30
```

用量单价按输入 2 元/百万 token、输出 8 元/百万 token 估算（`agent.py` 内 `cost_rmb`）。

---

## 5. 关键机制在哪

| 机制                        | 位置                                                                                      |
| ------------------------- | --------------------------------------------------------------------------------------- |
| 系统提示（角色 / 工具 / 输出格式 / 规则） | `agent.py` 主循环内的 `prompt`                                                               |
| 最大步数                      | `agent.py` 读取 `MAX_STEPS`，主循环 `while` 判断                                                |
| 指数退避                      | `agent.py` 的 `@retry` 装饰器：`wait_exponential(min=2, max=10)`，仅对 429 / 超时 / 连接错误 / 5xx 生效 |
| 解析失败重试                    | `agent.py` 的两个 `except`：`Step` 校验失败、`FinalAnswer` 校验失败，回填错误后进入下一轮                       |
| USAGE                     | `agent.py` 每步打印 `tokens_in / tokens_out / cost`                                         |

---

## 6. 怎么确认它真的有效

## 运行演示脚本：

     python test.py

```
日志中应出现 FinalAnswer解析失败 ... confidence Field required，下一轮模型补上该字段后通过。
```

---

## 7. 常见问题

| 现象                                             | 原因 / 处理                                         |
| ---------------------------------------------- | ----------------------------------------------- |
| `请确保LLM_API_KEY，LLM_BASE_URL，LLM_MODEL_NAME存在` | `.env` 没读到，或路径不对                                |
| 一直 `解析失败，重试中`                                  | 模型输出不是合法 JSON；检查 `response_format` 与提示词是否被改动    |
| `MAX_STEPS` 改了不生效                              | 确认代码读取的变量名与 `.env` 完全一致（曾出现 `MAX_STEPTS` 拼写问题）  |
| `search` 工具报配置错误                               | 未设置 `SERPAPI_API_KEY`，或用 `get_weather` 即可完成演示   |
| 城市查不到                                          | `get_weather` 是本地假工具，只收录 上海 / 北京 / 深圳 / 湘潭 / 弥勒 |

---

## 8. 说明

- 天气工具是本地假数据，目的是跑通调用链路，不是真实天气服务。
- 解析失败的重试会占用一次步数，所以 `MAX_STEPS` 很小时可能来不及给出最终答案，属正常现象。


