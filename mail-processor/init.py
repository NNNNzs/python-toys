"""
@description 初始化项目依赖
@author AI Assistant
@date 2024
"""
import subprocess
import sys

def install_requirements():
    """
    安装项目依赖
    """
    print("开始安装依赖...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("依赖安装成功!")
    except subprocess.CalledProcessError as e:
        print(f"依赖安装失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    install_requirements()