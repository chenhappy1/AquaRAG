import sys
import subprocess
from read_ticket import get_jira_issue
from ai_update_code_from_ticket import ai_update_code_from_ticket
from ai_update_md import ai_update_md_from_ticket
from auto_branch import create_branch
from auto_commit import auto_commit
from auto_test import run_tests
from update_ticket import update_jira_status

def agent(issue_key):
    print(f"🚀 开始执行 Agent 自动化流水线: {issue_key}")
    
    print("\n📌 Step 1: Read Jira Ticket")
    ticket = get_jira_issue(issue_key)
    summary = ticket["fields"]["summary"]
    description = ticket["fields"]["description"] or ""
    ticket_text = summary + "\n" + description

    # 💡 优化：应该先创建或切换到新特性分支，再让 AI 修改文件，防止污染主分支
    print(f"\n📌 Step 2: Create Git Branch for {issue_key}")
    try:
        create_branch(issue_key)
    except Exception as e:
        print(f"⚠ 创建分支失败或分支已存在: {e}，继续执行...")

    print("\n📌 Step 3: AI Update Code & Documentation (.md)")
    ai_update_code_from_ticket(ticket_text)
    ai_update_md_from_ticket(ticket_text)

    # 🛠️ 核心引入：Compare Difference (差异对比)
    print("\n📌 Step 4: Compare Difference (Git Diff)")
    try:
        # 在控制台高亮打印出 AI 所有的修改细节
        diff_output = subprocess.check_output(["git", "diff"], text=True)
        if diff_output.strip():
            print("=" * 50)
            print("🔍 AI 修改差异报告预览：")
            print(diff_output)
            print("=" * 50)
        else:
            print("ℹ 无任何文件变更，AI 可能未匹配到需修改的代码。")
    except Exception as e:
        print(f"⚠ 无法获取 Git Diff 差异信息: {e}")

    print("\n📌 Step 5: Run Tests")
    # 在 Commit 之前先跑测试，如果测试不通过，连本地 Commit 都不应该产生
    success = run_tests()

    if success:
        print("\n📌 Step 6: Auto Commit Code + Docs")
        auto_commit(issue_key)
        
        print("\n📌 Step 7: Update Jira → Done")
        update_jira_status(issue_key, "31")
        print(f"🎉 任务 {issue_key} 自动化处理成功！")
    else:
        print("\n❌ Tests failed!")
        print("🚨 测试未通过，拒绝提交代码。正在尝试回滚本地 AI 修改以保护工作区...")
        # 自动回滚修改，防止坏代码留在本地
        subprocess.run(["git", "checkout", "."])
        print("📌 Jira 状态未做变更，请检查 AI 代码生成逻辑。")

if __name__ == "__main__":
    agent("SCRUM-6")

