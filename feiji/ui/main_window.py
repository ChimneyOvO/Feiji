"""
飞记主窗口：基于 FluentWindow 的侧边导航架构、系统托盘管理与到期提醒通知分发
"""

import os
import sys
from typing import Optional
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QPixmap, QColor, QPainter, QBrush, QAction
from PyQt6.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu, QWidget
)
from qfluentwidgets import (
    FluentWindow, NavigationItemPosition, FluentIcon,
    InfoBar, InfoBarPosition, setTheme, setThemeColor, Theme
)

from feiji.core.database import DatabaseManager
from feiji.core.monitor import FeishuMonitor
from feiji.core.reminder import ReminderEngine
from feiji.ui.board_view import BoardView
from feiji.ui.settings_view import SettingsView


class MainWindow(FluentWindow):
    """飞记主窗口"""

    def __init__(self, db: DatabaseManager, monitor: FeishuMonitor, reminder: ReminderEngine):
        super().__init__()
        self.db = db
        self.monitor = monitor
        self.reminder = reminder

        self._init_theme()
        self._init_subviews()
        self._init_window()
        self._init_tray()
        self._connect_signals()

    def _init_theme(self):
        """加载初始主题模式与主题色"""
        settings = self.db.get_all_settings()
        mode = settings.get("theme_mode", "Auto")
        if mode == "Light":
            setTheme(Theme.LIGHT)
        elif mode == "Dark":
            setTheme(Theme.DARK)
        else:
            setTheme(Theme.AUTO)

        color = settings.get("theme_color", "#0078D4")
        setThemeColor(color)

    def _init_subviews(self):
        """初始化导航页面"""
        self.board_view = BoardView(self.db, self.monitor, self)
        self.settings_view = SettingsView(self.db, self.monitor, self)

        # 添加到导航树
        self.addSubInterface(
            self.board_view,
            FluentIcon.APPLICATION,
            "待办看板"
        )
        self.addSubInterface(
            self.settings_view,
            FluentIcon.SETTING,
            "系统设置",
            NavigationItemPosition.BOTTOM
        )

    def _init_window(self):
        self.setWindowTitle("飞记 (FeiJi) - 飞书待办智能助手")
        self.resize(1120, 750)
        self.setMinimumSize(880, 600)

        # 居中显示
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    def _create_app_icon(self) -> QIcon:
        """生成一个干净大气的飞记 Logo 图标"""
        pix = QPixmap(64, 64)
        pix.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 圆角矩形背景 (Fluent Blue)
        painter.setBrush(QBrush(QColor("#0078D4")))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(4, 4, 56, 56, 14, 14)

        # 绘制白色的飞鸟/纸飞机极简形状
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor("#FFFFFF")))
        from PyQt6.QtGui import QPolygonF
        from PyQt6.QtCore import QPointF
        points = [
            QPointF(16, 32),
            QPointF(48, 18),
            QPointF(34, 46),
            QPointF(28, 36)
        ]
        painter.drawPolygon(QPolygonF(points))
        painter.end()

        return QIcon(pix)

    def _init_tray(self):
        """系统托盘图标与右键菜单"""
        base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        ico_path = os.path.join(base_dir, "feiji.ico")
        if os.path.exists(ico_path):
            self.app_icon = QIcon(ico_path)
        else:
            self.app_icon = self._create_app_icon()

        self.setWindowIcon(self.app_icon)

        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.app_icon)
        self.tray_icon.setToolTip("飞记 - 飞书待办智能助手\n后台监听中...")

        # 托盘菜单
        tray_menu = QMenu()

        show_action = QAction("显示主界面", self)
        show_action.triggered.connect(self.show_and_activate)
        tray_menu.addAction(show_action)

        tray_menu.addSeparator()

        self.toggle_monitor_action = QAction("暂停飞书监听", self)
        self.toggle_monitor_action.triggered.connect(self._on_toggle_tray_monitor)
        tray_menu.addAction(self.toggle_monitor_action)

        tray_menu.addSeparator()

        exit_action = QAction("退出飞记", self)
        exit_action.triggered.connect(self.quit_app)
        tray_menu.addAction(exit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _connect_signals(self):
        # 监听提醒引擎信号
        self.reminder.reminder_triggered.connect(self._on_reminder_triggered)
        # 监听飞书监控状态更新托盘菜单文字
        self.monitor.status_changed.connect(self._on_monitor_status_changed)

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.show_and_activate()

    def show_and_activate(self):
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def _on_toggle_tray_monitor(self):
        if self.monitor.is_running():
            self.monitor.stop()
        else:
            self.monitor.start()

    def _on_monitor_status_changed(self, running: bool, connected: bool, text: str):
        if running:
            self.toggle_monitor_action.setText("暂停飞书监听")
            self.tray_icon.setToolTip("飞记 - 飞书待办助手\n" + ("🟢 飞书在线" if connected else "🟡 监听就绪"))
        else:
            self.toggle_monitor_action.setText("启动飞书监听")
            self.tray_icon.setToolTip("飞记 - 飞书待办助手\n🔴 监听已暂停")

    def _on_reminder_triggered(self, task: dict, reminder_type: str, message: str):
        """提醒触发：推送 Windows 托盘气泡与应用内 InfoBar"""
        # 1. 系统托盘气泡通知（即使最小化也能看到）
        icon_type = QSystemTrayIcon.MessageIcon.Warning if reminder_type in ("due", "repeat") else QSystemTrayIcon.MessageIcon.Information
        self.tray_icon.showMessage(
            f"飞记待办提醒 ({'已到期' if reminder_type != 'advance' else '即将到期'})",
            message,
            icon_type,
            5000
        )

        # 2. 如果窗口处于前台，增加前台横幅
        if self.isVisible():
            if reminder_type == "advance":
                InfoBar.warning(
                    title="待办即将截止",
                    content=message,
                    parent=self,
                    position=InfoBarPosition.TOP_RIGHT,
                    duration=5000
                )
            else:
                InfoBar.error(
                    title="待办到期通知",
                    content=message,
                    parent=self,
                    position=InfoBarPosition.TOP_RIGHT,
                    duration=6000
                )
            self.board_view.refresh_board()

    def closeEvent(self, event):
        """关闭窗口时最小化到系统托盘，保持后台监听与到期提醒"""
        if self.tray_icon.isVisible():
            self.hide()
            self.tray_icon.showMessage(
                "飞记已最小化",
                "程序正在后台继续观察飞书并调度提醒。双击托盘图标可恢复界面。",
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )
            event.ignore()
        else:
            self.quit_app()

    def quit_app(self):
        """真正退出应用程序"""
        self.monitor.stop()
        self.reminder.stop()
        self.tray_icon.hide()
        QApplication.quit()
