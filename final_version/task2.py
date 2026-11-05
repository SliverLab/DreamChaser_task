from openai import OpenAI
import os
from dotenv import load_dotenv
import logging
import time
logger=logging.getLogger(__name__)
load_dotenv()
MAX_RETRIES=int(os.getenv("MAX_RETRIES","3"))
LLM_API_KEY=os.getenv("LLM_API_KEY")
LLM_BASE_URL=os.getenv("LLM_BASE_URL")
LLM_MODEL_NAME=os.getenv("LLM_MODEL_NAME")
if not all  ([LLM_API_KEY,LLM_BASE_URL,LLM_MODEL_NAME]):
    raise ValueError("请确保LLM_API_KEY，LLM_BASE_URL，LLM_MODEL_NAME存在")
client=OpenAI(
    api_key=LLM_API_KEY,
    base_url=LLM_BASE_URL,
    max_retries=0
)
def run(question:str):
    prompt="你是一个博学多知的学者，用户和你聊天请用古诗回答"
    messages=[
        {"role":"system","content":prompt},
        {"role":"user","content":question}
    ]
    for i in range(1,MAX_RETRIES+1):
        try:
            logger.info(f"开始请求大模型（第{i}/{MAX_RETRIES}次）")
            response=client.chat.completions.create(
                model=LLM_MODEL_NAME,
                messages=messages,
                temperature=1,
                stream=True,
            )
            for chunk in response:
                if not chunk.choices:
                    continue
                content=chunk.choices[0].delta.content if chunk.choices[0].delta.content else None
                if content:
                    print(content,end="",flush=True)
            logger.info("模型回复完成")
            return
        except Exception as e:
            logger.exception(f"调用模型发生异常（第{i}/{MAX_RETRIES}）次:{e}")
            if i>=MAX_RETRIES:
                raise
            wait=2**(i-1)
            logger.info(f"等待{wait}秒后重试")
            time.sleep(wait)
if __name__ =="__main__":
    logging.basicConfig(
        filename="run.log",
        level=logging.INFO,
        format="%(asctime)s -%(name)s -%(levelname)s -%(message)s"
    )
    print("这是一位博学多知的老师，和他谈话它会用古诗和您交谈")
    question=input("请输入您的第一句话：")
    run(question)