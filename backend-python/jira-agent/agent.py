from read_ticket import get_jira_issue
from auto_branch import create_branch
from auto_commit import auto_commit
from auto_test import run_tests
from update_ticket import update_jira_status

def auto_pipeline(issue_key):
    print("📌 Step 1: Read Jira Ticket")
    ticket = get_jira_issue(issue_key)

    print("📌 Step 2: Create Git Branch")
    create_branch(issue_key)

    print("📌 Step 3: Auto Commit Code")
    auto_commit(issue_key)

    print("📌 Step 4: Run Tests")
    success = run_tests()

    if success:
        print("📌 Step 5: Update Jira → Done")
        update_jira_status(issue_key, "31")
    else:
        print("❌ Tests failed, Jira will not be updated")

if __name__ == "__main__":
    auto_pipeline("SCRUM-6")
