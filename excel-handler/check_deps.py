import sys
import pkg_resources

required = {'pillow', 'openpyxl', 'wxPython'}
installed = {pkg.key for pkg in pkg_resources.working_set}
missing = required - installed

if missing:
    print("缺少以下依赖包：")
    for pkg in missing:
        print(f"  - {pkg}")
else:
    print("所有依赖包已安装")

# 检查版本
print("\n已安装的包版本：")
for pkg in required:
    try:
        version = pkg_resources.get_distribution(pkg).version
        print(f"{pkg}: {version}")
    except pkg_resources.DistributionNotFound:
        print(f"{pkg}: 未安装") 