import os
import json
from google import genai
from google.genai import types
# 使用 DeepSeek API（正确写法）
client = genai.Client()

DOCS_DIR = "docs"


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


def ai_select_md_files(ticket_text, docs):
    prompt = f"""
You are an expert software engineer and technical writer.

Jira Ticket:
{ticket_text}

Project Documentation (.md files):
{json.dumps(docs, indent=2)}

Task:
Determine which documentation files need to be updated based on the Jira ticket.
Return ONLY a JSON list of file names.
"""


    resp = client.models.generate_content(
        model='gemini-3-flash-preview',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            top_p=0.95,
            thinking_config=types.ThinkingConfig(thinking_budget=2048)  # 开启高思考链级别
        )
    )

    content = resp.text.strip() if resp.text else ""

    try:
        selected = json.loads(content)
    except Exception:
        selected = []

    return selected


def ai_update_single_md(ticket_text, md_name, old_md):
    prompt = f"""
You are an expert technical writer.

Jira Ticket:
{ticket_text}

Current Documentation File ({md_name}):
{old_md}

Task:
Update ONLY this documentation file according to the Jira ticket.
Keep the writing style consistent.
Return ONLY the updated markdown content.
"""

    resp = client.models.generate_content(
        model='gemini-3-flash-preview',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            top_p=0.95,
            thinking_config=types.ThinkingConfig(thinking_budget=2048)  # 开启高思考链级别
        )
    )

    content = resp.text.strip() if resp.text else ""
    return content

def ai_update_md_from_ticket(ticket_text):
    docs = read_docs()

    target_md_files = ai_select_md_files(ticket_text, docs)

    if not target_md_files:
        print("ℹ No documentation needs updating.")
        return

    for md_name in target_md_files:
        path = os.path.join(DOCS_DIR, md_name)

        if md_name not in docs:
            print(f"⚠ File not found: {md_name}")
            continue

        old_md = docs[md_name]
        new_md = ai_update_single_md(ticket_text, md_name, old_md)

        with open(path, "w", encoding="utf-8") as f:
            f.write(new_md)

        print(f"📘 Updated documentation: {md_name}")

