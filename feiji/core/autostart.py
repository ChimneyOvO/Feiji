"""
开机自启动管理：通过 Windows 注册表 HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run 管理
"""

import sys
import os
import winreg

APP_REG_NAME = "FeiJiApp"


class AutoStartManager:
    """Windows 开机自启动管理器"""

    REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"

    @classmethod
    def is_autostart_enabled(cls) -> bool:
        """检查当前是否已加入开机自启"""
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, cls.REG_PATH, 0, winreg.KEY_READ) as key:
                val, _ = winreg.QueryValueEx(key, APP_REG_NAME)
                return bool(val)
        except (FileNotFoundError, OSError):
            return False

    @classmethod
    def set_autostart(cls, enabled: bool) -> bool:
        """开启或关闭开机自启"""
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, cls.REG_PATH, 0, winreg.KEY_WRITE) as key:
                if enabled:
                    # 获取可执行文件路径或启动脚本
                    if getattr(sys, 'frozen', False):
                        # 打包后的 exe
                        cmd = f'"{sys.executable}"'
                    else:
                        # 源码运行模式
                        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                        run_script = os.path.join(project_root, "run.py")
                        # 优先使用 pythonw 避免黑框
                        py_dir = os.path.dirname(sys.executable)
                        pythonw = os.path.join(py_dir, "pythonw.exe")
                        py_exec = pythonw if os.path.exists(pythonw) else sys.executable
                        cmd = f'"{py_exec}" "{run_script}"'

                    winreg.SetValueEx(key, APP_REG_NAME, 0, winreg.REG_SZ, cmd)
                else:
                    try:
                        winreg.DeleteValue(key, APP_REG_NAME)
                    except FileNotFoundError:
                        pass
            return True
        except OSError as e:
            print(f"[AutoStart] 注册表修改失败: {e}")
            return False
