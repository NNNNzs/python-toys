import pkg_resources
import subprocess

# 获取所需的包列表
required_packages = {
    'openpyxl',
    'Pillow',
    'wxPython',
    'pyinstaller',
    'auto-py-to-exe',
    'pip',
    'setuptools',
    'wheel'
}

# 获取已安装包的版本信息
installed_packages = {pkg.key: pkg.version for pkg in pkg_resources.working_set}

# 生成requirements.txt
with open('requirements.txt', 'w', encoding='utf-8') as f:
    f.write("# 基础依赖\n")
    for pkg in ['openpyxl', 'Pillow', 'wxPython']:
        if pkg.lower() in installed_packages:
            f.write(f"{pkg}=={installed_packages[pkg.lower()]}\n")
    
    f.write("\n# 打包工具\n")
    for pkg in ['pyinstaller', 'auto-py-to-exe']:
        if pkg.lower() in installed_packages:
            f.write(f"{pkg}=={installed_packages[pkg.lower()]}\n")
    
    f.write("\n# 开发工具\n")
    for pkg in ['pip', 'setuptools', 'wheel']:
        if pkg.lower() in installed_packages:
            f.write(f"{pkg}=={installed_packages[pkg.lower()]}\n") 