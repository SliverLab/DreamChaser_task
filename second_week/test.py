# demo_final_retry.py
import json, types, logging
from pathlib import Path
import agent

Path("logs").mkdir(exist_ok=True)
logging.basicConfig(filename="logs/retry-final-20261112.log", level=logging.INFO,
                    format="%(asctime)s -%(name)s -%(levelname)s - %(message)s")

REAL = agent.tenacity_response
state = {"done": False}

def corrupt_finish(*args, **kwargs):
    resp = REAL(*args, **kwargs)                     # 真实响应，用量也是真的
    content = resp.choices[0].message.content or ""
    try:
        obj = json.loads(content)
    except Exception:
        return resp
    ai = obj.get("action_input")
    if obj.get("action") == "Finish" and isinstance(ai, dict) \
            and "confidence" in ai and not state["done"]:
        state["done"] = True
        ai.pop("confidence")                          # 删掉必填字段
        agent.logger.warning("【测试注入】从真实 Finish 响应中删除 confidence")
        resp.choices[0].message.content = json.dumps(obj, ensure_ascii=False)
    return resp

agent.tenacity_response = corrupt_finish
agent.run("上海今天适合户外跑步吗？结合天气给建议")