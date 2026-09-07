"""
待办新增/编辑弹窗：支持输入标题、对话原文、选择状态与快捷设定截止时间
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from qfluentwidgets import (
    MessageBoxBase, SubtitleLabel, CaptionLabel, BodyLabel,
    LineEdit, TextEdit, ComboBox, PushButton, FluentIcon
)
from feiji.core.parser import TaskParser


class TaskEditDialog(MessageBoxBase):
    """任务编辑与新增弹窗"""

    def __init__(self, task: Optional[Dict[str, Any]] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.task = task or {}
        self.is_edit = bool(task and task.get("id"))
        self._init_ui()

    def _init_ui(self):
        # 弹窗标题
        dialog_title = "编辑待办任务" if self.is_edit else "新建待办任务"
        self.title_label = SubtitleLabel(dialog_title, self)
        self.viewLayout.addWidget(self.title_label)

        # 1. 任务标题输入
        self.viewLayout.addWidget(CaptionLabel("任务标题 *", self))
        self.title_edit = LineEdit(self)
        self.title_edit.setPlaceholderText("请输入简要待办内容...")
        self.title_edit.setText(self.task.get("title", ""))
        self.viewLayout.addWidget(self.title_edit)

        # 2. 原始对话或详细说明
        self.viewLayout.addWidget(CaptionLabel("详细说明 / 对话原文", self))
        self.content_edit = TextEdit(self)
        self.content_edit.setPlaceholderText("输入相关聊天背景或备忘说明（选填）...")
        self.content_edit.setText(self.task.get("content", ""))
        self.content_edit.setFixedHeight(90)
        self.viewLayout.addWidget(self.content_edit)

        # 3. 状态选择
        self.viewLayout.addWidget(CaptionLabel("任务状态", self))
        self.status_combo = ComboBox(self)
        self.status_combo.addItem("待办", userData="todo")
        self.status_combo.addItem("进行中", userData="in_progress")
        self.status_combo.addItem("已完成", userData="done")

        current_status = self.task.get("status", "todo")
        status_index = {"todo": 0, "in_progress": 1, "done": 2}.get(current_status, 0)
        self.status_combo.setCurrentIndex(status_index)
        self.viewLayout.addWidget(self.status_combo)

        # 4. 截止时间与快捷按钮
        self.viewLayout.addWidget(CaptionLabel("截止时间 (格式: YYYY-MM-DD HH:MM:SS)", self))
        self.deadline_edit = LineEdit(self)
        self.deadline_edit.setPlaceholderText("例如: 2026-09-08 18:00:00 (可点击下方快捷键)")
        self.deadline_edit.setText(self.task.get("deadline") or "")
        self.viewLayout.addWidget(self.deadline_edit)

        # 快捷填充按钮行
        quick_btn_layout = QHBoxLayout()
        quick_btn_layout.setSpacing(6)

        btn_today = PushButton("今天下班(18:00)", self)
        btn_today.clicked.connect(lambda: self._set_quick_deadline("今天下班前"))
        quick_btn_layout.addWidget(btn_today)

        btn_tomorrow = PushButton("明天18:00", self)
        btn_tomorrow.clicked.connect(lambda: self._set_quick_deadline("明天18点"))
        quick_btn_layout.addWidget(btn_tomorrow)

        btn_friday = PushButton("本周五18:00", self)
        btn_friday.clicked.connect(lambda: self._set_quick_deadline("周五下班前"))
        quick_btn_layout.addWidget(btn_friday)

        btn_clear = PushButton("清除", self)
        btn_clear.clicked.connect(lambda: self.deadline_edit.clear())
        quick_btn_layout.addWidget(btn_clear)

        self.viewLayout.addLayout(quick_btn_layout)

        # 确认与取消按钮文本
        self.yesButton.setText("保存")
        self.cancelButton.setText("取消")

        self.widget.setMinimumWidth(440)

    def _set_quick_deadline(self, text_expr: str):
        dt = TaskParser.extract_deadline(text_expr)
        if dt:
            self.deadline_edit.setText(dt.strftime("%Y-%m-%d %H:%M:%S"))

    def get_data(self) -> Optional[Dict[str, Any]]:
        """获取验证后的表单数据"""
        title = self.title_edit.text().strip()
        if not title:
            return None
        content = self.content_edit.toPlainText().strip()
        status = self.status_combo.currentData() or "todo"
        deadline = self.deadline_edit.text().strip() or None

        return {
            "title": title,
            "content": content,
            "status": status,
            "deadline": deadline
        }
