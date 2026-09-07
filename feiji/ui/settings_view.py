"""
设置中心：包含关键词管理、提醒强度与频率配置、主题颜色与深浅模式切换、开机自启开关
"""

from typing import Optional, Dict, Any, List
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QGridLayout, QColorDialog
)
from qfluentwidgets import (
    TitleLabel, SubtitleLabel, CaptionLabel, BodyLabel, StrongBodyLabel,
    CardWidget, PushButton, PrimaryPushButton, TransparentToolButton,
    LineEdit, ComboBox, SpinBox, SwitchButton, FluentIcon,
    SmoothScrollArea, InfoBar, InfoBarPosition,
    setTheme, setThemeColor, Theme
)

from feiji.core.database import DatabaseManager
from feiji.core.monitor import FeishuMonitor
from feiji.core.autostart import AutoStartManager


class KeywordItemWidget(QWidget):
    """关键词行微件"""
    toggled = pyqtSignal(int, bool)
    deleted = pyqtSignal(int)

    def __init__(self, kw_id: int, keyword: str, enabled: bool, parent=None):
        super().__init__(parent)
        self.kw_id = kw_id
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        self.label = BodyLabel(keyword, self)
        layout.addWidget(self.label)

        layout.addStretch()

        self.switch = SwitchButton(self)
        self.switch.setChecked(enabled)
        self.switch.checkedChanged.connect(lambda val: self.toggled.emit(self.kw_id, val))
        layout.addWidget(self.switch)

        del_btn = TransparentToolButton(FluentIcon.DELETE, self)
        del_btn.setToolTip("删除此关键词")
        del_btn.clicked.connect(lambda: self.deleted.emit(self.kw_id))
        layout.addWidget(del_btn)


class SettingsView(QWidget):
    """设置中心页面"""

    def __init__(self, db: DatabaseManager, monitor: FeishuMonitor, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.db = db
        self.monitor = monitor
        self._init_ui()
        self._load_settings()

    def _init_ui(self):
        self.setObjectName("settingsView")
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(28, 20, 28, 20)
        main_layout.setSpacing(16)

        # 标题
        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(4)
        title_label = TitleLabel("设置", self)
        sub_label = CaptionLabel("定制关键词、提醒策略、外观与自启动", self)
        sub_label.setStyleSheet("color: #777777;")
        title_vbox.addWidget(title_label)
        title_vbox.addWidget(sub_label)
        main_layout.addLayout(title_vbox)

        # 滚动区域
        self.scroll = SmoothScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(4, 4, 16, 16)
        self.container_layout.setSpacing(20)

        # 1. 关键词设置卡片
        self._build_keywords_section()

        # 2. 提醒强度与频率卡片
        self._build_reminders_section()

        # 3. 主题颜色与深浅模式卡片
        self._build_appearance_section()

        # 4. 系统集成卡片（开机自启等）
        self._build_system_section()

        self.scroll.setWidget(self.container)
        main_layout.addWidget(self.scroll)

    def _build_keywords_section(self):
        card = CardWidget(self.container)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 16, 20, 16)
        card_layout.setSpacing(12)

        card_layout.addWidget(SubtitleLabel("待办触发关键词", card))
        desc = CaptionLabel("当飞书聊天中出现以下关键词时，飞记将自动捕获并存入待办看板。", card)
        desc.setStyleSheet("color: #888888;")
        card_layout.addWidget(desc)

        # 添加新关键词行
        add_layout = QHBoxLayout()
        self.new_kw_edit = LineEdit(card)
        self.new_kw_edit.setPlaceholderText("输入新关键词，如：尽快安排、核对...")
        add_btn = PrimaryPushButton(FluentIcon.ADD, "添加关键词", card)
        add_btn.clicked.connect(self._add_keyword)
        self.new_kw_edit.returnPressed.connect(self._add_keyword)

        add_layout.addWidget(self.new_kw_edit)
        add_layout.addWidget(add_btn)
        card_layout.addLayout(add_layout)

        # 关键词列表容器
        self.kw_list_container = QWidget(card)
        self.kw_list_layout = QVBoxLayout(self.kw_list_container)
        self.kw_list_layout.setContentsMargins(0, 8, 0, 0)
        self.kw_list_layout.setSpacing(6)
        card_layout.addWidget(self.kw_list_container)

        self.container_layout.addWidget(card)

    def _build_reminders_section(self):
        card = CardWidget(self.container)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 16, 20, 16)
        card_layout.setSpacing(16)

        card_layout.addWidget(SubtitleLabel("提醒强度与频率", card))
        desc = CaptionLabel("设定任务临近截止与超时后的提醒策略。", card)
        desc.setStyleSheet("color: #888888;")
        card_layout.addWidget(desc)

        # 提醒强度模式
        intensity_layout = QHBoxLayout()
        intensity_layout.addWidget(BodyLabel("提醒强度模式", card))
        intensity_layout.addStretch()

        self.intensity_combo = ComboBox(card)
        self.intensity_combo.addItem("轻度（仅在到期时提醒一次）", userData="light")
        self.intensity_combo.addItem("中度（提前预警 + 到期提醒）", userData="medium")
        self.intensity_combo.addItem("强力催促（提前 + 到期 + 超时循环催促）", userData="strong")
        self.intensity_combo.currentIndexChanged.connect(self._save_reminder_settings)
        intensity_layout.addWidget(self.intensity_combo)
        card_layout.addLayout(intensity_layout)

        # 提前预警分钟
        advance_layout = QHBoxLayout()
        advance_layout.addWidget(BodyLabel("提前预警时间（分钟）", card))
        advance_layout.addStretch()

        self.advance_spin = SpinBox(card)
        self.advance_spin.setRange(1, 120)
        self.advance_spin.setValue(15)
        self.advance_spin.valueChanged.connect(self._save_reminder_settings)
        advance_layout.addWidget(self.advance_spin)
        card_layout.addLayout(advance_layout)

        # 循环催促间隔
        repeat_layout = QHBoxLayout()
        repeat_layout.addWidget(BodyLabel("强力催促循环间隔（分钟）", card))
        repeat_layout.addStretch()

        self.repeat_spin = SpinBox(card)
        self.repeat_spin.setRange(1, 60)
        self.repeat_spin.setValue(10)
        self.repeat_spin.valueChanged.connect(self._save_reminder_settings)
        repeat_layout.addWidget(self.repeat_spin)
        card_layout.addLayout(repeat_layout)

        self.container_layout.addWidget(card)

    def _build_appearance_section(self):
        card = CardWidget(self.container)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 16, 20, 16)
        card_layout.setSpacing(16)

        card_layout.addWidget(SubtitleLabel("外观与主题", card))
        desc = CaptionLabel("切换深色/浅色显示模式与主题强调色。", card)
        desc.setStyleSheet("color: #888888;")
        card_layout.addWidget(desc)

        # 模式切换
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(BodyLabel("应用主题模式", card))
        mode_layout.addStretch()

        self.theme_combo = ComboBox(card)
        self.theme_combo.addItem("跟随系统", userData="Auto")
        self.theme_combo.addItem("浅色模式", userData="Light")
        self.theme_combo.addItem("深色模式", userData="Dark")
        self.theme_combo.currentIndexChanged.connect(self._on_theme_mode_changed)
        mode_layout.addWidget(self.theme_combo)
        card_layout.addLayout(mode_layout)

        # 强调色选择
        color_layout = QHBoxLayout()
        color_layout.addWidget(BodyLabel("主题强调色", card))
        color_layout.addStretch()

        preset_colors = [
            ("经典蓝", "#0078D4"),
            ("极光紫", "#6B69D6"),
            ("松柏绿", "#008272"),
            ("朱砂红", "#D13438"),
            ("珊瑚橙", "#D83B01")
        ]

        self.color_combo = ComboBox(card)
        for name, hex_val in preset_colors:
            self.color_combo.addItem(name, userData=hex_val)

        self.color_combo.currentIndexChanged.connect(self._on_theme_color_changed)
        color_layout.addWidget(self.color_combo)
        card_layout.addLayout(color_layout)

        self.container_layout.addWidget(card)

    def _build_system_section(self):
        card = CardWidget(self.container)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 16, 20, 16)
        card_layout.setSpacing(16)

        card_layout.addWidget(SubtitleLabel("系统与监控", card))
        desc = CaptionLabel("配置 Windows 系统联动与性能参数。", card)
        desc.setStyleSheet("color: #888888;")
        card_layout.addWidget(desc)

        # 开机自启
        autostart_layout = QHBoxLayout()
        autostart_layout.addWidget(BodyLabel("开机自动启动", card))
        autostart_layout.addStretch()

        self.autostart_switch = SwitchButton(card)
        self.autostart_switch.setChecked(AutoStartManager.is_autostart_enabled())
        self.autostart_switch.checkedChanged.connect(self._on_autostart_changed)
        autostart_layout.addWidget(self.autostart_switch)
        card_layout.addLayout(autostart_layout)

        # 飞书监控轮询间隔
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(BodyLabel("飞书窗口采样间隔（秒）", card))
        interval_layout.addStretch()

        self.interval_spin = SpinBox(card)
        self.interval_spin.setRange(1, 10)
        self.interval_spin.setValue(2)
        self.interval_spin.valueChanged.connect(self._on_interval_changed)
        interval_layout.addWidget(self.interval_spin)
        card_layout.addLayout(interval_layout)

        self.container_layout.addWidget(card)

    # ---------------- 业务逻辑 ----------------

    def _load_settings(self):
        self._refresh_keywords_list()

        settings = self.db.get_all_settings()

        # 强度
        intensity = settings.get("reminder_intensity", "medium")
        idx = {"light": 0, "medium": 1, "strong": 2}.get(intensity, 1)
        self.intensity_combo.setCurrentIndex(idx)

        # 提前分钟
        try:
            adv = int(settings.get("reminder_advance_minutes", "15"))
            self.advance_spin.setValue(adv)
        except ValueError:
            pass

        # 循环分钟
        try:
            rep = int(settings.get("reminder_repeat_minutes", "10"))
            self.repeat_spin.setValue(rep)
        except ValueError:
            pass

        # 主题
        mode = settings.get("theme_mode", "Auto")
        mode_idx = {"Auto": 0, "Light": 1, "Dark": 2}.get(mode, 0)
        self.theme_combo.setCurrentIndex(mode_idx)

        # 采样间隔
        try:
            sec = int(settings.get("monitor_interval_sec", "2"))
            self.interval_spin.setValue(sec)
        except ValueError:
            pass

    def _refresh_keywords_list(self):
        # 清空现有子项
        while self.kw_list_layout.count():
            item = self.kw_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        keywords = self.db.get_keywords(enabled_only=False)
        for kw in keywords:
            w = KeywordItemWidget(kw["id"], kw["keyword"], bool(kw["enabled"]), self.kw_list_container)
            w.toggled.connect(self._on_kw_toggled)
            w.deleted.connect(self._on_kw_deleted)
            self.kw_list_layout.addWidget(w)

    def _add_keyword(self):
        text = self.new_kw_edit.text().strip()
        if not text:
            return
        if self.db.add_keyword(text):
            self.new_kw_edit.clear()
            self._refresh_keywords_list()
            self.monitor.refresh_keywords()
            InfoBar.success("添加成功", f"已新增关键词：{text}", parent=self.window(), duration=1500)
        else:
            InfoBar.warning("无法添加", "关键词已存在或无效", parent=self.window(), duration=2000)

    def _on_kw_toggled(self, kw_id: int, enabled: bool):
        self.db.toggle_keyword(kw_id, enabled)
        self.monitor.refresh_keywords()

    def _on_kw_deleted(self, kw_id: int):
        self.db.remove_keyword(kw_id)
        self._refresh_keywords_list()
        self.monitor.refresh_keywords()

    def _save_reminder_settings(self):
        intensity = self.intensity_combo.currentData()
        adv = str(self.advance_spin.value())
        rep = str(self.repeat_spin.value())
        self.db.set_setting("reminder_intensity", intensity)
        self.db.set_setting("reminder_advance_minutes", adv)
        self.db.set_setting("reminder_repeat_minutes", rep)

    def _on_theme_mode_changed(self):
        mode = self.theme_combo.currentData()
        self.db.set_setting("theme_mode", mode)
        if mode == "Light":
            setTheme(Theme.LIGHT)
        elif mode == "Dark":
            setTheme(Theme.DARK)
        else:
            setTheme(Theme.AUTO)

    def _on_theme_color_changed(self):
        hex_color = self.color_combo.currentData()
        if hex_color:
            self.db.set_setting("theme_color", hex_color)
            setThemeColor(hex_color)

    def _on_autostart_changed(self, enabled: bool):
        success = AutoStartManager.set_autostart(enabled)
        if success:
            self.db.set_setting("autostart", "1" if enabled else "0")
            msg = "已开启开机自启动" if enabled else "已关闭开机自启动"
            InfoBar.success("设置成功", msg, parent=self.window(), duration=2000)
        else:
            self.autostart_switch.setChecked(not enabled)
            InfoBar.error("设置失败", "无法修改 Windows 开机启动注册表", parent=self.window(), duration=3000)

    def _on_interval_changed(self, val: int):
        self.db.set_setting("monitor_interval_sec", str(val))
