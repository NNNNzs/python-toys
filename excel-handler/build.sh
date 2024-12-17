#!/bin/bash

# 设置颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 输出带颜色的信息
info() {
    echo -e "${GREEN}[INFO] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[WARN] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
}

# 检查依赖
check_dependencies() {
    info "检查依赖..."
    python3 check_deps.py
    if [ $? -ne 0 ]; then
        error "依赖检查失败"
        exit 1
    fi
}

# 生成图标
generate_icon() {
    info "生成图标..."
    python3 icon.py
    if [ $? -ne 0 ]; then
        error "图标生成失败"
        exit 1
    fi
}

# 清理旧的构建文件
clean_build() {
    info "清理旧的构建文件..."
    rm -rf build dist
    rm -f *.spec
}

# 创建Windows版本spec文件
create_windows_spec() {
    cat > excel-handler-win.spec << EOL
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['zip-img.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['PIL', 'PIL._imagingtk', 'PIL._tkinter_finder', 'openpyxl'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ExcelImageCompressor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico'
)
EOL
}

# 创建macOS版本spec文件
create_macos_spec() {
    cat > excel-handler-mac.spec << EOL
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['zip-img.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['PIL', 'PIL._imagingtk', 'PIL._tkinter_finder', 'openpyxl'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ExcelImageCompressor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.icns'
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ExcelImageCompressor'
)

app = BUNDLE(
    coll,
    name='ExcelImageCompressor.app',
    icon='icon.icns',
    bundle_identifier='com.exceltools.imagecompressor',
    info_plist={
        'NSHighResolutionCapable': 'True',
        'LSBackgroundOnly': 'False',
        'CFBundleShortVersionString': '1.0.0',
    },
)
EOL
}

# 打包Windows版本
build_windows() {
    info "开始打包Windows版本..."
    create_windows_spec
    pyinstaller --clean excel-handler-win.spec
    if [ $? -ne 0 ]; then
        error "Windows版本打包失败"
        return 1
    fi
    
    # 创建发布目录
    mkdir -p release/windows
    cp dist/ExcelImageCompressor.exe release/windows/
    cp start.bat release/windows/
    
    # 创建zip包
    cd release
    zip -r ExcelImageCompressor-windows.zip windows
    cd ..
    
    info "Windows版本打包完成"
}

# 打包macOS版本
build_macos() {
    info "开始打包macOS版本..."
    create_macos_spec
    pyinstaller --clean excel-handler-mac.spec
    if [ $? -ne 0 ]; then
        error "macOS版本打包失败"
        return 1
    fi
    
    # 创建发布目录
    mkdir -p release/macos
    cp -r dist/ExcelImageCompressor.app release/macos/
    
    # 创建zip包
    cd release
    zip -r ExcelImageCompressor-macos.zip macos
    cd ..
    
    info "macOS版本打包完成"
}

# 主函数
main() {
    info "开始构建Excel图片压缩工具..."
    
    # 检查依赖
    check_dependencies
    
    # 生成图标
    generate_icon
    
    # 清理旧的构建文件
    clean_build
    
    # 创建release目录
    mkdir -p release
    
    # 根据操作系统打包
    if [[ "$OSTYPE" == "darwin"* ]]; then
        build_macos
        warn "Windows版本需要在Windows系统上构建"
    elif [[ "$OSTYPE" == "msys"* ]] || [[ "$OSTYPE" == "cygwin"* ]]; then
        build_windows
        warn "macOS版本需要在macOS系统上构建"
    else
        error "不支持的操作系统"
        exit 1
    fi
    
    info "构建完成！"
    info "发布文件位于 release 目录"
}

# 执行主函数
main 