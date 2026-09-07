"""
任务看板主页面：展示统计进度条、三列看板流转、快速检索、飞书监控状态与模拟测试入口
"""

from typing import Optional, Dict, Any, List
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QFrame
)
from qfluentwidgets import (
    TitleLabel, SubtitleLabel, CaptionLabel, BodyLabel,
    PrimaryPushButton, PushButton, SearchLineEdit, ProgressBar,
    InfoBar, InfoBarPosition, FluentIcon, InfoBadge, MessageBox,
    Dialog
)

from feiji.core.database import DatabaseManager
from feiji.core.monitor import FeishuMonitor
from feiji.ui.kanban_column import KanbanColumn
from feiji.ui.task_dialog import TaskEditDialog


class BoardView(QWidget):
    """任务看板视图"""

    # 信号
    task_updated = pyqtSignal()

    def __init__(self, db: DatabaseManager, monitor: FeishuMonitor, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.db = db
        self.monitor = monitor
        self.search_filter = ""
        self._init_ui()
        self._connect_signals()
        self.refresh_board()

    def _init_ui(self):
        self.setObjectName("boardView")
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(28, 20, 28, 20)
        main_layout.setSpacing(16)

        # 1. 顶部标题与监控状态栏
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(4)
        title_label = TitleLabel("任务看板", self)
        self.subtitle_label = CaptionLabel("实时同步飞书聊天中的待办与截止时间", self)
        self.subtitle_label.setStyleSheet("color: #777777;")
        title_vbox.addWidget(title_label)
        title_vbox.addWidget(self.subtitle_label)
        header_layout.addLayout(title_vbox)

        header_layout.addStretch()

        # 飞书监听状态按钮
        self.monitor_btn = PushButton(FluentIcon.RINGER, "飞书监听中", self)
        self.monitor_btn.clicked.connect(self._toggle_monitor)
        header_layout.addWidget(self.monitor_btn)

        # 模拟飞书消息测试按钮
        sim_btn = PushButton(FluentIcon.CHAT, "模拟飞书消息", self)
        sim_btn.clicked.connect(self._open_sim_dialog)
        header_layout.addWidget(sim_btn)

        # 新建待办按钮
        new_task_btn = PrimaryPushButton(FluentIcon.ADD, "新建待办", self)
        new_task_btn.clicked.connect(self._open_add_dialog)
        header_layout.addWidget(new_task_btn)

        main_layout.addLayout(header_layout)

        # 2. 进度条与搜索栏
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setSpacing(16)

        # 进度统计小部件
        progress_widget = QWidget(self)
        progress_layout = QVBoxLayout(progress_widget)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(4)

        self.progress_text = CaptionLabel("完成进度: 0 / 0 (0%)", progress_widget)
        self.progress_bar = ProgressBar(progress_widget)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setMinimumWidth(260)

        progress_layout.addWidget(self.progress_text)
        progress_layout.addWidget(self.progress_bar)
        toolbar_layout.addWidget(progress_widget)

        toolbar_layout.addStretch()

        # 搜索过滤框
        self.search_edit = SearchLineEdit(self)
        self.search_edit.setPlaceholderText("搜索任务标题或原文...")
        self.search_edit.setFixedWidth(240)
        self.search_edit.textChanged.connect(self._on_search_changed)
        toolbar_layout.addWidget(self.search_edit)

        main_layout.addLayout(toolbar_layout)

        # 分割线
        line = QFrame(self)
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: rgba(0, 0, 0, 0.08); max-height: 1px;")
        main_layout.addWidget(line)

        # 飞书快捷捕获提示栏
        tip_frame = QFrame(self)
        tip_frame.setStyleSheet("background-color: rgba(0, 120, 212, 0.08); border: 1px solid rgba(0, 120, 212, 0.2); border-radius: 6px;")
        tip_layout = QHBoxLayout(tip_frame)
        tip_layout.setContentsMargins(10, 6, 10, 6)
        tip_label = CaptionLabel("💡 飞书待办捕获方式：在飞书聊天中只需选中待办消息右键【复制】（或按 Ctrl+C），飞记将立即自动识别关键词与截止时间并直接添加入看板！", tip_frame)
        tip_label.setStyleSheet("color: #005A9E; font-size: 12px; font-weight: 500;")
        tip_layout.addWidget(tip_label)
        main_layout.addWidget(tip_frame)

        # 3. 三列看板
        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(16)

        self.col_todo = KanbanColumn("待处理", "todo", "#0078D4", self)
        self.col_progress = KanbanColumn("进行中", "in_progress", "#D83B01", self)
        self.col_done = KanbanColumn("已完成", "done", "#107C41", self)

        columns_layout.addWidget(self.col_todo)
        columns_layout.addWidget(self.col_progress)
        columns_layout.addWidget(self.col_done)

        main_layout.addLayout(columns_layout)

    def _connect_signals(self):
        for col in (self.col_todo, self.col_progress, self.col_done):
            col.status_change_requested.connect(self._on_status_change)
            col.edit_requested.connect(self._open_edit_dialog)
            col.delete_requested.connect(self._on_delete_task)

        # 监控器事件
        self.monitor.task_created.connect(self._on_task_captured)
        self.monitor.status_changed.connect(self._on_monitor_status_changed)

    def refresh_board(self):
        """重新读取数据库并渲染看板所有列与进度统计"""
        all_tasks = self.db.get_all_tasks()

        # 搜索过滤
        if self.search_filter:
            q = self.search_filter.lower()
            filtered_tasks = [
                t for t in all_tasks
                if q in t.get("title", "").lower() or q in t.get("content", "").lower()
            ]
        else:
            filtered_tasks = all_tasks

        todo_tasks = [t for t in filtered_tasks if t.get("status") == "todo"]
        prog_tasks = [t for t in filtered_tasks if t.get("status") == "in_progress"]
        done_tasks = [t for t in filtered_tasks if t.get("status") == "done"]

        self.col_todo.set_tasks(todo_tasks)
        self.col_progress.set_tasks(prog_tasks)
        self.col_done.set_tasks(done_tasks)

        # 更新进度
        total = len(all_tasks)
        done_count = sum(1 for t in all_tasks if t.get("status") == "done")
        percent = int(done_count / total * 100) if total > 0 else 0

        self.progress_bar.setValue(percent)
        self.progress_text.setText(f"完成进度: {done_count} / {total} 项 ({percent}%)")

        self.task_updated.emit()

    def _on_search_changed(self, text: str):
        self.search_filter = text.strip()
        self.refresh_board()

    def _on_status_change(self, task_id: int, new_status: str):
        self.db.update_task_status(task_id, new_status)
        self.refresh_board()

    def _open_add_dialog(self):
        dialog = TaskEditDialog(parent=self.window())
        if dialog.exec():
            data = dialog.get_data()
            if data:
                self.db.add_task(
                    title=data["title"],
                    content=data["content"],
                    status=data["status"],
                    deadline=data["deadline"],
                    source="manual"
                )
                self.refresh_board()
                InfoBar.success(
                    title="创建成功",
                    content=f"已添加待办【{data['title']}】",
                    parent=self.window(),
                    position=InfoBarPosition.TOP_RIGHT,
                    duration=2500
                )

    def _open_edit_dialog(self, task: Dict[str, Any]):
        dialog = TaskEditDialog(task=task, parent=self.window())
        if dialog.exec():
            data = dialog.get_data()
            if data:
                self.db.update_task(
                    task_id=task["id"],
                    title=data["title"],
                    content=data["content"],
                    deadline=data["deadline"],
                    status=data["status"]
                )
                self.refresh_board()
                InfoBar.success(
                    title="更新成功",
                    content=f"待办【{data['title']}】已保存",
                    parent=self.window(),
                    position=InfoBarPosition.TOP_RIGHT,
                    duration=2000
                )

    def _on_delete_task(self, task_id: int):
        task = self.db.get_task(task_id)
        task_title = task["title"] if task else "待办"
        msg_box = MessageBox(
            title="确认删除",
            content=f"确定要删除待办【{task_title}】吗？此操作不可撤销。",
            parent=self.window()
        )
        if msg_box.exec():
            self.db.delete_task(task_id)
            self.refresh_board()
            InfoBar.info(
                title="已删除",
                content=f"待办【{task_title}】已移除",
                parent=self.window(),
                position=InfoBarPosition.TOP_RIGHT,
                duration=2000
            )

    def _toggle_monitor(self):
        if self.monitor.is_running():
            self.monitor.stop()
            self.monitor_btn.setText("监听已暂停 (点击启动)")
            self.monitor_btn.setIcon(FluentIcon.PAUSE)
        else:
            self.monitor.start()
            self.monitor_btn.setText("飞书监听中")
            self.monitor_btn.setIcon(FluentIcon.RINGER)

    def _on_monitor_status_changed(self, running: bool, connected: bool, text: str):
        if not running:
            self.monitor_btn.setText("监听已暂停")
            self.monitor_btn.setIcon(FluentIcon.PAUSE)
            self.subtitle_label.setText("飞书界面监听已暂停")
        else:
            if connected:
                self.monitor_btn.setText("飞书在线")
                self.monitor_btn.setIcon(FluentIcon.RINGER)
                self.subtitle_label.setText("🟢 " + text)
            else:
                self.monitor_btn.setText("等待飞书")
                self.monitor_btn.setIcon(FluentIcon.SYNC)
                self.subtitle_label.setText("🟡 " + text)

    def _on_task_captured(self, task: Dict[str, Any]):
        """当飞书监控捕获到新任务时刷新看板并弹窗提示"""
        self.refresh_board()
        deadline_info = f" (截止: {task['deadline']})" if task.get("deadline") else ""
        InfoBar.success(
            title="🎯 捕获新待办",
            content=f"已自动从飞书记录：【{task['title']}】{deadline_info}",
            parent=self.window(),
            position=InfoBarPosition.TOP_RIGHT,
            duration=4000
        )

    def _open_sim_dialog(self):
        """模拟对话输入，便于用户随时测试验证"""
        from qfluentwidgets import LineEdit, MessageBoxBase

        class SimDialog(MessageBoxBase):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.title_label = SubtitleLabel("模拟飞书消息输入", self)
                self.viewLayout.addWidget(self.title_label)

                desc = CaptionLabel("输入一段包含关键词与时间的对话，测试飞记是否能自动捕获并解析：", self)
                desc.setWordWrap(True)
                self.viewLayout.addWidget(desc)

                self.input_edit = LineEdit(self)
                self.input_edit.setPlaceholderText("例如: 辛苦明天下午3点前帮忙整理方案")
                self.input_edit.setText("辛苦明天下午3点前帮忙把项目周报汇总发我")
                self.viewLayout.addWidget(self.input_edit)

                self.yesButton.setText("发送测试")
                self.cancelButton.setText("取消")
                self.widget.setMinimumWidth(460)

        dialog = SimDialog(parent=self.window())
        if dialog.exec():
            sim_text = dialog.input_edit.text().strip()
            if sim_text:
                task = self.monitor.simulate_message(sim_text)
                if not task:
                    InfoBar.warning(
                        title="未识别为待办",
                        content="该消息未命中启用的关键词，或已被处理过。",
                        parent=self.window(),
                        position=InfoBarPosition.TOP_RIGHT,
                        duration=3000
                    )
