import json
import os
import logging
logger=logging.getLogger(__name__)
class MemoryManager:
    def __init__(self,file_path="memory.json",window_turns=4):
        self.file_path=file_path
        self.window_turns=window_turns
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path,"r",encoding="utf-8")as f:
                    content=json.load(f)
                    self.summary=content.get["summary",""]
                    self.turns=content.get["turns",[]]
            except Exception as e:
                logger.error(f"加载记忆失败，将记忆初始化为空白：{e}")
                self.summary=""
                self.turns=[]
        else:
            self.summary=""
            self.turns=[]
    def save(self):
        with open(self.file_path,"w",encoding="utf-8")as f:
            json.dump(
                {
                    "summary":self.summary,
                    "turns":self.turns
                },f,ensure_ascii=False
            )
    def build_messages(self,system_prompt,current_turn):
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


                

