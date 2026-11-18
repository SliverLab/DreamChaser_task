from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
import serpapi
from typing import Optional
from pathlib import Path
from cryptography.fernet import Fernet
import requests
import json
import os
from dotenv import load_dotenv
load_dotenv()
mcp=MCPServer("My-Agent-Server")
def _truncate(text: str, max_len: int = 200) -> str:
    """截断文本到指定长度，避免信息过载"""
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."
@mcp.tool()
def search(query:str)->str:
    """该工具用 Google 搜索关键词，
    返回直接答案或网页摘要。适合查实时信息、事实、人物、地点。"""
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





BASE_DIR=Path(__file__).resolve().parent
SANDBOX_DIR=(BASE_DIR/"sandbox").resolve()
SANDBOX_DIR.mkdir(exist_ok=True,parents=True)#parents=True是自动创建所有上级缺失的父目录，exist_ok=True,存在时不报错
key=os.getenv("SANDBOX_KEY")
cipher=Fernet(key.encode())
def _get_safe_path(filename:str)->Path:
    target_path=(SANDBOX_DIR/filename).resolve()
    if not target_path.is_relative_to(SANDBOX_DIR):
        raise ToolError(f"安全拦截，不允许访问沙箱外的文件({filename})")
    return target_path
@mcp.tool()
def encrypt_file(filename:str,confirm:bool=False)->dict:
    """加密沙箱内的指定文件。这是一个破坏性操作，需要二次确认。"""
    if not confirm:
        return {
            "status": "pending_confirmation", 
            "message": f"⚠️ 即将加密文件 [{filename}]，加密后原文件内容将被覆盖。请带上 confirm=true 再次调用以确认。"           
        }
    file_path=_get_safe_path(filename)
    if not file_path.exists():
        raise ToolError(f"{filename}文件不存在")
    original_data=file_path.read_bytes()
    encrypted_data=cipher.encrypt(original_data)
    file_path.write_bytes(encrypted_data)
    return {"status": "success", "message": f"文件 {filename} 已成功加密。"}

@mcp.tool()
def decrypt_file(filename:str)->dict:
    """解密沙箱内的文件
    Args:
        file_name:需要解密的文件路径
    """
    file_path=_get_safe_path(filename)
    if not file_path.exists():
        raise ToolError(f"{filename}不存在，请检查文件路径是否对")
    decrypted_data=cipher.decrypt(file_path.read_bytes())
    file_path.write_bytes(decrypted_data)
    return{"status":"success","message":f"{filename}中的文件已经重新解密，并且实现覆盖"}


@mcp.tool()
def github_repo_info(owner:str,repo:str)->dict:
    """获取指定 GitHub 仓库的 Star 数量和最后推送时间。
    
    Args:
        owner: 仓库所有者，例如 "openai"
        repo: 仓库名称，例如 "openai-python"
    """
    url=f"https://api.github.com/repos/{owner}/{repo}"
    try:
        response=requests.get(url,timeout=5)
        response.raise_for_status()
        data=response.json()
        stars=data["stargazers_count"]
        pushed_time=data["pushed_at"]
        return{
            "owner":owner,
            "repo":repo,
            "stars":data["stargazers_count"],
            "pushed_at":data["pushed_at"],
            "success":True
        }
    except requests.exceptions.Timeout:
        return {"success":False,"error":"请求github超时，请稍后重试"}
    except json.JSONDecodeError:
        return {"success":False,"error":"返回的内容不是合法json"}
    except KeyError:
        return {"success":False,"error":"返回的数据里面没有stargazers_count/pushed_time字段"}
    except requests.exceptions.RequestException as e:
        return {"success":False,"error":f"报错信息:{e}"}
if __name__=="__main__":
    mcp.run(transport="stdio")