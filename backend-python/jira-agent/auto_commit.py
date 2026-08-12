import os
import subprocess
import sys

def auto_commit(issue_key):
    try:
        # ⭐ 切换到项目根目录
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        os.chdir(project_root)
        print(f"📁 Working directory switched to: {project_root}")

        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", f"{issue_key}: auto update"], check=True)
        subprocess.run(["git", "push", "-f", "--set-upstream", "origin", f"feature/{issue_key}"], check=True)

        print("✅ Code committed & pushed")
    except subprocess.CalledProcessError:
        print("❌ Commit failed")
        sys.exit(1)

if __name__ == "__main__":
    auto_commit("SCRUM-6")

