import subprocess

def run_tests():
    result = subprocess.run(["pytest"], capture_output=True, text=True)
    print(result.stdout)
    return result.returncode == 0

if __name__ == "__main__":
    success = run_tests()
    print("Tests passed" if success else "Tests failed")
