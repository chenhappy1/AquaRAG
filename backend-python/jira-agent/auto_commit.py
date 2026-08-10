import subprocess
import sys

def auto_commit(issue_key):
    try:
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", f"{issue_key}: auto update"], check=True)
        
        # 💡 核心修改：在列表中加入 "-f" 参数来强制推送，覆盖远端冲突
        subprocess.run(["git", "push", "-f", "--set-upstream", "origin", f"feature/{issue_key}"], check=True)
        
        print("✅ Code committed & pushed")
    except subprocess.CalledProcessError:
        print("❌ Commit failed")
        sys.exit(1)

if __name__ == "__main__":
    auto_commit("SCRUM-6")
