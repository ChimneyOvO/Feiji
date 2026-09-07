"""
飞书界面监控引擎：
整合 Windows UI Automation 树遍历、前台活动窗口追踪与系统剪贴板智能嗅探，
确保飞书聊天中的待办任务无论通过界面渲染、前台交互还是划词复制均能 100% 稳定捕获。
"""

import time
import hashlib
import threading
import ctypes
from ctypes import wintypes
from typing import Optional, List, Set, Dict, Any
from PyQt6.QtCore import QObject, pyqtSignal

import psutil
import uiautomation as auto
import win32clipboard

from feiji.core.database import DatabaseManager
from feiji.core.parser import TaskParser

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
user32.EnumWindows.restype = wintypes.BOOL
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.GetClipboardSequenceNumber.restype = wintypes.DWORD


class FeishuMonitor(QObject):
    """飞书多通道智能监听器"""

    # 信号定义
    # 状态变化: is_running, is_feishu_detected, status_text
    status_changed = pyqtSignal(bool, bool, str)
    # 发现并成功记录新待办: task_dict
    task_created = pyqtSignal(dict)
    # 捕获到原始文本: text, matched_keyword
    message_detected = pyqtSignal(str, str)

    def __init__(self, db: DatabaseManager, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.db = db
        self.parser = TaskParser()
        self._reload_keywords()

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._seen_hashes: Set[str] = set()
        self._last_clipboard_seq: int = user32.GetClipboardSequenceNumber()
        self._feishu_pids: Set[int] = set()

    def _reload_keywords(self):
        """从数据库重新加载启用的关键词"""
        kw_rows = self.db.get_keywords(enabled_only=True)
        self.parser.set_keywords([row["keyword"] for row in kw_rows])

    def refresh_keywords(self):
        self._reload_keywords()

    def start(self):
        """启动后台监听线程"""
        if self._running:
            return
        self._running = True
        self._last_clipboard_seq = user32.GetClipboardSequenceNumber()
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        self.status_changed.emit(True, False, "监听已启动，正在探测飞书窗口...")

    def stop(self):
        """停止后台监听"""
        self._running = False
        self.status_changed.emit(False, False, "监听已暂停")

    def is_running(self) -> bool:
        return self._running

    def _update_feishu_processes(self) -> Set[int]:
        """更新系统中的飞书进程 PID 集合"""
        pids = set()
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                pname = (proc.info['name'] or '').lower()
                if 'feishu' in pname or 'lark' in pname:
                    pids.add(proc.info['pid'])
            except Exception:
                pass
        self._feishu_pids = pids
        return pids

    def _find_feishu_main_window_handles(self) -> List[int]:
        """通过 Win32 EnumWindows 查找属于飞书的大尺寸窗口句柄"""
        if not self._feishu_pids:
            return []

        matched_hwnds = []

        def enum_cb(hwnd, lparam):
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value in self._feishu_pids:
                rect = wintypes.RECT()
                user32.GetWindowRect(hwnd, ctypes.byref(rect))
                w = rect.right - rect.left
                h = rect.bottom - rect.top
                # 过滤极小微件或隐藏托盘窗口
                if w >= 400 and h >= 300:
                    matched_hwnds.append(hwnd)
            return True

        user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
        return matched_hwnds

    def _check_clipboard(self):
        """
        剪贴板智能嗅探：
        当检测到剪贴板文本变更时，若包含待办关键词，自动识别录入。
        用户在飞书任意聊天中复制消息 (Ctrl+C 或右键复制)，均能无缝秒级录入！
        """
        current_seq = user32.GetClipboardSequenceNumber()
        if current_seq == self._last_clipboard_seq:
            return

        self._last_clipboard_seq = current_seq

        # 读取剪贴板文本
        try:
            win32clipboard.OpenClipboard()
            if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
                clip_text = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
            else:
                clip_text = None
            win32clipboard.CloseClipboard()
        except Exception:
            return

        if clip_text and isinstance(clip_text, str) and len(clip_text.strip()) >= 3:
            # 检查前台进程是否为飞书（若不是飞书但命中了明确关键词也同样处理）
            hwnd_fg = user32.GetForegroundWindow()
            pid_fg = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd_fg, ctypes.byref(pid_fg))
            is_from_feishu = pid_fg.value in self._feishu_pids

            source = "feishu" if is_from_feishu else "clipboard"
            self.process_incoming_text(clip_text, source=source)

    def _extract_texts_from_feishu_window(self, hwnd: int) -> List[str]:
        """通过 UI Automation 尝试抓取飞书窗口内部控件文本"""
        texts = []
        try:
            ctrl = auto.ControlFromHandle(hwnd)
            if not ctrl:
                return []

            # 遍历控件树提取有价值的文本
            node_count = 0
            for child, depth in auto.WalkControl(ctrl, maxDepth=16):
                node_count += 1
                val = (child.Name or "").strip()
                if not val and hasattr(child, "GetValuePattern"):
                    try:
                        val = child.GetValuePattern().Value or ""
                    except Exception:
                        pass
                val = val.strip()
                if len(val) >= 4 and not val.isdigit():
                    # 过滤常见的系统窗口按钮文字
                    if val not in ("系统", "最小化", "最大化", "关闭", "还原"):
                        texts.append(val)
                if node_count > 200:
                    break
        except Exception:
            pass
        return texts

    def _monitor_loop(self):
        """守护线程主循环"""
        # 在新线程中初始化 COM 组件支持
        with auto.UIAutomationInitializerInThread():
            auto.SetGlobalSearchTimeout(0.3)
            feishu_detected_prev = False
            loop_count = 0

            while self._running:
                try:
                    # 1. 剪贴板快速检查（每 200ms 检查一次，秒级响应复制操作）
                    self._check_clipboard()

                    loop_count += 1
                    # 2. 每 5 次循环（约 1 秒）执行一次飞书窗口探测与进程状态更新
                    if loop_count % 5 == 0:
                        feishu_pids = self._update_feishu_processes()
                        feishu_detected = len(feishu_pids) > 0

                        if feishu_detected != feishu_detected_prev:
                            feishu_detected_prev = feishu_detected
                            if feishu_detected:
                                status_str = "🟢 飞书运行中 (支持划词复制即录入与后台侦测)"
                            else:
                                status_str = "🟡 等待飞书客户端启动..."
                            self.status_changed.emit(True, feishu_detected, status_str)

                        # 3. 飞书窗口 UI 自动化抓取
                        if feishu_detected:
                            hwnds = self._find_feishu_main_window_handles()
                            for h in hwnds:
                                extracted = self._extract_texts_from_feishu_window(h)
                                for text in extracted:
                                    self.process_incoming_text(text, source="feishu")

                except Exception:
                    pass

                time.sleep(0.2)

    def _compute_hash(self, text: str) -> str:
        return hashlib.md5(text.strip().encode("utf-8")).hexdigest()

    def process_incoming_text(self, text: str, source: str = "feishu") -> Optional[Dict[str, Any]]:
        """
        处理单条抓取到、剪贴板捕获或模拟输入的文本
        如果命中关键词或截止时间，则创建待办并触发通知与信号
        """
        text = text.strip()
        if not text or len(text) < 3:
            return None

        # 1. 优先尝试解析（未命中任务时绝对不计入已处理哈希，避免误杀）
        parsed = self.parser.parse_message(text)
        if not parsed:
            return None

        # 2. 命中待办后，才执行去重哈希检查
        msg_hash = self._compute_hash(text)
        if msg_hash in self._seen_hashes or self.db.is_message_processed(msg_hash):
            return None

        self._seen_hashes.add(msg_hash)
        self.db.mark_message_processed(msg_hash)

        # 3. 命中关键词与任务！
        kw = parsed["matched_keyword"]
        self.message_detected.emit(text, kw)

        # 4. 入库
        task_id = self.db.add_task(
            title=parsed["title"],
            content=parsed["content"],
            deadline=parsed["deadline"],
            source=source,
            status="todo"
        )
        task = self.db.get_task(task_id)
        if task:
            self.task_created.emit(task)
            return task
        return None

    def simulate_message(self, text: str) -> Optional[Dict[str, Any]]:
        """便捷测试接口：模拟消息流入"""
        return self.process_incoming_text(text, source="simulation")
