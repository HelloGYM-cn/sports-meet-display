"""
运动会大屏全屏窗口
Screen Window

Author:  HelloGYM
Version: 1.0.0
License: CC BY-NC 4.0
"""

import sys
import os
import ctypes
import atexit
import signal
import tempfile
import time
import random

from PySide6.QtCore import Qt, QUrl, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineProfile

IS_WINDOWS = sys.platform == "win32"
SENTINEL = os.path.join(tempfile.gettempdir(), "sports_meet_taskbar_hidden")


def hide_taskbar():
    if not IS_WINDOWS:
        return
    try:
        hwnd = ctypes.windll.user32.FindWindowW("Shell_TrayWnd", None)
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)
            try:
                with open(SENTINEL, "w") as f:
                    f.write("1")
            except Exception:
                pass
    except Exception:
        pass


def show_taskbar():
    if not IS_WINDOWS:
        return
    try:
        hwnd = ctypes.windll.user32.FindWindowW("Shell_TrayWnd", None)
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 5)
        if os.path.exists(SENTINEL):
            try:
                os.remove(SENTINEL)
            except Exception:
                pass
    except Exception:
        pass


def check_stale_taskbar():
    if os.path.exists(SENTINEL):
        show_taskbar()


def _restore_all():
    try:
        show_taskbar()
    except Exception:
        pass


def _sig_handler(signum, frame):
    _restore_all()
    sys.exit(0)


atexit.register(_restore_all)
for sig in (signal.SIGINT, signal.SIGTERM):
    try:
        signal.signal(sig, _sig_handler)
    except Exception:
        pass


def _make_cache_bust(url):
    """给 URL 加随机参数，避免缓存"""
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}_v={int(time.time() * 1000)}_{random.randint(1000, 9999)}"


class ScreenWindow(QMainWindow):
    def __init__(self, url: str, screen_index: int = 0,
                 hide_tb: bool = True, on_switch=None):
        super().__init__()

        check_stale_taskbar()

        self.on_switch = on_switch
        self.hide_tb = hide_tb
        self._base_url = url

        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
        )
        self.setCursor(Qt.BlankCursor)

        # 禁用 WebEngine 缓存
        try:
            profile = QWebEngineProfile.defaultProfile()
            profile.setHttpCacheType(QWebEngineProfile.NoCache)
            profile.clearHttpCache()
        except Exception as e:
            print(f"[WebEngine] 清缓存失败: {e}")

        self.view = QWebEngineView()
        self.view.setContextMenuPolicy(Qt.NoContextMenu)
        self.setCentralWidget(self.view)

        # 捕获 JS console
        try:
            self.view.page().javaScriptConsoleMessage = self._on_js_console
        except Exception:
            pass

        # 用随机参数加载
        bust_url = _make_cache_bust(self._base_url)
        print(f"[大屏] 加载 URL: {bust_url}")
        self.view.setUrl(QUrl(bust_url))

        # 加载失败自动重试
        self._retry_count = 0
        self._retry_timer = QTimer(self)
        self._retry_timer.setSingleShot(True)
        self._retry_timer.timeout.connect(self._retry_load)
        self.view.loadFinished.connect(self._on_load_finished)

        screens = QApplication.screens()
        if 0 <= screen_index < len(screens):
            target = screens[screen_index]
        else:
            target = screens[0]
        self.setGeometry(target.geometry())
        self.showFullScreen()

        if self.hide_tb:
            hide_taskbar()

        QShortcut(QKeySequence("Ctrl+Shift+M"), self, self.switch_to_editor)
        QShortcut(QKeySequence("Ctrl+Shift+Q"), self, self.close)

    def _on_js_console(self, level, message, line, source):
        print(f"[JS] {message}  (line {line})")

    def _on_load_finished(self, ok):
        if ok:
            if self._retry_count > 0:
                print(f"[大屏] 第 {self._retry_count} 次重试成功")
            self._retry_count = 0
            return
        self._retry_count += 1
        print(f"[大屏] 加载失败（第 {self._retry_count} 次），1.5 秒后重试...")
        self._retry_timer.start(1500)

    def _retry_load(self):
        bust_url = _make_cache_bust(self._base_url)
        print(f"[大屏] 重试 URL: {bust_url}")
        self.view.setUrl(QUrl(bust_url))

    def switch_to_editor(self):
        if self.on_switch:
            if self.hide_tb:
                show_taskbar()
            self.hide()
            self.on_switch()

    def show_screen(self):
        if self.hide_tb:
            hide_taskbar()
        self.showFullScreen()
        self.raise_()
        self.activateWindow()

    def keyPressEvent(self, event):
        event.accept()

    def closeEvent(self, event):
        if self.hide_tb:
            show_taskbar()
        event.accept()