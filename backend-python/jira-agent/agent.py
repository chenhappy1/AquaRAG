import sys
import os
import subprocess

from read_ticket import get_jira_issue
from ai_update_code_from_ticket import ai_update_code_from_ticket
from ai_update_md import ai_update_md_from_ticket
from auto_branch import create_branch
from auto_commit import auto_commit
from auto_test import run_tests
from update_ticket import update_jira_status
from auto_pr import create_pr


# ---------------------------------------------------------
# ⭐ 修复 Jira Cloud rich text → 转成纯文本
# ---------------------------------------------------------
def extract_description_text(description):
    if not description:
        return ""

    try:
        content = description.get("content", [])
        texts = []

        for block in content:
            if "content" in block:
                for item in block["content"]:
                    if item.get("type") == "text":
                        texts.append(item.get("text", ""))

        return "\n".join(texts)

    except Exception:
        return str(description)


# ---------------------------------------------------------
# ⭐ 主 Agent 自动化流水线
# ---------------------------------------------------------
def agent(issue_key):
    print(f"🚀 开始执行 Agent 自动化流水线: {issue_key}")

    # -----------------------------------------------------
    # ⭐ Step 0: 切换到项目根目录（关键修复）
    # -----------------------------------------------------
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    os.chdir(project_root)
    print(f"📁 Working directory switched to: {project_root}")

    # -----------------------------------------------------
    # ⭐ Step 1: 读取 Jira Ticket
    # -----------------------------------------------------
    print("\n📌 Step 1: Read Jira Ticket")
    ticket = get_jira_issue(issue_key)

    summary = ticket["fields"]["summary"]
    raw_description = ticket["fields"]["description"]
    description = extract_description_text(raw_description)

    ticket_text = summary + "\n" + description
    print(f"📄 Jira 内容:\n{ticket_text}")

    # -----------------------------------------------------
    # ⭐ Step 2: 创建分支
    # -----------------------------------------------------
    print(f"\n📌 Step 2: Create Git Branch for {issue_key}")
    try:
        create_branch(issue_key)
    except Exception as e:
        print(f"⚠ 创建分支失败或分支已存在: {e}，继续执行...")

    # -----------------------------------------------------
    # ⭐ Step 3: AI 修改代码 + 文档
    # -----------------------------------------------------
    print("\n📌 Step 3: AI Update Code & Documentation (.md)")
    ai_update_code_from_ticket(ticket_text)
    ai_update_md_from_ticket(ticket_text)

    # -----------------------------------------------------
    # ⭐ Step 4: Git Diff
    # -----------------------------------------------------
    print("\n📌 Step 4: Compare Difference (Git Diff)")
    try:
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

    # -----------------------------------------------------
    # ⭐ Step 5: 自动测试
    # -----------------------------------------------------
    print("\n📌 Step 5: Run Tests")
    success = run_tests()

    # -----------------------------------------------------
    # ⭐ Step 6: 自动提交 + 推送
    # -----------------------------------------------------
    if success:
        print("\n📌 Step 6: Auto Commit Code + Docs")
        auto_commit(issue_key)

        # -------------------------------------------------
        # ⭐ Step 6.5: 自动创建 PR
        # -------------------------------------------------
        print("\n📌 Step 6.5: Auto Create Remote Pull Request")
        pr_url = create_pr(issue_key, summary)
        print(f"🔗 PR 已创建: {pr_url}")

        # -------------------------------------------------
        # ⭐ Step 7: 更新 Jira 状态
        # -------------------------------------------------
        print("\n📌 Step 7: Update Jira → Done")
        update_jira_status(issue_key, "31")  # 31 = Done
        print(f"🎉 任务 {issue_key} 自动化处理成功！")

    else:
        # -------------------------------------------------
        # ❌ 测试失败 → 回滚 AI 修改
        # -------------------------------------------------
        print("\n❌ Tests failed!")
        print("🚨 测试未通过，拒绝提交代码。正在回滚本地 AI 修改...")
        subprocess.run(["git", "checkout", "."])
        print("📌 Jira 状态未做变更，请检查 AI 代码生成逻辑。")


# ---------------------------------------------------------
# ⭐ 入口
# ---------------------------------------------------------
if __name__ == "__main__":
    agent("SCRUM-7")


