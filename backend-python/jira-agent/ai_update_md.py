import os
import json
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))  # 可换成 DeepSeek / 硅基流动

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
Return ONLY a JSON list of file names, e.g.:

["api.md", "README.md"]
"""

    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
    )

    content = resp.choices[0].message.content

    try:
        selected = json.loads(content)
    except Exception:
        selected = []  # 如果模型没按格式来，就不更新任何文档

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

    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
    )

    return resp.choices[0].message.content


def ai_update_md_from_ticket(ticket_text):
    docs = read_docs()

    # 1. AI 判断哪些文档需要更新
    target_md_files = ai_select_md_files(ticket_text, docs)

    if not target_md_files:
        print("ℹ No documentation needs updating.")
        return

    # 2. AI 更新每个文档
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


if __name__ == "__main__":
    example_ticket = """
    Add a new field 'age' to the User model and update API documentation.
    Also update README to reflect new API response format.
    """
    ai_update_md_from_ticket(example_ticket)
