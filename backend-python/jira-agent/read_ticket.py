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
        return

    url = f"https://{domain}/rest/api/3/issue/{issue_key}"

    auth = base64.b64encode(f"{email}:{token}".encode()).decode()

    headers = {
        "Authorization": f"Basic {auth}",
        "Accept": "application/json"
    }

    response = requests.get(url, headers=headers)
    print(json.dumps(response.json(), indent=2))

if __name__ == "__main__":
    get_jira_issue("SCRUM-6")
