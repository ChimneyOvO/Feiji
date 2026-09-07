"""
测试监控器消息处理与去重
"""

import unittest
import os
import tempfile
from feiji.core.database import DatabaseManager
from feiji.core.monitor import FeishuMonitor


class TestMonitor(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_monitor.db")
        self.db = DatabaseManager(self.db_path)
        self.monitor = FeishuMonitor(self.db)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_simulate_message_flow(self):
        # 模拟包含关键词和时间的消息
        msg = "项目组各位，辛苦明天下午4点前把各自的模块自测报告提交到群里，需要完成统计"
        task = self.monitor.simulate_message(msg)
        self.assertIsNotNone(task)
        self.assertEqual(task["status"], "todo")
        self.assertIn("自测报告", task["title"])
        self.assertIsNotNone(task["deadline"])

        # 测试防重复
        dup_task = self.monitor.simulate_message(msg)
        self.assertIsNone(dup_task)

        # 测试不包含关键词的消息
        irrelevant_msg = "中午一起去吃面吗？"
        no_task = self.monitor.simulate_message(irrelevant_msg)
        self.assertIsNone(no_task)


if __name__ == "__main__":
    unittest.main()
