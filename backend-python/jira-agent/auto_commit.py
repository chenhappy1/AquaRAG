import subprocess
import sys

def auto_commit(issue_key):
    try:
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", f"{issue_key}: auto update"], check=True)
        subprocess.run(["git", "push", "--set-upstream", "origin", f"feature/{issue_key}"], check=True)
        print("✅ Code committed & pushed")
    except subprocess.CalledProcessError:
        print("❌ Commit failed")
        sys.exit(1)

if __name__ == "__main__":
    auto_commit("SCRUM-6")
