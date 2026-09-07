@echo off
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
