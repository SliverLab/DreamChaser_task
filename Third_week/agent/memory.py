import json
import os
import logging
from pathlib import Path
from datetime import datetime
logger=logging.getLogger(__name__)
class MemoryManager:
    def __init__(self,file_path="memory.json",window_turns=2,md_path="MEMORY.md"):
        self.file_path=Path(file_path)
        self.window_turns=window_turns

        self.md_path=Path(md_path)
        self.long_term_memory=""
        if self.md_path.exists():
            try:
                with open(self.md_path,"r",encoding="utf-8")as f:
                    self.long_term_memory=f.read().strip()
                logger.info(f"长期记忆加载成功，共有{len(self.long_term_memory)}个字符")
            except Exception as e:
                logger.error(f"长期记忆加载失败:{e}")
                self.long_term_memory=""
        
        if self.file_path.exists():
            try:
                with open(self.file_path,"r",encoding="utf-8")as f:
                    content=json.load(f)
                    self.summary=content.get("summary","")
                    self.turns=content.get("turns",[])
            except Exception as e:
                logger.error(f"加载记忆失败，将记忆初始化为空白：{e}")
                self.summary=""
                self.turns=[]
        else:
            self.summary=""
            self.turns=[]
    def save(self):
        self.file_path.parent.mkdir(parents=True,exist_ok=True)
        with open(self.file_path,"w",encoding="utf-8")as f:
            json.dump(
                {
                    "summary":self.summary,
                    "turns":self.turns
                },f,ensure_ascii=False,
                indent=2
            )
        logger.info(f"已经成功将短期记忆保存至{self.file_path}")

    def build_messages(self,system_prompt,current_turn):
        if self.long_term_memory:
            system_prompt+=f"\n\n长期记忆:{self.long_term_memory}"
        messages=[{"role":"system","content":system_prompt}]
        if self.summary:
            messages.append(
                {
                    "role":"system",
                    "content":self.summary,
                }
            )
        recent_turns=self.turns[-self.window_turns:]
        for turn in recent_turns:
            messages.extend(turn)
        messages.extend(current_turn)
        return messages


    def estimate_token(self,safety_margin=1.2):
        total=0
        for turn in self.turns:
            for msg in turn:
                content=msg.get("content","") or ""
                if not content:
                    continue
                chinese_chars=sum(1 for c in content if '\u4e00' <= c <= '\u9fff')
                other_chars=len(content)-chinese_chars
                total+=int((chinese_chars*0.6+other_chars*0.3)*safety_margin)
        logger.info(f"该次发送的message的大致token估计为{total}")
        return total



    async def compress_memory(self,client,model_name,token_budget=3000):
        if len(self.turns)<=self.window_turns and self.estimate_token()<=token_budget:
            return 
        old_turns=self.turns[:-self.window_turns]
        text_lines=[]
        for turn in old_turns:
            for msg in turn:
                role=msg["role"]
                if role=="user":
                    text_lines.append(f'用户：{msg.get("content","")}')
                elif role=="assistant":
                    content=msg.get("content","")or ""
                    if content:
                        text_lines.append(f"AI:{content}")
                    if msg.get("tool_calls"):
                        for tc in msg["tool_calls"]:
                            func_name=tc["function"]["name"]
                            args=tc["function"]["arguments"]
                            text_lines.append(f"AI决定调用工具：{func_name}，参数：{args}")
                elif role=="tool":
                    content=msg.get("content","")or ""
                    if len(content)>100:
                        content=content[:100]+"..."
                    text_lines.append(f"工具执行结果：{content}")
        old_text="\n".join(text_lines)
        prompt= f"""请把以下历史对话压缩成简短的摘要，保留核心事实、用户的偏好以及达成的一致结论。不需要保留工具的具体返回细节。
【之前的摘要】：{self.summary if self.summary else "无"}

【需要合并的新对话】：
{old_text}

请直接输出合并后的新摘要，不要包含“好的”、“摘要如下”等废话。"""
        messages=[
            {"role":"user","content":prompt}
        ]
        try:
            response=await client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=0.3
            )
            content=response.choices[0].message.content.strip() if response.choices[0].message.content.strip() else ""
            self.summary=content
            logger.info(f"历史记忆成功压缩，新摘要：{self.summary}")
        except Exception as e:
            logger.error(f"历史记忆压缩失败，错误原因:{str(e)}")
            return
        self.turns=self.turns[-self.window_turns:]
        self.save()



    def save_long_term_memory(self,new_memory_lines):

        self.long_term_memory+=f"- {new_memory_lines}\n"
        self.md_path.parent.mkdir(parents=True,exist_ok=True)
        with open(self.md_path,"w",encoding="utf-8")as f:
            f.write(self.long_term_memory)
        logger.info("成功在MEMORY.md中追加一条长期记忆")

    async def extract_long_term_memory(self,client,model_name,current_turn):
        turn_text=[]
        for msg in current_turn:
            role=msg["role"]
            content=msg.get("content","") or ""
            if role=="user":
                turn_text.append(f'用户：{content}')
            elif role=="assistant":
                if content:
                    turn_text.append(f'AI:{content}')
                if msg.get("tool_calls"):
                    for tc in msg.get("tool_calls"):
                        fun_name=tc["function"]["name"]
                        args=tc["function"]["arguments"]
                        turn_text.append(f"AI决定调用工具:{fun_name}[{args}]")
            elif role=="tool":
                turn_text.append(f'工具执行结果:{content}')
        text_data="\n".join(turn_text)
        prompt=f"""你是一个信息提取助手。请分析以下对话，提取值得长期记住的用户个人信息（如：姓名、偏好、项目代号、重要约定等）。
【已有的长期记忆】（请不要重复提取这里已经有的信息）：
{self.long_term_memory if self.long_term_memory else "无"}

【当前这轮对话】：
{text_data}

【指令】：
- 如果有值得长期记住的**新**信息，请用一句话概括核心事实（不要带日期）。
- 如果没有新信息，或者已有记忆里已经包含了，请直接输出“无”。
- 绝对不要输出任何多余的解释。"""
        messages=[{"role":"user","content":prompt}]
        try:
            response=await client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=0.3
            )
            content=response.choices[0].message.content.strip() if response.choices[0].message.content.strip() else ""
            if content and "无" not in content[:3]:
                today=datetime.now().strftime("%Y-%m-%d")
                self.save_long_term_memory(f"{today} {content}")
        except Exception as e:
            logger.error(f"模型生成摘要错误：{e}")
                


#整个记忆系统的底座：
#  {
#    "summary": "用户之前要求把 test 文件加密。",
#    "turns": [
#      [
#        {"role": "user", "content": "帮我加密test"},
#        {"role": "assistant", "content": "请确认..."},
#        {"role": "tool", "content": "加密成功"},
#        {"role": "assistant", "content": "已加密完毕"}
#      ],
#      [
#        {"role": "user", "content": "刚才那个test在哪里？"},
#        {"role": "assistant", "content": "在沙箱目录下。"}
#         {
#              "role": "assistant",
#              "content": "好的，我来搜索一下。",
#              "tool_calls": [            
#                  {
#                      "id": "call_123",
#                      "type": "function",
#                      "function": {"name": "search", "arguments": "{\"query\": \"天气\"}"}
#                  }
#              ]
#         }
#      ]
#    ]
#  }



                            # current_turn.append({
                            #     "role":"tool",
                            #     "tool_call_id":tool_call.id,
                            #     "content":tool_output
                            # })