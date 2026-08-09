import subprocess
import sys

def create_branch(issue_key):
    branch_name = f"feature/{issue_key}"
    try:
        subprocess.run(["git", "checkout", "-b", branch_name], check=True)
        print(f"✅ Created branch: {branch_name}")
    except subprocess.CalledProcessError:
        print("❌ Failed to create branch")
        sys.exit(1)

if __name__ == "__main__":
    create_branch("SCRUM-6")
