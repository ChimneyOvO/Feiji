@echo off
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
