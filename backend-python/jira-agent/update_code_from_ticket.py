import os
import json
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))  # 或者换成 DeepSeek / 硅基流动

DOCS_DIR = "docs"
CODE_ROOTS = ["backend", "backend-python", "frontend"]


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

Return ONLY a JSON list of file paths, e.g.:
["backend/src/main/java/com/example/backend/rag/RagController.java",
 "frontend/src/app/rag/rag.service.ts"]
"""

    resp = client.chat.completions.create(
        model="gpt-4o",  # 或者 DeepSeek-R1 对应的模型名
        messages=[{"role": "user", "content": prompt}],
    )

    content = resp.choices[0].message.content
    try:
        selected = json.loads(content)
    except Exception:
        # 如果模型没按格式来，就简单兜底：全量返回
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
Return ONLY the FULL updated code for this file, no explanations.
"""

    resp = client.chat.completions.create(
        model="gpt-4o",  # 或者 DeepSeek-R1
        messages=[{"role": "user", "content": prompt}],
    )

    new_code = resp.choices[0].message.content

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_code)

    print(f"✅ Updated code file: {file_path}")


def ai_update_code_from_ticket(ticket_text: str):
    # 1. 读 MD 文档，建立项目理解
    docs = read_docs()

    # 2. 扫描代码文件列表
    files = scan_code_files()

    # 3. 让 AI 选出需要修改的文件
    target_files = ai_select_files(ticket_text, docs, files)

    # 4. 逐个文件让 AI 生成修改后的代码
    for path in target_files:
        if os.path.exists(path):
            ai_update_single_file(ticket_text, docs, path)
        else:
            print(f"⚠ File not found (skipped): {path}")


if __name__ == "__main__":
    # 示例：你可以从 Jira 读出 summary + description 传进来
    example_ticket = """
    Add a new field 'age' to the User model and return it in the user API response.
    Also make sure the frontend displays the age field in the chat user info.
    """
    ai_update_code_from_ticket(example_ticket)
