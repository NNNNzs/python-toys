@echo off
cd /d "%~dp0"
start ExcelImageCompressor.exe
if errorlevel 1 (
    echo 程序启动失败，错误代码：%errorlevel%
    pause
) 