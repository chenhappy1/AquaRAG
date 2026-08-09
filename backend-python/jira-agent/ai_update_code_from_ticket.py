import os
import json
import time  # 引入时间库用于限流等待
from google import genai
from google.genai import types

# 1. 初始化官方 Gemini 客户端
# 默认会自动读取您在系统环境变量中配置的 GEMINI_API_KEY
client = genai.Client()

DOCS_DIR = r"D:\AquaRAG\docs"
CODE_ROOTS = [
    r"D:\AquaRAG\backend",
    r"D:\AquaRAG\backend-python",
    r"D:\AquaRAG\frontend"
]


def read_docs():
    docs = {}
    if not os.path.isdir(DOCS_DIR):
        return docs

    for f in os.listdir(DOCS_DIR):
        if f.endswith(".md"):
            path = os.path.join(DOCS_DIR, f)
            with open(path, "r", encoding="utf-8") as file:
                docs[f] = file.read()
    return docs


def scan_code_files():
    files = []
    for root in CODE_ROOTS:
        if not os.path.isdir(root):
            continue
        for dirpath, _, filenames in os.walk(root):
            # 💡 优化 1：过滤掉 node_modules 等超大依赖文件夹，防止 Token 瞬间爆炸
            if any(ignored in dirpath for ignored in ["node_modules", ".git", "venv", "__pycache__", "dist", "build"]):
                continue
                
            for f in filenames:
                if f.endswith((".py", ".java", ".ts", ".js", ".html", ".css", ".json", ".yaml", ".yml")):
                    files.append(os.path.join(dirpath, f))
    return files


def ai_select_files(ticket_text, docs, files):   
    # 💡 优化 2：只把相对路径传给 AI，大大压缩 prompt 长度，节省输入 Token
    short_files = []
    for f in files:
        for root in CODE_ROOTS:
            if f.startswith(root):
                short_files.append(os.path.relpath(f, root))
                break

    prompt = f"""
You are an expert software engineer.

Jira Ticket:
{ticket_text}

Project Documentation (.md):
{json.dumps(docs, indent=2)}

Project Code Files (relative paths):
{short_files}

Task:
Based on the ticket and documentation, decide which code files are relevant
and should be modified.

Return ONLY a JSON list of relative file paths from the provided list. Do not wrap it in markdown block syntax.
"""

    # 💡 优化 3：限流控制，发送请求前强制休眠 5 秒，防 429 报错
    print("\n⏳ 正在等待配额刷新并调用 AI 选择文件...")
    time.sleep(5)

    # 🛠️ 【核心修改】：改用官方最标准的 generate_content 方法，彻底解决属性错误，并优雅地传参
    resp = client.models.generate_content(
        model='gemini-3-flash-preview',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            top_p=0.95,
            thinking_config=types.ThinkingConfig(thinking_budget=2048)  # 开启高思考链级别
        )
    )

    # 在 generate_content 返回的对象中，直接使用 .text 是百分百支持且最安全的
    content = resp.text.strip() if resp.text else ""
    
    if content.startswith("```"):
        lines = content.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines[-1].startswith("```"):
            lines = lines[:-1]
        content = "\n".join(lines).strip()
    
    try:
        selected_rel_paths = json.loads(content)
        # 将 AI 返回的相对路径还原为系统中的绝对路径
        selected = []
        for rel in selected_rel_paths:
            for root in CODE_ROOTS:
                full_path = os.path.join(root, rel)
                if os.path.exists(full_path):
                    selected.append(full_path)
                    break
    except Exception:
        print("⚠ 无法解析 AI 返回的 JSON 列表，使用保底全量文件列表。")
        selected = files

    return selected


def ai_update_single_file(ticket_text, docs, file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        old_code = f.read()

    prompt = f"""
You are an expert software engineer.

Jira Ticket:
{ticket_text}

Relevant Project Documentation:
{json.dumps(docs, indent=2)}

File Path:
{file_path}

Current Code:
{old_code}

Task:
Modify ONLY this file according to the Jira ticket and project context.
Keep style consistent with existing code.
Return ONLY the FULL updated code for this file. Do not include markdown code block syntax (like ```python).
"""

    # 💡 优化 4：多文件循环修改时，每修改完一个文件强制休息 6 秒
    print(f"\n⏳ 正在等待配额刷新并开始修改文件: {file_path} ...")
    time.sleep(6)

    # 🛠️ 【核心修改】：同步改为最可靠的 generate_content 接口
    resp = client.models.generate_content(
        model='gemini-3-flash-preview',
        contents=prompt,
        config=types.GenerateContentConfig(
            top_p=0.95,
            thinking_config=types.ThinkingConfig(thinking_budget=2048)
        )
    )

    new_code = resp.text if resp.text else ""

    if new_code.strip().startswith("```"):
        lines = new_code.strip().splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines[-1].startswith("```"):
            lines = lines[:-1]
        new_code = "\n".join(lines)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_code)

    print(f"✅ Updated code file: {file_path}")


def ai_update_code_from_ticket(ticket_text: str):
    docs = read_docs()
    files = scan_code_files()
    target_files = ai_select_files(ticket_text, docs, files)

    for path in target_files:
        if os.path.exists(path):
            ai_update_single_file(ticket_text, docs, path)
        else:
            print(f"⚠ File not found (skipped): {path}")


if __name__ == "__main__":
    example_ticket = """
    Add a new field 'age' to the User model and return it in the user API response.
    Also make sure the frontend displays the age field in the chat user info.
    """
    ai_update_code_from_ticket(example_ticket)
