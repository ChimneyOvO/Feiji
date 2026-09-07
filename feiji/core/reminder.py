"""
提醒调度管理：根据任务截止时间与提醒强度配置，执行定时预警与到期催促
"""

from datetime import datetime, timedelta
from typing import Callable, Optional, Dict, Any
from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from feiji.core.database import DatabaseManager


class ReminderEngine(QObject):
    """待办提醒引擎"""

    # 信号：通知 UI 或系统托盘发出提醒 (task_dict, reminder_type, reminder_msg)
    reminder_triggered = pyqtSignal(dict, str, str)

    def __init__(self, db: DatabaseManager, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.db = db
        # 轮询定时器，每 15 秒检查一次待办状态
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_reminders)

    def start(self, interval_ms: int = 15000):
        self.timer.start(interval_ms)
        # 启动后立刻执行一次检查
        self.check_reminders()

    def stop(self):
        self.timer.stop()

    def check_reminders(self):
        """遍历待办，判定是否触发提醒"""
        pending_tasks = self.db.get_pending_reminders()
        if not pending_tasks:
            return

        settings = self.db.get_all_settings()
        intensity = settings.get("reminder_intensity", "medium")
        try:
            advance_min = int(settings.get("reminder_advance_minutes", "15"))
        except ValueError:
            advance_min = 15

        try:
            repeat_min = int(settings.get("reminder_repeat_minutes", "10"))
        except ValueError:
            repeat_min = 10

        now = datetime.now()

        for task in pending_tasks:
            deadline_str = task.get("deadline")
            if not deadline_str:
                continue

            try:
                deadline = datetime.strptime(deadline_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue

            diff = (deadline - now).total_seconds()
            reminded = task.get("reminded", 0)
            last_reminded_str = task.get("last_reminded_at")
            last_reminded_at = None
            if last_reminded_str:
                try:
                    last_reminded_at = datetime.strptime(last_reminded_str, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    pass

            # 判定条件
            # 1. 轻度提醒 (light)：仅在到期后提醒一次
            if intensity == "light":
                if diff <= 0 and reminded == 0:
                    msg = f"任务【{task['title']}】已到截止时间！"
                    self.db.mark_reminded(task["id"], reminded_state=1)
                    self.reminder_triggered.emit(task, "due", msg)

            # 2. 中度提醒 (medium)：提前预警 + 到期提醒
            elif intensity == "medium":
                # 提前预警 (0 < diff <= advance_min * 60)
                if 0 < diff <= advance_min * 60 and reminded == 0:
                    mins_left = max(1, int(diff // 60))
                    msg = f"任务【{task['title']}】即将在 {mins_left} 分钟后截止！"
                    self.db.mark_reminded(task["id"], reminded_state=1)
                    self.reminder_triggered.emit(task, "advance", msg)
                # 到期提醒 (diff <= 0 且 状态 < 2)
                elif diff <= 0 and reminded < 2:
                    msg = f"任务【{task['title']}】已到期，请尽快处理！"
                    self.db.mark_reminded(task["id"], reminded_state=2)
                    self.reminder_triggered.emit(task, "due", msg)

            # 3. 强提醒 (strong)：提前预警 + 到期提醒 + 每隔 repeat_min 循环催促
            elif intensity == "strong":
                if 0 < diff <= advance_min * 60 and reminded == 0:
                    mins_left = max(1, int(diff // 60))
                    msg = f"任务【{task['title']}】即将在 {mins_left} 分钟后截止！"
                    self.db.mark_reminded(task["id"], reminded_state=1)
                    self.reminder_triggered.emit(task, "advance", msg)
                elif diff <= 0:
                    should_repeat = False
                    if reminded < 2:
                        should_repeat = True
                    elif last_reminded_at:
                        elapsed = (now - last_reminded_at).total_seconds()
                        if elapsed >= repeat_min * 60:
                            should_repeat = True

                    if should_repeat:
                        overdue_mins = int(abs(diff) // 60)
                        if overdue_mins == 0:
                            msg = f"【加急催促】任务【{task['title']}】已到期！"
                        else:
                            msg = f"【加急催促】任务【{task['title']}】已超时 {overdue_mins} 分钟，仍未完成！"
                        self.db.mark_reminded(task["id"], reminded_state=2)
                        self.reminder_triggered.emit(task, "repeat", msg)
