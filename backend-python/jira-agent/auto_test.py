import subprocess
import os
import py_compile

def run_tests():
    backend_success = True
    frontend_success = True

    # 1. 后端 Python 语法健康检查
    backend_py_path = r"D:\AquaRAG\backend-python"
    print("⏳ 正在检查 Python 后端代码语法是否正确...")
    if os.path.exists(backend_py_path):
        try:
            # 自动遍历后端所有 .py 文件，检查是否有语法错误
            for root, _, filenames in os.walk(backend_py_path):
                for f in filenames:
                    if f.endswith(".py"):
                        file_path = os.path.join(root, f)
                        py_compile.compile(file_path, doraise=True)
            print("✅ 后端 Python 代码语法检查通过！")
        except py_compile.PyCompileError as e:
            print(f"❌ 后端 Python 代码存在语法错误:\n{e}")
            backend_success = False

    # 2. 前端编译健康检查 (检查 AI 是否写挂了标签或引用)
    frontend_path = r"D:\AquaRAG\frontend"
    print("\n⏳ 正在检查前端代码是否可以正常编译...")
    if os.path.exists(frontend_path):
        # 使用 npm run build 替代 npm test。如果没有写测试，build 能检验代码能否正常跑起来
        result_frontend = subprocess.run(
            ["npm", "run", "build"], 
            cwd=frontend_path, 
            capture_output=True, 
            text=True,
            shell=True 
        )
        if result_frontend.returncode != 0:
            print("❌ 前端打包编译失败！AI 修改的代码可能存在文件引用或组件语法错误。")
            print(result_frontend.stderr)
            frontend_success = False
        else:
            print("✅ 前端打包编译成功！")

    return backend_success and frontend_success
