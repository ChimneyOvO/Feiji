"""
测试自然语言时间与关键词提取器
"""

import unittest
from datetime import datetime, timedelta
from feiji.core.parser import TaskParser


class TestTaskParser(unittest.TestCase):
    def setUp(self):
        self.keywords = ["帮忙", "辛苦", "TODO", "需要完成", "截止"]
        self.parser = TaskParser(self.keywords)
        # 固定测试基准时间：2026-09-07 10:00:00 (星期一)
        self.base_time = datetime(2026, 9, 7, 10, 0, 0)

    def test_keyword_matching(self):
        self.assertTrue(self.parser.matches_keyword("请大家帮忙看看这个方案")[0])
        self.assertTrue(self.parser.matches_keyword("TODO: 修改登录页面")[0])
        self.assertTrue(self.parser.matches_keyword("这个功能需要完成代码审查")[0])
        self.assertFalse(self.parser.matches_keyword("今天天气不错，一起去喝咖啡吧")[0])

    def test_relative_hours_and_minutes(self):
        # 2小时后
        res = TaskParser.extract_deadline("请在2小时后提交给我", self.base_time)
        self.assertEqual(res, self.base_time + timedelta(hours=2))

        # 30分钟后
        res = TaskParser.extract_deadline("麻烦30分钟后把数据导出发我", self.base_time)
        self.assertEqual(res, self.base_time + timedelta(minutes=30))

        # 半小时后
        res = TaskParser.extract_deadline("半小时后开会", self.base_time)
        self.assertEqual(res, self.base_time + timedelta(minutes=30))

    def test_today_and_tomorrow(self):
        # 今天下午3点
        res = TaskParser.extract_deadline("今天下午3点前完成对账", self.base_time)
        self.assertEqual(res, datetime(2026, 9, 7, 15, 0, 0))

        # 明天上午10:30
        res = TaskParser.extract_deadline("明天上午10:30前整理发群里", self.base_time)
        self.assertEqual(res, datetime(2026, 9, 8, 10, 30, 0))

        # 明天下班前 / 明天
        res = TaskParser.extract_deadline("辛苦明天完成初稿", self.base_time)
        self.assertEqual(res, datetime(2026, 9, 8, 18, 0, 0))

        # 后天下午5点
        res = TaskParser.extract_deadline("后天下午5点前必须交付", self.base_time)
        self.assertEqual(res, datetime(2026, 9, 9, 17, 0, 0))

    def test_weekdays(self):
        # 2026-09-07 是周一
        # 周五下班前 -> 2026-09-11 18:00:00
        res = TaskParser.extract_deadline("本周五下班前帮忙核对一下", self.base_time)
        self.assertEqual(res, datetime(2026, 9, 11, 18, 0, 0))

        # 下周一上午9点 -> 2026-09-14 09:00:00
        res = TaskParser.extract_deadline("下周一上午9点准时上线", self.base_time)
        self.assertEqual(res, datetime(2026, 9, 14, 9, 0, 0))

    def test_explicit_dates(self):
        # 9月15日 14:00
        res = TaskParser.extract_deadline("请在9月15日14点提交汇报材料", self.base_time)
        self.assertEqual(res, datetime(2026, 9, 15, 14, 0, 0))

    def test_full_parse_message(self):
        msg = "@张三 辛苦明天下午3点半前帮忙把周报汇总发我一下"
        parsed = self.parser.parse_message(msg, self.base_time)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["deadline"], "2026-09-08 15:30:00")
        self.assertIn("帮忙", msg)
        self.assertNotIn("@张三", parsed["title"])


if __name__ == "__main__":
    unittest.main()
