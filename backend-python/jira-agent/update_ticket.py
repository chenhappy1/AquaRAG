import requests
import base64
import json
import os

def update_jira_status(issue_key, status_id):
    email = os.getenv("JIRA_EMAIL")
    token = os.getenv("JIRA_TOKEN")
    domain = os.getenv("JIRA_DOMAIN")

    auth = base64.b64encode(f"{email}:{token}".encode()).decode()

    url = f"https://{domain}/rest/api/3/issue/{issue_key}/transitions"

    payload = {
        "transition": {
            "id": status_id   # Done 的 ID
        }
    }

    headers = {
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/json"
    }

    response = requests.post(url, headers=headers, data=json.dumps(payload))

    print(response.status_code, response.text)

if __name__ == "__main__":
    update_jira_status("SCRUM-6", "31")  # 31 = Done（你的 Jira 可能不同）
