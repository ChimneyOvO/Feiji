"""
飞记应用程序入口主逻辑
"""

import sys
import os
import ctypes
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from feiji.core.database import DatabaseManager
from feiji.core.monitor import FeishuMonitor
from feiji.core.reminder import ReminderEngine
from feiji.ui.main_window import MainWindow


def main():
    # Windows 任务栏应用图标与独立分组支持
    if sys.platform == "win32":
        try:
            myappid = "feiji.todo.assistant.v1"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass

    # 高分屏 DPI 适配
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("飞记")
    app.setOrganizationName("FeiJi")
    app.setQuitOnLastWindowClosed(False)  # 允许关闭窗口后保持托盘常驻

    # 1. 初始化数据库
    db = DatabaseManager()

    # 2. 初始化监听与提醒核心引擎
    monitor = FeishuMonitor(db)
    reminder = ReminderEngine(db)

    # 3. 创建主界面
    window = MainWindow(db, monitor, reminder)
    window.show()

    # 4. 根据设置启动后台服务
    if db.get_setting("monitor_enabled", "1") == "1":
        monitor.start()

    reminder.start(interval_ms=15000)

    # 运行主循环
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
