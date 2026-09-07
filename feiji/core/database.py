"""
数据库管理模块：基于 SQLite3 管理待办任务、关键词库与应用配置
"""

import sqlite3
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

DEFAULT_DB_PATH = os.path.join(os.path.expanduser("~"), ".feiji", "feiji.db")

DEFAULT_KEYWORDS = [
    "完成", "需要", "请", "提交", "更新", "收集", "整理", "汇总", "统计", "核对",
    "发我", "发群里", "安排", "处理", "帮忙", "辛苦", "麻烦", "TODO", "待办",
    "记得", "跟进", "截止", "截至", "排期", "查收", "准备", "同步"
]

DEFAULT_SETTINGS = {
    "reminder_intensity": "medium",       # light: 仅到期; medium: 提前+到期; strong: 循环催促
    "reminder_advance_minutes": "15",     # 提前预警分钟
    "reminder_repeat_minutes": "10",      # 循环提醒间隔（分钟）
    "theme_mode": "Auto",                 # Light, Dark, Auto
    "theme_color": "#0078D4",             # 默认 Fluent 蓝
    "autostart": "0",                     # 开机自启开关 (0/1)
    "monitor_enabled": "1",               # 飞书监控启停开关
    "monitor_interval_sec": "2"           # 监控轮询间隔（秒）
}


from contextlib import contextmanager


class DatabaseManager:
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        if self.db_path != ":memory:":
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # 任务表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    content TEXT,
                    status TEXT NOT NULL DEFAULT 'todo',
                    deadline TEXT,
                    source TEXT DEFAULT 'feishu',
                    reminded INTEGER DEFAULT 0,
                    last_reminded_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # 关键词表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS keywords (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    keyword TEXT UNIQUE NOT NULL,
                    enabled INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL
                )
            """)

            # 设置表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)

            # 已处理消息哈希表（防止抓取重复录入）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS processed_messages (
                    msg_hash TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL
                )
            """)

            conn.commit()

        # 写入默认数据
        self._init_defaults()

    def _init_defaults(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # 默认关键词
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for kw in DEFAULT_KEYWORDS:
                cursor.execute("""
                    INSERT OR IGNORE INTO keywords (keyword, enabled, created_at)
                    VALUES (?, 1, ?)
                """, (kw, now_str))

            # 默认设置
            for k, v in DEFAULT_SETTINGS.items():
                cursor.execute("""
                    INSERT OR IGNORE INTO settings (key, value)
                    VALUES (?, ?)
                """, (k, v))

            # 首次运行写入初始示例引导任务
            cursor.execute("SELECT count(*) as count FROM tasks")
            if cursor.fetchone()["count"] == 0:
                tomorrow_dt = (datetime.now() + timedelta(days=1)).replace(hour=18, minute=0, second=0)
                tomorrow_str = tomorrow_dt.strftime("%Y-%m-%d %H:%M:%S")

                sample_tasks = [
                    ("欢迎使用飞记待办助手！", "点击右上方【编辑】可调整内容。飞记会后台观察飞书对话并自动生成待办卡片。", "todo", tomorrow_str, "manual"),
                    ("飞书对话体验：尝试在聊天中包含关键词和时间", "例如：【辛苦明天下午3点前帮忙汇总数据】，飞记将自动捕获并设定到期提醒。", "in_progress", tomorrow_str, "feishu"),
                    ("熟悉看板状态流转操作", "点击卡片底部的【开始】或【完成】可快捷推进待办进度。", "done", None, "manual")
                ]
                for title, content, status, deadline, source in sample_tasks:
                    cursor.execute("""
                        INSERT INTO tasks (title, content, status, deadline, source, reminded, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, 0, ?, ?)
                    """, (title, content, status, deadline, source, now_str, now_str))

            conn.commit()

    # ---------------- 任务 CRUD ----------------

    def add_task(self, title: str, content: str = "", deadline: Optional[str] = None,
                 source: str = "feishu", status: str = "todo") -> int:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO tasks (title, content, status, deadline, source, reminded, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 0, ?, ?)
            """, (title, content, status, deadline, source, now_str, now_str))
            conn.commit()
            return cursor.lastrowid

    def update_task_status(self, task_id: int, status: str) -> bool:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?
            """, (status, now_str, task_id))
            conn.commit()
            return cursor.rowcount > 0

    def update_task(self, task_id: int, title: str, content: str, deadline: Optional[str], status: str) -> bool:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE tasks 
                SET title = ?, content = ?, deadline = ?, status = ?, updated_at = ?
                WHERE id = ?
            """, (title, content, deadline, status, now_str, task_id))
            conn.commit()
            return cursor.rowcount > 0

    def delete_task(self, task_id: int) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            conn.commit()
            return cursor.rowcount > 0

    def get_task(self, task_id: int) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_tasks(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if status:
                cursor.execute("SELECT * FROM tasks WHERE status = ? ORDER BY created_at DESC", (status,))
            else:
                cursor.execute("SELECT * FROM tasks ORDER BY created_at DESC")
            return [dict(row) for row in cursor.fetchall()]

    def get_pending_reminders(self) -> List[Dict[str, Any]]:
        """获取尚未完成且有截止时间的任务"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM tasks 
                WHERE status != 'done' AND deadline IS NOT NULL AND deadline != ''
                ORDER BY deadline ASC
            """)
            return [dict(row) for row in cursor.fetchall()]

    def mark_reminded(self, task_id: int, reminded_state: int = 1):
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE tasks SET reminded = ?, last_reminded_at = ? WHERE id = ?
            """, (reminded_state, now_str, task_id))
            conn.commit()

    def get_task_statistics(self) -> Dict[str, int]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status, count(*) as count FROM tasks GROUP BY status")
            stats = {"todo": 0, "in_progress": 0, "done": 0, "total": 0}
            for row in cursor.fetchall():
                status = row["status"]
                if status in stats:
                    stats[status] = row["count"]
            stats["total"] = stats["todo"] + stats["in_progress"] + stats["done"]
            return stats

    # ---------------- 关键词管理 ----------------

    def get_keywords(self, enabled_only: bool = True) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if enabled_only:
                cursor.execute("SELECT * FROM keywords WHERE enabled = 1 ORDER BY id ASC")
            else:
                cursor.execute("SELECT * FROM keywords ORDER BY id ASC")
            return [dict(row) for row in cursor.fetchall()]

    def add_keyword(self, keyword: str) -> bool:
        kw = keyword.strip()
        if not kw:
            return False
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO keywords (keyword, enabled, created_at)
                    VALUES (?, 1, ?)
                """, (kw, now_str))
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False

    def remove_keyword(self, keyword_id: int) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM keywords WHERE id = ?", (keyword_id,))
            conn.commit()
            return cursor.rowcount > 0

    def toggle_keyword(self, keyword_id: int, enabled: bool) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE keywords SET enabled = ? WHERE id = ?", (1 if enabled else 0, keyword_id))
            conn.commit()
            return cursor.rowcount > 0

    # ---------------- 消息去重 ----------------

    def is_message_processed(self, msg_hash: str) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM processed_messages WHERE msg_hash = ?", (msg_hash,))
            return cursor.fetchone() is not None

    def mark_message_processed(self, msg_hash: str):
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO processed_messages (msg_hash, created_at) VALUES (?, ?)", (msg_hash, now_str))
            conn.commit()

    # ---------------- 设置项 ----------------

    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row:
                return row["value"]
            return default if default is not None else DEFAULT_SETTINGS.get(key)

    def set_setting(self, key: str, value: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO settings (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """, (key, str(value)))
            conn.commit()

    def get_all_settings(self) -> Dict[str, str]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM settings")
            res = {**DEFAULT_SETTINGS}
            for row in cursor.fetchall():
                res[row["key"]] = row["value"]
            return res
