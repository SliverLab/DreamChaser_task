import os
import json
import asyncio
import sys
import logging
from dotenv import load_dotenv
from openai import AsyncOpenAI
from mcp import ClientSession,StdioServerParameters
from tenacity import retry,stop_after_attempt,wait_exponential,before_sleep_log,retry_if_exception_type
from openai import APIConnectionError,APITimeoutError,RateLimitError,InternalServerError
from mcp.client.stdio import stdio_client
from memory import MemoryManager
logger=logging.getLogger(__name__)
load_dotenv()
MAX_RETRIES=int(os.getenv("MAX_RETRIES","3"))
LLM_API_KEY=os.getenv("LLM_API_KEY")
LLM_BASE_URL=os.getenv("LLM_BASE_URL")
LLM_MODEL_NAME=os.getenv("LLM_MODEL_NAME")
MAX_STEPTS=int(os.getenv("MAX_STEPTS","8"))
if not all  ([LLM_API_KEY,LLM_BASE_URL,LLM_MODEL_NAME,MAX_STEPTS]):
    raise ValueError("请确保LLM_API_KEY，LLM_BASE_URL，LLM_MODEL_NAME存在")
client=AsyncOpenAI(
    api_key=LLM_API_KEY,
    base_url=LLM_BASE_URL,
    max_retries=0
)

def log_success(retry_state):
    try:
        _=retry_state.outcome.result()
        logger.info(f"LLM在第{retry_state.attempt_number}次请求尝试后，成功响应")
    except:
        pass
        
@retry(
    retry=retry_if_exception_type((
        APITimeoutError,
        APIConnectionError,
        RateLimitError,
        InternalServerError
    )),
    stop=stop_after_attempt(MAX_RETRIES),
    wait=wait_exponential(multiplier=1,min=2,max=10),
    before_sleep=before_sleep_log(logger,logging.WARNING),
    after=log_success,
    reraise=True
)
async def tenacity_response(model,messages,tools):
    response=await client.chat.completions.create(
        model=model,
        messages=messages,
        tools=tools,
        tool_choice="auto"
    )
    return response


memory=MemoryManager(file_path="memory.json",window_turns=4)

async def run():
    server_params=StdioServerParameters(
        command=sys.executable,
        args=[r"D:\个人文件\DreamCharser\Third_week\mcp_server\server.py"],
        env=None
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read,write) as session:
            await session.initialize()
            logger.info("成功与mcp握手")
            mcp_tools=await session.list_tools()
            logger.info(f"发现{len(mcp_tools.tools)}个工具，：{[t.name for t in mcp_tools.tools]}")
            openai_tools=[]
            for tool in mcp_tools.tools:
                openai_tools.append({
                    "type":"function",
                    "function":{
                        "name":tool.name,
                        "description":tool.description,
                        "parameters":tool.input_schema
                    }
                })
            system_prompt = """你是一个可以使用工具的 AI 助手。
请根据用户问题，自主决定是否调用工具。在决定调用工具之前，请先用一段文字简要说明你的思考过程（Thought）。

【重要交互规则】
1. 如果工具返回的结果中包含类似 `pending_confirmation`、`需要确认`、`awaiting approval` 等标识，说明该操作需要用户二次确认。
2. 此时，你【必须立刻停止】调用任何工具，并用简明扼要的自然语言向用户复述工具返回的提示信息，等待用户回复。
3. 不要在用户确认前自己去试探性调用，也不要自行编造额外的确认流程（如询问备份等），直接按工具的要求请用户确认即可。
4. 如果用户提供了绝对路径而工具报错，请尝试提取纯文件名再次调用，不要反复向用户索要相同的参数。"""
            while True:
                question=input("请输入您的问题")
                if question.lower() in ["exit","quit","q","退出"]:
                    print("对话结束")
                    break
                current_stepts=1


                current_turn=[{"role":"user","content":question}]
                turn_success=True

                while current_stepts<=MAX_STEPTS:
                    logger.info(f"----第{current_stepts}次调用模型----")
                    print(f"----第{current_stepts}次调用模型----")

                    message=memory.build_messages(system_prompt,current_turn)

                    try:
                        response=await tenacity_response(model=LLM_MODEL_NAME,messages=message,tools=openai_tools)
                        msg=response.choices[0].message
                        tokens_in=response.usage.prompt_tokens if response.usage else 0
                        tokens_out=response.usage.completion_tokens if response.usage else 0
                        cost_rmb=(tokens_in/1000000)*2+(tokens_out/1000000)*8
                        logger.info(
                            f"USAGE tokens_in={response.usage.prompt_tokens}  tokens_out={response.usage.completion_tokens}  step={current_stepts}  cost={cost_rmb:.6f}"
                        )
                    except Exception as e:
                        logger.error(f"API请求失败（不可恢复）：{e}")
                        turn_success=False
                        break


                    current_turn.append(msg.model_dump(exclude_none=True))#经过model_dump之后，msg是一个字典，里面包含了tool_calls，tool_calls里面有很多没必要的内容，所以需要稍微提取修饰一下tool_call


                    if not msg.tool_calls:
                        logger.info(f"最终回答\n{msg.content}")
                        print(f"最终回答：{msg.content}")
                        break
                    need_human_confirm=False
                    for tool_call in msg.tool_calls:
                        func_name=tool_call.function.name
                        try:
                            args=json.loads(tool_call.function.arguments)
                        except json.JSONDecodeError:
                            tool_output="Error:你生成的参数不是合法的JSON格式，请重新生成"


                            current_turn.append({
                                "role":"tool",
                                "tool_call_id":tool_call.id,
                                "content":tool_output
                            })
                            continue
                        logger.info(f"模型决定调用工具：{func_name}，其参数为{args}")
                        try:
                            result=await session.call_tool(func_name,arguments=args)
                            tool_output=result.content[0].text if result.content else ""
                            if getattr(result,"isError",False):
                                tool_output=f"工具执行报错{tool_output}"
                        except Exception as e:
                            tool_output=f"工具通信异常{str(e)}"
                        try:
                            out_json=json.loads(tool_output)
                            if out_json.get("status")=="pending_confirmation":
                                print(f"{out_json.get('message')}")
                                need_human_confirm=True
                        except:
                            pass
                        logger.info(f"工具返回结果：{tool_output}")
                        current_turn.append({
                            "role":"tool",
                            "tool_call_id":tool_call.id,
                            "content":tool_output
                        })
                        if need_human_confirm:
                            break
                    if need_human_confirm:
                        break
                    current_stepts+=1


                if turn_success:
                    memory.turns.append(current_turn)
                    memory.save()
                    logger.info(f"本轮对话已经写入短期记忆")


                await memory.compress_memory(client=client,model_name=LLM_MODEL_NAME)


if __name__=="__main__":
    logging.basicConfig(
        filename=r"D:\个人文件\DreamCharser\Third_week\logs\week3.log",
        level=logging.INFO,
        format="%(asctime)s -%(name)s -%(levelname)s -%(message)s"
    )
    asyncio.run(run())
                