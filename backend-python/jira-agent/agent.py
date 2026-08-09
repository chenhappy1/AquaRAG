from read_ticket import get_jira_issue
from ai_update_code import ai_update_code_from_ticket
from ai_update_md import ai_update_md_from_ticket
from auto_branch import create_branch
from auto_commit import auto_commit
from auto_test import run_tests
from update_ticket import update_jira_status

def auto_pipeline(issue_key):
    print("📌 Step 1: Read Jira Ticket")
    ticket = get_jira_issue(issue_key)

    summary = ticket["fields"]["summary"]
    description = ticket["fields"]["description"]
    ticket_text = summary + "\n" + description

    print("📌 Step 2: AI Update Code")
    ai_update_code_from_ticket(ticket_text)

    print("📌 Step 3: AI Update Documentation (.md)")
    ai_update_md_from_ticket(ticket_text)

    print("📌 Step 4: Create Git Branch")
    create_branch(issue_key)

    print("📌 Step 5: Auto Commit Code + Docs")
    auto_commit(issue_key)

    print("📌 Step 6: Run Tests")
    success = run_tests()

    if success:
        print("📌 Step 7: Update Jira → Done")
        update_jira_status(issue_key, "31")
    else:
        print("❌ Tests failed, Jira will not be updated")

if __name__ == "__main__":
    auto_pipeline("SCRUM-6")
