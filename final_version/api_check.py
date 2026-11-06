#!/usr/bin/env python
"""Dresm 工作室第 1 周 · 第 5 项：终端验证 .env 里的密钥配置是否正确

用法：
    python api_check.py            真实请求一次模型，收到回复即判定通过
    python api_check.py --dry-run  只校验 .env 是否齐全，不联网、不消耗额度

退出码：0 通过 / 1 配置问题 / 2 密钥无效(401) / 3 模型名不对(404)
        4 网络或代理不通 / 5 限流、余额或其他异常

安全约定：脚本只打印密钥的前 4 位和长度，截图不会泄露真实密钥。
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

ENV_FILE = Path(__file__).resolve().parent / ".env"
# 同时兼容 .env.example 里的 LLM_ 前缀写法和任务书里 API_KEY/BASE_URL/MODEL 的写法
ALIASES = {
    "api_key": ("LLM_API_KEY", "API_KEY"),
    "base_url": ("LLM_BASE_URL", "BASE_URL"),
    "model": ("LLM_MODEL_NAME", "MODEL"),
}
PLACEHOLDERS = {"", "sk-xxx", "your_api_key", "your-key", "xxx", "填你的key", "无"}


def step(index: int, total: int, title: str) -> None:
    print(f"[{index}/{total}] {title}")


def mask(secret: str) -> str:
    """只显示前 4 位，保证截图可以公开。"""
    if len(secret) <= 4:
        return f"****（长度 {len(secret)}，过短，很可能不是完整密钥）"
    return f"{secret[:4]}****（长度 {len(secret)}）"


def load_env() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        print("[×] 缺少 python-dotenv，请先执行：pip install python-dotenv")
        sys.exit(1)
    if not ENV_FILE.exists():
        print(f"[×] 当前目录下找不到 .env：{ENV_FILE}")
        print("    请先把 .env.example 复制一份改名为 .env，再填入自己的配置。")
        sys.exit(1)
    # 显式按脚本所在目录加载，避免在别的目录运行时读不到配置
    load_dotenv(dotenv_path=ENV_FILE, override=True)


def read_config() -> tuple[str, str, str]:
    values = {}
    for field, names in ALIASES.items():
        value = None
        for name in names:
            raw = os.getenv(name)
            if raw and raw.strip():
                value = raw.strip()
                break
        values[field] = value
    missing = [ALIASES[f][0] for f in values if not values[f]]
    if missing:
        print(f"[×] .env 里缺少这几项：{', '.join(missing)}")
        print("    对照 .env.example 补齐，变量名不要改。")
        sys.exit(1)

    api_key, base_url, model = values["api_key"], values["base_url"], values["model"]
    print(f"      API_KEY  : {mask(api_key)}")
    print(f"      BASE_URL : {base_url}")
    print(f"      MODEL    : {model}")

    if api_key.lower() in PLACEHOLDERS:
        print("[×] API_KEY 还是占位内容，没填真实密钥。")
        sys.exit(1)
    if not base_url.startswith(("http://", "https://")):
        print(f"[×] BASE_URL 必须以 http:// 或 https:// 开头，现在是：{base_url}")
        sys.exit(1)
    if base_url.rstrip("/").endswith("/chat/completions"):
        print("[×] BASE_URL 只要写到根地址（例如 https://api.deepseek.com），不要带 /chat/completions。")
        sys.exit(1)
    return api_key, base_url, model


def classify(err: Exception) -> tuple[int, str]:
    """把 SDK 异常翻译成人能看懂的结论。"""
    try:
        import openai
    except ImportError:
        return 1, "缺少 openai 库，请先执行：pip install openai"
    rules = [
        ("AuthenticationError", 2, "密钥无效或被拒绝（401）。检查 API_KEY 是否复制完整、有没有多余空格。"),
        ("PermissionDeniedError", 2, "密钥没有该接口权限（403）。"),
        ("NotFoundError", 3, "模型不存在（404）。检查 MODEL 名字拼写，以及 BASE_URL 是否指向了错误的服务商。"),
        ("APITimeoutError", 4, "请求超时。多半是网络或代理问题，确认代理可用后重试。"),
        ("APIConnectionError", 4, "连不上服务器。检查网络、DNS 和代理设置（HTTPS_PROXY）。"),
        ("RateLimitError", 5, "被限流或余额不足（429）。等一会儿再试，或检查账户额度。"),
        ("BadRequestError", 5, "请求参数被拒绝（400），多为模型名或参数不被该服务商支持。"),
    ]
    for name, code, message in rules:
        cls = getattr(openai, name, None)
        if isinstance(cls, type) and isinstance(err, cls):
            return code, message
    return 5, f"未预期的错误：{type(err).__name__}: {err}"


def main() -> int:
    parser = argparse.ArgumentParser(description="验证 .env 中的模型密钥是否配置正确")
    parser.add_argument("--dry-run", action="store_true", help="只检查配置，不发请求")
    parser.add_argument("--timeout", type=float, default=30.0, help="单次请求超时秒数，默认 30")
    args = parser.parse_args()
    total = 5 if not args.dry_run else 4

    step(1, total, "读取 .env")
    load_env()
    print(f"      配置文件 : {ENV_FILE}")

    step(2, total, "检查配置完整性")
    api_key, base_url, model = read_config()
    proxy = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy")
    print(f"      HTTPS_PROXY : {proxy if proxy else '（未设置，直连）'}")

    step(3, total, "准备客户端")
    try:
        from openai import OpenAI
    except ImportError:
        print("[×] 缺少 openai 库，请先执行：pip install openai")
        return 1
    print("      openai SDK 已就绪")

    if args.dry_run:
        step(4, total, "结论")
        print("      配置检查通过（--dry-run 未发起真实请求）")
        return 0

    step(4, total, "发起一次最小请求")
    client = OpenAI(api_key=api_key, base_url=base_url, timeout=args.timeout, max_retries=0)
    started = time.perf_counter()
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "你是连通性检测助手，回答要简短。"},
                {"role": "user", "content": "请只回复两个字：你好"},
            ],
            temperature=0,
            max_tokens=16,
        )
    except Exception as err:  # noqa: BLE001 —— 这里需要把各类异常统一翻译
        code, message = classify(err)
        print(f"[×] {message}")
        print(f"      原始报错：{type(err).__name__}: {err}")
        if proxy and code == 4:
            print("      代理已设置但仍不通，可用 --dry-run 先排除配置问题，再换网络测试。")
        return code

    elapsed = (time.perf_counter() - started) * 1000
    reply = (response.choices[0].message.content or "").strip() or "（返回内容为空）"
    usage = getattr(response, "usage", None)
    tokens = f"{usage.prompt_tokens} 入 / {usage.completion_tokens} 出" if usage else "未知"

    step(5, total, "结论")
    print(f"      连接成功，模型回复：{reply}")
    print(f"      耗时 {elapsed:.0f} ms ｜ 用量 {tokens} ｜ 模型 {model}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
