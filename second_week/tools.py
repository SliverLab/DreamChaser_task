from __future__ import annotations
import re
import serpapi
from scheme import WeatherAnswer,WeatherArgs,SearchAnswer,SearchArgs
class ToolError(Exception):
    pass
_weather_dict:dict[str,dict]={
    "上海": {"temp_c": 24.5, "condition": "多云，东南风 3 级，湿度 68%"},
    "北京": {"temp_c": 18.0, "condition": "晴，空气干燥"},
    "深圳": {"temp_c": 29.0, "condition": "阵雨，湿度 85%"},
    "湘潭": {"temp_c": 21.0, "condition": "阴转小雨"},
    "弥勒": {"temp_c": 23.0, "condition": "晴间多云，紫外线较强"},
}
_MAX_EXPRESION_LEN=200

def get_weather(args:WeatherArgs)->dict:
    data=_weather_dict.get(args.city)
    if data is None:
        raise ToolError(f"城市未收录：{args.city},当前可用城市：{','.join(_weather_dict)}")
    return WeatherAnswer(
        city=args.city,
        temp=data.get("temp_c"),
        condition=data.get("condition")
    ).model_dump()


import os
from dotenv import load_dotenv
dotenv_path=r"D:\个人文件\DreamCharser\final_version\.env"
load_dotenv(dotenv_path=dotenv_path)
def _truncate(text: str, max_len: int = 200) -> str:
    """截断文本到指定长度，避免信息过载"""
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."

def search(query: str) -> str:
    try:
        api_key = os.getenv("SERPAPI_API_KEY")
        if not api_key:
            return "错误: SERPAPI_API_KEY 未在 .env 文件中配置。"
        client=serpapi.Client(api_key=api_key)
        results=client.search({
            "engine":"google",
            "q":query
        }
        )

        # 优先返回直接答案（答案框、知识图谱等），统一截断
        if "answer_box_list" in results and results["answer_box_list"]:
            answer_text = "\n".join(
                [item.get("answer", "") for item in results["answer_box_list"] if item.get("answer")]
            )
            if answer_text:
                return _truncate(answer_text, max_len=300)

        if "answer_box" in results and results["answer_box"].get("answer"):
            return _truncate(results["answer_box"]["answer"], max_len=300)

        if "knowledge_graph" in results and results["knowledge_graph"].get("description"):
            return _truncate(results["knowledge_graph"]["description"], max_len=300)

        # 没有直接答案时，返回前两个有机结果，每个结果截断标题+摘要
        if "organic_results" in results and results["organic_results"]:
            snippets = []
            for i, res in enumerate(results["organic_results"][:2]):
                title = res.get("title", "")
                snippet = res.get("snippet", "")
                # 每个结果限制总长度 200 字符
                combined = f"[{i+1}] {title}\n{snippet}"
                snippets.append(_truncate(combined, max_len=200))
            # 最终返回不超过 500 字符
            return "\n\n".join(snippets)[:500]

        return f"对不起，没有找到关于 '{query}' 的信息。"

    except Exception as e:
        return f"搜索时发生错误: {e}"

def search_tool(args:SearchArgs)->dict:
    text=search(args.query)
    if text.startswith("搜索时发生错误"):
        raise ToolError(text)
    return SearchAnswer(query=args.query,result=text).model_dump()


TOOLS:list[dict]=[
    {
        "type":"function",
        "function":{
            "name":"get_weather",
            "description":"查询指定城市的天气",
            "parameters":WeatherArgs.model_json_schema(),
        },
    },
    {
        "type":"function",
        "function":{
            "name":"search",
            "description":"用 Google 搜索关键词，返回直接答案或网页摘要。适合查实时信息、事实、人物、地点。",
            "parameters":SearchArgs.model_json_schema(),
        }
    }
]

TOOL_REGISTRY: dict[str, tuple] = {
    "get_weather": (get_weather, WeatherArgs),
    "search":(search_tool,SearchArgs),
}