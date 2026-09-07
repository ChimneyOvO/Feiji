"""
飞记 (FeiJi) 打包与安装包构建脚本
自动执行：
1. PyInstaller 编译生成独立无黑框可执行程序 (FeiJi.exe)
2. 生成桌面快捷方式一键安装器 (安装-创建桌面快捷方式.bat)
3. 生成一键卸载脚本 (卸载飞记.bat)
4. 打包输出完整的绿色版与安装包 ZIP 压缩包
"""

import os
import sys
import shutil
import zipfile
import subprocess

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(PROJECT_DIR, "dist")
BUILD_DIR = os.path.join(PROJECT_DIR, "build")
APP_NAME = "FeiJi"
VERSION = "1.0.0"


def run_pyinstaller():
    print(f"=== [1/4] 开始使用 PyInstaller 编译打包 {APP_NAME}.exe ===")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",              # 无控制台黑框
        "--onefile",               # 单文件独立可执行程序
        f"--name={APP_NAME}",
        f"--icon={os.path.join(PROJECT_DIR, 'feiji.ico')}",
        f"--add-data={os.path.join(PROJECT_DIR, 'feiji.ico')};.",
        "--collect-all=qfluentwidgets",
        "--collect-all=uiautomation",
        "--hidden-import=win32clipboard",
        "--hidden-import=win32gui",
        "--hidden-import=win32process",
        "--hidden-import=comtypes",
        os.path.join(PROJECT_DIR, "run.py")
    ]
    print("执行命令:", " ".join(cmd))
    res = subprocess.run(cmd, cwd=PROJECT_DIR)
    if res.returncode != 0:
        raise RuntimeError(f"PyInstaller 打包失败，退出码: {res.returncode}")
    print(f"--> {APP_NAME}.exe 编译成功！")


def create_installer_package():
    print(f"\n=== [2/4] 构建安装包分发目录 ===")
    setup_dir = os.path.join(DIST_DIR, f"FeiJi_Setup_v{VERSION}")
    if os.path.exists(setup_dir):
        shutil.rmtree(setup_dir)
    os.makedirs(setup_dir, exist_ok=True)

    # 1. 拷贝主执行程序与图标
    exe_src = os.path.join(DIST_DIR, f"{APP_NAME}.exe")
    shutil.copy2(exe_src, os.path.join(setup_dir, f"{APP_NAME}.exe"))
    shutil.copy2(os.path.join(PROJECT_DIR, "feiji.ico"), os.path.join(setup_dir, "feiji.ico"))

    # 2. 生成安装脚本 (安装到用户本地应用程序目录，并创建桌面与开始菜单快捷方式)
    install_bat = os.path.join(setup_dir, "安装飞记(创建桌面快捷方式).bat")
    with open(install_bat, "w", encoding="gbk", errors="ignore") as f:
        f.write(r"""@echo off
chcp 936 >nul
title 飞记 (FeiJi) - 自动安装程序
echo ========================================================
echo             飞记 (FeiJi) - 飞书待办智能助手
echo ========================================================
echo.
echo 正在安装飞记到您的电脑...

set "TARGET_DIR=%LOCALAPPDATA%\FeiJi"
if not exist "%TARGET_DIR%" mkdir "%TARGET_DIR%"

echo [1/3] 复制程序文件到: %TARGET_DIR% ...
copy /Y "%~dp0FeiJi.exe" "%TARGET_DIR%\FeiJi.exe" >nul
copy /Y "%~dp0feiji.ico" "%TARGET_DIR%\feiji.ico" >nul

echo [2/3] 创建桌面快捷方式与开始菜单图标...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ws = New-Object -ComObject WScript.Shell; ^
   $s = $ws.CreateShortcut([System.IO.Path]::Combine([Environment]::GetFolderPath('Desktop'), '飞记.lnk')); ^
   $s.TargetPath = [System.IO.Path]::Combine($env:LOCALAPPDATA, 'FeiJi\FeiJi.exe'); ^
   $s.IconLocation = [System.IO.Path]::Combine($env:LOCALAPPDATA, 'FeiJi\feiji.ico'); ^
   $s.Description = '飞记 - 飞书待办智能助手'; ^
   $s.Save(); ^
   $sm = [Environment]::GetFolderPath('StartMenu'); ^
   $s2 = $ws.CreateShortcut([System.IO.Path]::Combine($sm, 'Programs\飞记.lnk')); ^
   $s2.TargetPath = [System.IO.Path]::Combine($env:LOCALAPPDATA, 'FeiJi\FeiJi.exe'); ^
   $s2.IconLocation = [System.IO.Path]::Combine($env:LOCALAPPDATA, 'FeiJi\feiji.ico'); ^
   $s2.Description = '飞记 - 飞书待办智能助手'; ^
   $s2.Save();"

echo [3/3] 安装完成！
echo.
echo 桌面已生成【飞记】快捷方式，随时双击即可开启！
echo.
set /p launch="是否立即启动飞记？(Y/N, 默认Y): "
if /i "%launch%"=="n" goto end
start "" "%TARGET_DIR%\FeiJi.exe"

:end
echo.
echo 感谢使用飞记，按任意键退出安装向导...
pause >nul
""")

    # 3. 生成卸载脚本
    uninstall_bat = os.path.join(setup_dir, "卸载飞记.bat")
    with open(uninstall_bat, "w", encoding="gbk", errors="ignore") as f:
        f.write(r"""@echo off
chcp 936 >nul
title 卸载飞记
echo 正在卸载飞记...
taskkill /F /IM FeiJi.exe >nul 2>&1

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$desk = [System.IO.Path]::Combine([Environment]::GetFolderPath('Desktop'), '飞记.lnk'); ^
   if (Test-Path $desk) { Remove-Item $desk -Force }; ^
   $sm = [System.IO.Path]::Combine([Environment]::GetFolderPath('StartMenu'), 'Programs\飞记.lnk'); ^
   if (Test-Path $sm) { Remove-Item $sm -Force };"

set "TARGET_DIR=%LOCALAPPDATA%\FeiJi"
if exist "%TARGET_DIR%" rd /s /q "%TARGET_DIR%"

echo.
echo 飞记已成功从您的电脑中卸载。
pause
""")

    # 4. 说明文件
    readme_txt = os.path.join(setup_dir, "使用说明.txt")
    with open(readme_txt, "w", encoding="utf-8") as f:
        f.write("""飞记 (FeiJi) - 飞书待办智能助手 v1.0.0
=====================================================

【快速使用方法】
1. 双击运行【安装飞记(创建桌面快捷方式).bat】，即可自动完成安装并生成桌面图标。
2. 也可直接双击【FeiJi.exe】免安装运行（绿色便携版）。

【飞书待办捕获方式】
- 在飞书中看到或发送任意待办消息，鼠标右键点击【复制】（或按 Ctrl+C）。
- 飞记将在右下角瞬间弹出提示，并自动提取截止时间添加入待办看板中！

【卸载方法】
- 双击运行【卸载飞记.bat】即可一键彻底清理程序与快捷方式。
""")

    print(f"--> 安装包分发目录已就绪: {setup_dir}")
    return setup_dir


def zip_packages(setup_dir):
    print(f"\n=== [3/4] 压缩打包安装包 ZIP ===")
    zip_path = os.path.join(DIST_DIR, f"FeiJi_v{VERSION}_Setup_x64.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(setup_dir):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, DIST_DIR)
                zf.write(full_path, rel_path)

    print(f"--> 安装包压缩包生成成功: {zip_path}")
    print(f"    大小: {os.path.getsize(zip_path) / (1024*1024):.2f} MB")
    return zip_path


def main():
    run_pyinstaller()
    setup_dir = create_installer_package()
    zip_path = zip_packages(setup_dir)
    print("\n=== [4/4] 打包全流程完成！===")
    print(f"1. 独立单文件版: {os.path.join(DIST_DIR, 'FeiJi.exe')}")
    print(f"2. 安装包目录:   {setup_dir}")
    print(f"3. 发布压缩包:   {zip_path}")


if __name__ == "__main__":
    main()
