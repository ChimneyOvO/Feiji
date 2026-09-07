"""
看板列组件：管理待办、进行中、已完成三个状态列及其任务卡片
"""

from typing import List, Dict, Any, Optional
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
)
from qfluentwidgets import (
    SingleDirectionScrollArea, SubtitleLabel, CaptionLabel,
    InfoBadge, SmoothScrollArea
)
from feiji.ui.task_card import TaskCard


class KanbanColumn(QWidget):
    """单个状态看板列"""

    status_change_requested = pyqtSignal(int, str)
    edit_requested = pyqtSignal(dict)
    delete_requested = pyqtSignal(int)

    def __init__(self, title: str, status_code: str, accent_color: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.title = title
        self.status_code = status_code
        self.accent_color = accent_color
        self._cards: List[TaskCard] = []
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(12)

        # 1. 列标题栏
        header_widget = QWidget(self)
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(6, 4, 6, 4)
        header_layout.setSpacing(8)

        # 颜色标记圆点
        color_dot = QFrame(header_widget)
        color_dot.setFixedSize(10, 10)
        color_dot.setStyleSheet(f"background-color: {self.accent_color}; border-radius: 5px;")
        header_layout.addWidget(color_dot)

        # 标题文本
        title_label = SubtitleLabel(self.title, header_widget)
        header_layout.addWidget(title_label)

        # 任务数量徽章
        self.count_badge = InfoBadge(0, header_widget)
        self.count_badge.setStyleSheet("font-size: 12px; padding: 2px 8px;")
        header_layout.addWidget(self.count_badge)

        header_layout.addStretch()
        main_layout.addWidget(header_widget)

        # 2. 卡片滚动区域
        self.scroll_area = SmoothScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(4, 4, 4, 4)
        self.cards_layout.setSpacing(10)
        self.cards_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # 空状态提示标签
        self.empty_label = CaptionLabel("暂无任务", self.cards_container)
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("color: #999999; padding: 40px 0;")
        self.cards_layout.addWidget(self.empty_label)

        self.scroll_area.setWidget(self.cards_container)
        main_layout.addWidget(self.scroll_area)

    def set_tasks(self, tasks: List[Dict[str, Any]]):
        """重新加载当前列的所有任务卡片"""
        # 清理已有卡片
        for card in self._cards:
            self.cards_layout.removeWidget(card)
            card.deleteLater()
        self._cards.clear()

        # 更新数量
        count = len(tasks)
        self.count_badge.setText(str(count))

        if count == 0:
            self.empty_label.show()
        else:
            self.empty_label.hide()
            for task in tasks:
                card = TaskCard(task, self.cards_container)
                card.status_change_requested.connect(self.status_change_requested)
                card.edit_requested.connect(self.edit_requested)
                card.delete_requested.connect(self.delete_requested)
                self.cards_layout.addWidget(card)
                self._cards.append(card)
