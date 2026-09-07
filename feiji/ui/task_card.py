"""
任务卡片组件：展示单个待办的标题、原对话、截止时间倒计时与状态流转操作
"""

from datetime import datetime
from typing import Dict, Any, Optional
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from qfluentwidgets import (
    CardWidget, BodyLabel, CaptionLabel, StrongBodyLabel,
    TransparentToolButton, PushButton, PrimaryPushButton,
    FluentIcon, InfoBadge
)


class TaskCard(CardWidget):
    """看板中的单项任务卡片"""

    status_change_requested = pyqtSignal(int, str)  # task_id, new_status
    edit_requested = pyqtSignal(dict)               # task_dict
    delete_requested = pyqtSignal(int)             # task_id

    def __init__(self, task: Dict[str, Any], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.task = task
        self.task_id = task["id"]
        self.status = task.get("status", "todo")
        self._init_ui()

    def _init_ui(self):
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        # 1. 顶部栏：来源标识与删除/编辑按钮
        top_layout = QHBoxLayout()
        top_layout.setSpacing(6)

        source_text = "飞书捕获" if self.task.get("source") == "feishu" else (
            "模拟测试" if self.task.get("source") == "simulation" else "手动创建"
        )
        source_label = CaptionLabel(source_text, self)
        source_label.setStyleSheet("color: #0078D4; font-weight: bold; background: rgba(0, 120, 212, 0.1); padding: 2px 6px; border-radius: 4px;")
        top_layout.addWidget(source_label)

        top_layout.addStretch()

        # 编辑与删除按钮
        edit_btn = TransparentToolButton(FluentIcon.EDIT, self)
        edit_btn.setToolTip("编辑任务")
        edit_btn.clicked.connect(lambda: self.edit_requested.emit(self.task))
        top_layout.addWidget(edit_btn)

        del_btn = TransparentToolButton(FluentIcon.DELETE, self)
        del_btn.setToolTip("删除任务")
        del_btn.clicked.connect(lambda: self.delete_requested.emit(self.task_id))
        top_layout.addWidget(del_btn)

        layout.addLayout(top_layout)

        # 2. 标题
        title_label = StrongBodyLabel(self.task.get("title", "未命名任务"), self)
        title_label.setWordWrap(True)
        layout.addWidget(title_label)

        # 3. 原始聊天内容片段（若有）
        content = self.task.get("content", "").strip()
        if content and content != self.task.get("title"):
            content_preview = content if len(content) <= 80 else content[:77] + "..."
            content_label = CaptionLabel(content_preview, self)
            content_label.setWordWrap(True)
            content_label.setToolTip(f"完整原对话：\n{content}")
            content_label.setStyleSheet("color: #707070;")
            layout.addWidget(content_label)

        # 4. 截止时间与状态徽章
        deadline_layout = QHBoxLayout()
        deadline_str = self.task.get("deadline")
        deadline_badge = self._create_deadline_badge(deadline_str)
        deadline_layout.addWidget(deadline_badge)
        deadline_layout.addStretch()
        layout.addLayout(deadline_layout)

        # 5. 底部流转按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        if self.status == "todo":
            progress_btn = PushButton(FluentIcon.PLAY, "开始", self)
            progress_btn.clicked.connect(lambda: self.status_change_requested.emit(self.task_id, "in_progress"))
            done_btn = PrimaryPushButton(FluentIcon.COMPLETED, "完成", self)
            done_btn.clicked.connect(lambda: self.status_change_requested.emit(self.task_id, "done"))
            btn_layout.addWidget(progress_btn)
            btn_layout.addWidget(done_btn)

        elif self.status == "in_progress":
            back_btn = PushButton(FluentIcon.SYNC, "放回待办", self)
            back_btn.clicked.connect(lambda: self.status_change_requested.emit(self.task_id, "todo"))
            done_btn = PrimaryPushButton(FluentIcon.COMPLETED, "完成", self)
            done_btn.clicked.connect(lambda: self.status_change_requested.emit(self.task_id, "done"))
            btn_layout.addWidget(back_btn)
            btn_layout.addWidget(done_btn)

        elif self.status == "done":
            reopen_btn = PushButton(FluentIcon.ROTATE, "重新打开", self)
            reopen_btn.clicked.connect(lambda: self.status_change_requested.emit(self.task_id, "todo"))
            btn_layout.addWidget(reopen_btn)

        layout.addLayout(btn_layout)

    def _create_deadline_badge(self, deadline_str: Optional[str]) -> QWidget:
        """根据截止时间生成倒计时与颜色高亮标签"""
        if not deadline_str:
            badge = CaptionLabel("无截止时间", self)
            badge.setStyleSheet("color: #888888;")
            return badge

        try:
            deadline = datetime.strptime(deadline_str, "%Y-%m-%d %H:%M:%S")
            now = datetime.now()
            diff_sec = (deadline - now).total_seconds()

            if self.status == "done":
                text = f"截止: {deadline.strftime('%m-%d %H:%M')}"
                badge = CaptionLabel(text, self)
                badge.setStyleSheet("color: #107C41; background: rgba(16, 124, 65, 0.1); padding: 2px 6px; border-radius: 4px;")
                return badge

            if diff_sec < 0:
                overdue_hours = int(abs(diff_sec) // 3600)
                if overdue_hours > 24:
                    text = f"已超时 {int(overdue_hours // 24)} 天"
                else:
                    text = f"已超时 {max(1, overdue_hours)} 小时"
                badge = CaptionLabel(f"⏰ {text} ({deadline.strftime('%m-%d %H:%M')})", self)
                badge.setStyleSheet("color: #D13438; font-weight: bold; background: rgba(209, 52, 56, 0.15); padding: 2px 8px; border-radius: 4px;")
                return badge

            elif diff_sec <= 24 * 3600:
                hours_left = max(1, int(diff_sec // 3600))
                text = f"⏰ 剩余 {hours_left} 小时 ({deadline.strftime('%H:%M')})"
                badge = CaptionLabel(text, self)
                badge.setStyleSheet("color: #D83B01; font-weight: bold; background: rgba(216, 59, 1, 0.15); padding: 2px 8px; border-radius: 4px;")
                return badge

            else:
                text = f"📅 截止: {deadline.strftime('%m-%d %H:%M')}"
                badge = CaptionLabel(text, self)
                badge.setStyleSheet("color: #555555; background: rgba(0, 0, 0, 0.05); padding: 2px 6px; border-radius: 4px;")
                return badge

        except ValueError:
            badge = CaptionLabel(f"截止: {deadline_str}", self)
            return badge
