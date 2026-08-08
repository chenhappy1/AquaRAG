import requests
import base64
import json
import os

# 从 config.json 读取配置（推荐做法）
def load_config():
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)

def get_jira_issue(issue_key):
    config = load_config()

    email = config["email"]
    token = config["token"]
    domain = config["domain"]

    url = f"https://{domain}/rest/api/3/issue/{issue_key}"

    # Basic Auth
    auth = base64.b64encode(f"{email}:{token}".encode()).decode()

    headers = {
        "Authorization": f"Basic {auth}",
        "Accept": "application/json"
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        print("\n✅ Successfully fetched Jira Ticket:")
        print(json.dumps(response.json(), indent=2))
        return response.json()
    else:
        print(f"\n❌ Error: {response.status_code}")
        print(response.text)
        return None

if __name__ == "__main__":
    # 你可以改成任何 Jira Issue Key
    get_jira_issue("SCRUM-6")
