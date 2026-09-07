"""
测试 SQLite 数据库操作
"""

import unittest
import os
import tempfile
from feiji.core.database import DatabaseManager


class TestDatabaseManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_feiji.db")
        self.db = DatabaseManager(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_task_lifecycle(self):
        # 增
        task_id = self.db.add_task(
            title="测试任务",
            content="请明天提交周报",
            deadline="2026-09-08 18:00:00",
            source="feishu"
        )
        self.assertGreater(task_id, 0)

        # 查
        task = self.db.get_task(task_id)
        self.assertEqual(task["title"], "测试任务")
        self.assertEqual(task["status"], "todo")

        # 改状态
        self.db.update_task_status(task_id, "in_progress")
        updated_task = self.db.get_task(task_id)
        self.assertEqual(updated_task["status"], "in_progress")

        # 统计 (含首次运行的 3 个示例引导任务)
        stats = self.db.get_task_statistics()
        self.assertEqual(stats["in_progress"], 2)
        self.assertEqual(stats["total"], 4)

        # 删
        self.assertTrue(self.db.delete_task(task_id))
        self.assertIsNone(self.db.get_task(task_id))
        stats_after = self.db.get_task_statistics()
        self.assertEqual(stats_after["total"], 3)

    def test_keywords_and_settings(self):
        keywords = self.db.get_keywords()
        self.assertGreater(len(keywords), 0)

        # 新增关键词
        self.assertTrue(self.db.add_keyword("紧急"))
        all_kw = [k["keyword"] for k in self.db.get_keywords()]
        self.assertIn("紧急", all_kw)

        # 校验设置读写
        self.db.set_setting("theme_mode", "Dark")
        self.assertEqual(self.db.get_setting("theme_mode"), "Dark")

    def test_message_deduplication(self):
        hash_val = "abc123hash"
        self.assertFalse(self.db.is_message_processed(hash_val))
        self.db.mark_message_processed(hash_val)
        self.assertTrue(self.db.is_message_processed(hash_val))


if __name__ == "__main__":
    unittest.main()
