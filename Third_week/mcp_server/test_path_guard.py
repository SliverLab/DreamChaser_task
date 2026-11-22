r"""路径白名单自测：验证"越界路径被拒绝"。

用 MCP 官方 Client 以 in-process 方式连上 server.py 里的 MCPServer，
走的是真实的 MCP 协议分派，但不需要起子进程，方便本地反复跑。

用法（在 Third_week 目录下）：
    ..\venv\Scripts\python.exe mcp_server\test_path_guard.py

明细（参数、isError、工具返回的完整文本）全部写进 logs/test_guard.log，
控制台只打印最后一行汇总；退出码 0=全过，1=有失败。
"""

import asyncio
import importlib.util
import logging
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR.parent / "logs"
LOG_FILE = LOG_DIR / "test_guard.log"

logger = logging.getLogger(__name__)


def setup_logging() -> None:
    """日志只写文件；logs 目录不存在时自动创建。"""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=LOG_FILE,
        filemode="w",
        encoding="utf-8",
        level=logging.INFO,
        format="%(asctime)s -%(name)s -%(levelname)s -%(message)s",
        force=True,
    )


# 按路径导入 server.py，避免包名冲突
spec = importlib.util.spec_from_file_location("week3_server", BASE_DIR / "server.py")
server_module = importlib.util.module_from_spec(spec)
sys.modules["week3_server"] = server_module
spec.loader.exec_module(server_module)

from mcp import Client  # noqa: E402

# (工具名, 参数, 期望出现的文本)
CASES = [
    ("encrypt_file", {"filename": "../secret.txt", "confirm": True}, "安全拦截"),
    ("encrypt_file", {"filename": "../../Windows/win.ini", "confirm": True}, "安全拦截"),
    ("encrypt_file", {"filename": r"C:\Windows\win.ini", "confirm": True}, "安全拦截"),
    ("decrypt_file", {"filename": "../secret.txt"}, "安全拦截"),
    # 对照组：文件名合法但沙箱里没有，应该报"不存在"而不是"安全拦截"
    ("encrypt_file", {"filename": "no_such_file.txt", "confirm": True}, "不存在"),
]


async def main() -> int:
    setup_logging()
    failures = 0
    async with Client(server_module.mcp) as client:
        tools = await client.list_tools()
        logger.info("已连接 My-Agent-Server，工具列表: %s", [t.name for t in tools.tools])

        for name, args, expect in CASES:
            result = await client.call_tool(name, args)
            text = "\n".join(
                getattr(block, "text", "") for block in result.content
            ).strip()
            ok = expect in text
            failures += 0 if ok else 1

            logger.info("[%s] %s(%s)", "PASS" if ok else "FAIL", name, args)
            logger.info("        isError = %s", result.is_error)
            logger.info("        返回    = %s", text)

    total = len(CASES)
    logger.info("结果：%s/%s 通过", total - failures, total)
    logger.info("沙箱目录：%s", server_module.SANDBOX_DIR)
    print(f"结果：{total - failures}/{total} 通过，明细见 {LOG_FILE}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
