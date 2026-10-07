"""
运动会大屏成绩展示系统
Sports Meet Display System

Author:  HelloGYM
Version: 1.0.0
License: CC BY-NC 4.0
"""

import sys
import os
import threading
import socket
import subprocess

import uvicorn
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont, QIcon
from PySide6.QtCore import Qt, QTimer

from app import app
from editor import Editor

# Windows 任务栏图标 ID
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "HelloGYM.SportsMeet.Display.1"
        )
    except Exception:
        pass

HOST = "0.0.0.0"
PORT = 8000


def resource_path(rel):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


def run_server():
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")


def find_browser():
    """找系统 Chrome 或 Edge"""
    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


def launch_browser_kiosk(url):
    """用系统 Chrome/Edge 在副屏以 kiosk 模式打开大屏"""
    browser = find_browser()
    if not browser:
        print("[大屏] 找不到 Chrome / Edge，无法启动大屏")
        return None

    # 找副屏位置
    screens = QApplication.screens()
    if len(screens) >= 2:
        geo = screens[1].geometry()
        # Chrome 窗口位置从主屏坐标算，副屏在右侧时 x=主屏宽
        pos_x = screens[0].geometry().width()
        pos_y = 0
        size_w = geo.width()
        size_h = geo.height()
        window_arg = f"--window-position={pos_x},{pos_y} --window-size={size_w},{size_h}"
    else:
        window_arg = "--window-position=0,0"

    args = [
        browser,
        "--kiosk",
        f"--app={url}",
        "--no-first-run",
        "--disable-features=Translate,OptimizationHints",
        "--disable-pinch",
        "--overscroll-history-navigation=0",
        "--disable-session-crashed-bubble",
        "--hide-crash-restore-bubble",
        "--user-data-dir=" + os.path.join(os.environ.get("TEMP", "."), "sports_meet_chrome"),
    ]
    # 副屏定位参数作为额外开关（kiosk 模式下会被忽略，用 window-position 指定副屏）
    args.extend(window_arg.split())

    print(f"[大屏] 启动浏览器 kiosk: {browser}")
    proc = subprocess.Popen(args)
    print(f"[大屏] 浏览器 PID: {proc.pid}")
    return proc


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    ip = get_local_ip()
    print("=" * 60)
    print("  运动会大屏系统")
    print(f"  大屏地址:   http://127.0.0.1:{PORT}/screen")
    print(f"  裁判录入:   http://{ip}:{PORT}/ref")
    print("=" * 60)

    threading.Thread(target=run_server, daemon=True).start()

    qt_app = QApplication(sys.argv)
    qt_app.setFont(QFont("Microsoft YaHei", 10))

    icon_path = resource_path("icon.ico")
    if os.path.exists(icon_path):
        qt_app.setWindowIcon(QIcon(icon_path))

    # 打印显示器信息
    screens = qt_app.screens()
    n = len(screens)
    print(f"检测到 {n} 块显示器")
    for i, s in enumerate(screens):
        g = s.geometry()
        print(f"  [{i}] {s.name()}  {g.width()}x{g.height()}  @({g.x()},{g.y()})")

    holder = {"browser_proc": None}

    def create_windows():
        url = f"http://127.0.0.1:{PORT}/screen"
        holder["browser_proc"] = launch_browser_kiosk(url)
        holder["editor"] = Editor(on_switch=None)
        holder["editor"].showMaximized()

    def cleanup():
        """退出时杀掉 Chrome kiosk"""
        proc = holder.get("browser_proc")
        if proc and proc.poll() is None:
            print(f"[退出] 关闭浏览器 PID={proc.pid}")
            try:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
            except Exception as e:
                print(f"[退出] 关闭失败: {e}")

    qt_app.aboutToQuit.connect(cleanup)

    QTimer.singleShot(6000, create_windows)

    sys.exit(qt_app.exec())


if __name__ == "__main__":
    main()
