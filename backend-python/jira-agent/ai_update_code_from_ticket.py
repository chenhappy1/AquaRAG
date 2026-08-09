import os
import json
from google import genai
from google.genai import types

# 1. 初始化官方 Gemini 客户端
# 默认会自动读取环境变量中的 GEMINI_API_KEY
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

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
            for f in filenames:
                if f.endswith((".py", ".java", ".ts", ".js")):
                    files.append(os.path.join(dirpath, f))
    return files


def ai_select_files(ticket_text, docs, files):
    prompt = f"""
You are an expert software engineer.

Jira Ticket:
{ticket_text}

Project Documentation (.md):
{json.dumps(docs, indent=2)}

Project Code Files:
{files}

Task:
Based on the ticket and documentation, decide which code files are relevant
and should be modified.

Return ONLY a JSON list of file paths.
"""

    # 2. 使用 interactions.create 调用 Gemini 3 Flash Preview
    # 使用 response_mime_type 强制输出合法 JSON
    resp = client.interactions.create(
        model='models/gemini-3-flash-preview',
        input=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            top_p=0.95,
            thinking_config=types.ThinkingConfig(thinking_budget=2048)  # 开启高思考链级别
        )
    )

    # 3. 提取最终生成的文本内容
    content = resp.steps[-1].text
    
    try:
        selected = json.loads(content)
    except Exception:
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

    # 4. 调用模型修改文件
    resp = client.interactions.create(
        model='models/gemini-3-flash-preview',
        input=prompt,
        config=types.GenerateContentConfig(
            top_p=0.95,
            thinking_config=types.ThinkingConfig(thinking_budget=2048)
        )
    )

    new_code = resp.steps[-1].text

    # 去除可能包含的 markdown 代码块标记
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

