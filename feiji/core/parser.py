"""
自然语言任务与时间解析器：负责关键词命中判断、中文相对/绝对截止时间提取与标题精简
"""

import re
from datetime import datetime, timedelta
from typing import Optional, Tuple, List, Dict, Any


class TaskParser:
    """中文待办与截止时间解析器"""

    # 星期数字映射
    WEEKDAY_MAP = {
        "一": 0, "1": 0,
        "二": 1, "2": 1,
        "三": 2, "3": 2,
        "四": 3, "4": 3,
        "五": 4, "5": 4,
        "六": 5, "6": 5,
        "日": 6, "天": 6, "7": 6,
    }

    # 中文数字映射 (1-59)
    CN_NUM = {
        "零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
        "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
        "十一": 11, "十二": 12, "十三": 13, "十四": 14, "十五": 15,
        "十六": 16, "十七": 17, "十八": 18, "十九": 19, "二十": 20,
        "三十": 30, "四十": 40, "五十": 50
    }

    def __init__(self, keywords: Optional[List[str]] = None):
        self.keywords = keywords or []

    def set_keywords(self, keywords: List[str]):
        self.keywords = keywords

    def matches_keyword(self, text: str) -> Tuple[bool, Optional[str]]:
        """检查文本是否包含任意关键词"""
        if not text:
            return False, None
        text_lower = text.lower()
        for kw in self.keywords:
            if kw and kw.lower() in text_lower:
                return True, kw
        # 智能判定：若文本包含明确的截止时间表达且伴随任务动作指示词（如 "前"、"完成"、"提交"、"收集" 等）
        if self.extract_deadline(text) is not None:
            if re.search(r"前|之前|截止|截至|完成|提交|更新|收集|整理|汇总|发我|发群|安排|处理|交付|上线|核对|反馈|回复|做完", text):
                return True, "截止时间命中"
        return False, None

    @classmethod
    def _parse_cn_number(cls, s: str) -> Optional[int]:
        """将简单中文数字转为整数（例如 '三', '二十五', '15'）"""
        s = s.strip()
        if not s:
            return None
        if s.isdigit():
            return int(s)
        if s in cls.CN_NUM:
            return cls.CN_NUM[s]
        # 匹配如 "二十三", "三十五"
        m = re.match(r"^([二三四五])十([一二两三四五六七八九])?$", s)
        if m:
            ten = cls.CN_NUM[m.group(1)]
            unit = cls.CN_NUM[m.group(2)] if m.group(2) else 0
            return ten + unit
        return None

    @classmethod
    def extract_deadline(cls, text: str, base_time: Optional[datetime] = None) -> Optional[datetime]:
        """
        从文本中提取截止时间，支持各类口语化中文表达
        """
        if not text:
            return None
        now = base_time or datetime.now()

        # 1. 相对时间：X小时后 / X分钟后 / X天后 / 半小时后
        delta_match = re.search(
            r"(?P<num>\d+|[一二两三四五六七八九十]+|半)\s*(?P<unit>个?小时|分钟|天|周)后",
            text
        )
        if delta_match:
            num_str = delta_match.group("num")
            unit_str = delta_match.group("unit")
            if num_str == "半":
                num = 0.5
            else:
                num = float(cls._parse_cn_number(num_str) or 1)

            if "分" in unit_str:
                return now + timedelta(minutes=int(num))
            elif "小" in unit_str:
                return now + timedelta(minutes=int(num * 60))
            elif "天" in unit_str:
                target_date = now + timedelta(days=int(num))
                return target_date.replace(hour=18, minute=0, second=0, microsecond=0)
            elif "周" in unit_str:
                target_date = now + timedelta(days=int(num * 7))
                return target_date.replace(hour=18, minute=0, second=0, microsecond=0)

        # 2. 绝对日期或相对日期推导
        target_date: Optional[datetime] = None
        has_explicit_date = False

        # 2.1 显式月日或年月日：如 2026-09-10 / 2026/09/10 / 9月15日 / 9-15
        date_pattern = re.search(
            r"(?:(?P<year>\d{4})[-/年])?(?P<month>\d{1,2})[-/月](?P<day>\d{1,2})[日号]?",
            text
        )
        if date_pattern:
            year = int(date_pattern.group("year")) if date_pattern.group("year") else now.year
            month = int(date_pattern.group("month"))
            day = int(date_pattern.group("day"))
            try:
                target_date = datetime(year, month, day)
                has_explicit_date = True
            except ValueError:
                pass

        # 2.2 相对日期词：今天、今晚、明天、后天、大后天
        if not target_date:
            if re.search(r"大后天", text):
                target_date = now + timedelta(days=3)
                has_explicit_date = True
            elif re.search(r"后天", text):
                target_date = now + timedelta(days=2)
                has_explicit_date = True
            elif re.search(r"明[天早晚日]", text):
                target_date = now + timedelta(days=1)
                has_explicit_date = True
            elif re.search(r"今[天晚日早]|当天", text):
                target_date = now
                has_explicit_date = True

        # 2.3 星期推导：下周X / 下星期X / 本周X / 周X / 礼拜X
        if not target_date:
            week_match = re.search(
                r"(?P<prefix>下下|下|本|这)?(?P<unit>周|星期|礼拜)(?P<w>[一二三四五六日天1234567])",
                text
            )
            if week_match:
                prefix = week_match.group("prefix") or "本"
                w_str = week_match.group("w")
                target_weekday = cls.WEEKDAY_MAP.get(w_str, 0)
                current_weekday = now.weekday()

                days_ahead = target_weekday - current_weekday
                if prefix == "下":
                    days_ahead += 7
                elif prefix == "下下":
                    days_ahead += 14
                elif days_ahead < 0:  # 本周但该天已过，默认顺延至下周
                    days_ahead += 7

                target_date = now + timedelta(days=days_ahead)
                has_explicit_date = True

        # 3. 时间点解析（时、分）
        hour = 18  # 默认下班前 18:00
        minute = 0
        has_explicit_time = False

        # 3.1 时段词检测：上午/中午/下午/晚上/下班前/下班后
        is_pm = False
        is_am = False
        if re.search(r"下午|晚上|傍晚|今晚|明晚|后天晚上", text):
            is_pm = True
        elif re.search(r"上午|早上|早晨|清晨", text):
            is_am = True
        elif re.search(r"中午", text):
            hour = 12
            has_explicit_time = True
        elif re.search(r"下班前", text):
            hour = 18
            minute = 0
            has_explicit_time = True

        # 3.2 匹配时间点表达：如 "15:30" / "15点" / "3点半" / "下午3点"
        time_match = re.search(
            r"(?P<h>\d{1,2}|[一二两三四五六七八九十]+)\s*(?:[:点时])\s*(?:(?P<m>\d{1,2}|[一二三四五六七八九十]+)[分]?)?(?P<half>半)?",
            text
        )
        if time_match:
            h_raw = time_match.group("h")
            h_val = cls._parse_cn_number(h_raw)
            if h_val is not None:
                if is_pm and h_val < 12:
                    h_val += 12
                elif is_am and h_val == 12:
                    h_val = 0
                hour = h_val
                has_explicit_time = True

            if time_match.group("half"):
                minute = 30
                has_explicit_time = True
            elif time_match.group("m"):
                m_val = cls._parse_cn_number(time_match.group("m"))
                if m_val is not None and 0 <= m_val < 60:
                    minute = m_val
                    has_explicit_time = True

        # 如果没有识别出任何日期或显式时间词，则未识别到截止时间
        if not has_explicit_date and not has_explicit_time:
            return None

        # 如果识别出了时间点但未提及日期：
        if not target_date:
            target_date = now
            # 若设定的时刻已经过去，且仅说几点（如当前是17点，说3点完成），通常指明天或者当天已过推到明天
            candidate = target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if candidate < now:
                target_date = now + timedelta(days=1)

        result_dt = target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
        return result_dt

    @classmethod
    def clean_title(cls, text: str, max_length: int = 50) -> str:
        """去除 @ 艾特、前后标点与开篇问候称谓，生成适合看板卡片展示的标题"""
        if not text:
            return "未命名任务"
        # 移除 @xxx
        cleaned = re.sub(r"@[\w\u4e00-\u9fa5\s]+", "", text)
        cleaned = cleaned.strip()
        # 移除开篇常见群发称呼：各位同事/大家好/群友/通知等
        cleaned = re.sub(r"^(?:各位同事|各位同学|各位领导|各位|大家好|群内各位|通知[：:])\s*[,，:：、]?\s*", "", cleaned)
        # 移除多余换行与空白
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        # 截断
        if len(cleaned) > max_length:
            return cleaned[:max_length] + "..."
        return cleaned or "待办任务"

    def parse_message(self, text: str, base_time: Optional[datetime] = None) -> Optional[Dict[str, Any]]:
        """
        完整解析一条消息：
        若命中关键词，返回字典包含 title, content, deadline (格式化字符串), matched_keyword
        若未命中，返回 None
        """
        matched, kw = self.matches_keyword(text)
        if not matched:
            return None

        deadline_dt = self.extract_deadline(text, base_time)
        deadline_str = deadline_dt.strftime("%Y-%m-%d %H:%M:%S") if deadline_dt else None
        title = self.clean_title(text)

        return {
            "title": title,
            "content": text.strip(),
            "deadline": deadline_str,
            "matched_keyword": kw
        }
