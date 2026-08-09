import json
import os
from read_ticket import get_jira_issue

def update_code_from_ticket(issue_key):
    ticket = get_jira_issue(issue_key)

    summary = ticket["fields"]["summary"]
    description = ticket["fields"]["description"]

    print("📌 Jira Summary:", summary)
    print("📌 Jira Description:", description)

    # 这里你可以用 AI 自动生成代码修改
    # 或者根据规则自动修改文件

    # 示例：如果 Ticket 要求添加一个 API
    if "add api" in description.lower():
        with open("backend/api/new_api.py", "w") as f:
            f.write("def new_api():\n    return 'new api created automatically'\n")

        print("✅ Code updated based on ticket")

    return True

if __name__ == "__main__":
    update_code_from_ticket("SCRUM-6")
