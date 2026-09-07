"""
集成测试：验证主界面组件加载、数据库联动、模拟消息识别与任务流转
"""

import sys
import os
import unittest
import tempfile
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from feiji.core.database import DatabaseManager
from feiji.core.monitor import FeishuMonitor
from feiji.core.reminder import ReminderEngine
from feiji.ui.main_window import MainWindow

# 确保单例 QApplication 存在
app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)


class TestIntegration(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_integration.db")
        self.db = DatabaseManager(self.db_path)
        self.monitor = FeishuMonitor(self.db)
        self.reminder = ReminderEngine(self.db)
        self.window = MainWindow(self.db, self.monitor, self.reminder)

    def tearDown(self):
        self.window.quit_app()
        self.temp_dir.cleanup()

    def test_window_initialization(self):
        self.assertIsNotNone(self.window.board_view)
        self.assertIsNotNone(self.window.settings_view)
        self.assertEqual(self.window.windowTitle(), "飞记 (FeiJi) - 飞书待办智能助手")

    def test_simulate_message_and_board_update(self):
        # 1. 模拟收到飞书包含待办与时间的消息
        msg = "研发组各位，辛苦明天下午5点前帮忙将各自分支合并并提测"
        task = self.monitor.simulate_message(msg)
        self.assertIsNotNone(task)
        self.assertEqual(task["status"], "todo")

        # 2. 检查看板是否更新 (初始有1个示例todo，新增后为2个)
        self.window.board_view.refresh_board()
        self.assertEqual(len(self.window.board_view.col_todo._cards), 2)

        # 3. 状态流转：流转至进行中
        task_id = task["id"]
        self.window.board_view._on_status_change(task_id, "in_progress")
        self.assertEqual(len(self.window.board_view.col_todo._cards), 1)
        self.assertEqual(len(self.window.board_view.col_progress._cards), 2)

        # 4. 状态流转：流转至已完成
        self.window.board_view._on_status_change(task_id, "done")
        self.assertEqual(len(self.window.board_view.col_progress._cards), 1)
        self.assertEqual(len(self.window.board_view.col_done._cards), 2)

        # 5. 验证统计数字与进度条 (2完成 / 4总计 = 50%)
        stats = self.db.get_task_statistics()
        self.assertEqual(stats["done"], 2)
        self.assertEqual(stats["total"], 4)
        self.assertEqual(self.window.board_view.progress_bar.value(), 50)


if __name__ == "__main__":
    unittest.main()
