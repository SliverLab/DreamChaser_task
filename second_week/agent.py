from openai import OpenAI
import os
import json
from dotenv import load_dotenv
import logging
import time
from tools import TOOLS,TOOL_REGISTRY,ToolError
from scheme import FinalAnswer,Step
import tiktoken


logger=logging.getLogger(__name__)
dotenv_path=r"D:\个人文件\DreamCharser\final_version\.env"
load_dotenv(dotenv_path=dotenv_path)
MAX_RETRIES=int(os.getenv("MAX_RETRIES","3"))
LLM_API_KEY=os.getenv("LLM_API_KEY")
LLM_BASE_URL=os.getenv("LLM_BASE_URL")
LLM_MODEL_NAME=os.getenv("LLM_MODEL_NAME")
MAX_STEPTS=int(os.getenv("MAX_STEPTS","8"))
if not all  ([LLM_API_KEY,LLM_BASE_URL,LLM_MODEL_NAME,MAX_STEPTS]):
    raise ValueError("请确保LLM_API_KEY，LLM_BASE_URL，LLM_MODEL_NAME存在")
client=OpenAI(
    api_key=LLM_API_KEY,
    base_url=LLM_BASE_URL,
    max_retries=0
)


def _tools_block():
    lines=[]
    for tool in TOOLS:
        fn=tool["function"]
        params=fn["parameters"]
        props=params.get("properties",{})
        required=params.get("required",[])
        lines.append(f"-{fn['name']}:{fn['description']}-")
        for param,others in props.items():
                tag="必填"if param in required else "可选"
                desc=others.get("description","")
                ptype=others.get("type","string")
                lines.append(f"-{param}({ptype},{tag}):{desc}")
    return '\n'.join(lines)


def run(question:str):
    history=[]
    current_stepts=1
    while current_stepts<MAX_STEPTS+1:
        print(f"----第{current_stepts}次调用大模型----")
        his_str="\n".join(history)
        prompt=f'''你是一个可以使用工具的 AI 助手。每一步只输出一个 JSON 对象，不要输出任何额外文本、不要用 Markdown、不要解释。
JSON 必须严格符合以下结构：
{{"thought": "你的推理过程", "action": "工具名或 Finish", "action_input": {{...}}}}
规则：
1. 需要工具时，action 填工具名，action_input 填该工具的参数对象。
2. 信息足够时，action 填 "Finish"，action_input 填最终答案：
   {{"summary": "一两句话给出可执行建议", "sources": ["实际用过的工具名"], "confidence": 0.8}}
   - confidence 是 0 到 1 之间的小数，不是百分数。
   - sources 只填真实调用过的工具名，没调用就填 []。
3. 收到 Observation 后继续下一轮。
4. 不要用相同参数重复调用同一个工具。
5. 信息足够时必须 Finish，不要继续调工具。

历史交互：{his_str}

可用工具：
{_tools_block()}

示例 1（需要工具）：
{{"thought": "需要查北京天气。", "action": "get_weather", "action_input": {{"city": "北京"}}}}

示例 2（收尾）：
{{"thought": "已拿到结果，可以给建议。", "action": "Finish", "action_input": {{"summary": "北京今天 18℃ 晴天。", "sources": ["get_weather"], "confidence": 0.9}}}}
'''
        messages=[
            {"role":"system","content":prompt},
            {"role":"user","content":question}
        ]
        try:
            response=client.chat.completions.create(
                model=LLM_MODEL_NAME,
                messages=messages,
                response_format={
                    "type":"json_object",
                }
            )
            msg=response.choices[0].message
            step=Step.model_validate_json(msg.content or "")
            history.append(f"Thought:{step.thought}")
            history.append(f"Action:{step.action},Action_input:{step.action_input}")
            logger.info(f"Thought:{step.thought}")
            logger.info(f"Action:{step.action},Action_input:{step.action_input}")
            if step.action=="Finish":
                final_answer=FinalAnswer.model_validate(step.action_input)
                logger.info(f"Final Answer:{final_answer.summary}")
                print(f"Final Answer:{final_answer.summary}")
                history.append(f"Final Answer:{final_answer}")
                break
            else:
                if step.action not in TOOL_REGISTRY:
                    observation=json.dumps(
                        {"error":f"未知工具:{step.action},可用工具：{list(TOOL_REGISTRY)}"},
                        ensure_ascii=False
                    )
                    history.append(f"Observation:{observation}")
                    current_stepts+=1
                    continue
                func,ArgsModel=TOOL_REGISTRY[step.action]
                try:
                    results=func(ArgsModel.model_validate(step.action_input))
                    observation=json.dumps(results,ensure_ascii=False)
                except ToolError as e:
                    observation=json.dumps({"error":str(e)},ensure_ascii=False)
                history.append(f"Observation:{observation}")
                logger.info(f"Observation:{observation}")
        except Exception as e:
            logger.error(f"因{e}发生错误，程序终止")
            break
        current_stepts+=1


                
if __name__ =="__main__":
    logging.basicConfig(
        filename="agent1.log",
        level=logging.INFO,
        format="%(asctime)s -%(name)s -%(levelname)s -%(message)s"
    )
    question=input("请输入您的问题：")
    run(question)