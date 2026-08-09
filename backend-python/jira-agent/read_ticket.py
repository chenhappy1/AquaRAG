import os
import requests
import base64
import json

def get_jira_issue(issue_key):
    email = os.getenv("JIRA_EMAIL")
    token = os.getenv("JIRA_TOKEN")
    domain = os.getenv("JIRA_DOMAIN")

    if not email or not token or not domain:
        print("❌ Missing environment variables. Please set JIRA_EMAIL, JIRA_TOKEN, JIRA_DOMAIN.")
        return None

    url = f"https://{domain}/rest/api/3/issue/{issue_key}"

    auth = base64.b64encode(f"{email}:{token}".encode()).decode()

    headers = {
        "Authorization": f"Basic {auth}",
        "Accept": "application/json"
    }

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print("❌ Jira API 请求失败:", response.status_code, response.text)
        return None

    data = response.json()
    print(json.dumps(data, indent=2))  # 你想打印可以保留
    return data

