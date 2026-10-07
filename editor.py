"""
运动会大屏成绩展示系统
Sports Meet Display System

Author:  HelloGYM
Version: 1.0.0
License: CC BY-NC 4.0
"""

import socket

import requests

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QPushButton, QLineEdit,
    QLabel, QCheckBox, QMessageBox, QHeaderView, QGroupBox,
    QComboBox, QSpinBox, QApplication, QGridLayout, QFileDialog,
    QListWidget, QListWidgetItem, QSplitter
)
from PySide6.QtCore import Qt, QTimer, QThreadPool, QRunnable, QObject, Signal
from PySide6.QtGui import QKeySequence, QShortcut, QPixmap, QPainter, QColor, QFont

BASE = "http://127.0.0.1:8000"

STYLE = """
QMainWindow, QWidget { background: #0a1430; color: #fff; }
QLabel { color: #fff; font-size: 14px; }
QGroupBox {
    border: 1px solid #2a3a6a; margin-top: 12px; padding-top: 12px;
    font-size: 14px; color: #ffd700;
}
QGroupBox::title { left: 12px; padding: 0 6px; }
QLineEdit, QSpinBox, QComboBox {
    background: #0f1c40; color: #fff; border: 1px solid #2a3a6a;
    padding: 8px; border-radius: 4px; font-size: 14px;
}
QComboBox QAbstractItemView {
    background: #0f1c40; color: #fff; selection-background-color: #2a3a6a;
}
QPushButton {
    background: #ffd700; color: #0a1430; font-weight: bold;
    padding: 10px 18px; border: none; border-radius: 4px;
    font-size: 14px;
}
QPushButton:hover { background: #ffe033; }
QPushButton.danger { background: #ff4444; color: #fff; }
QPushButton.danger:hover { background: #ff6666; }
QPushButton.ghost {
    background: transparent; color: #ffd700;
    border: 1px solid #ffd700;
}
QPushButton.ghost:hover { background: rgba(255,215,0,.1); }
QTableWidget, QListWidget {
    background: #0f1c40; color: #fff; gridline-color: #2a3a6a;
    border: 1px solid #2a3a6a; font-size: 14px;
}
QTableWidget::indicator,
QTableView::indicator {
    width: 22px;
    height: 22px;
    border: 2px solid #4a5670;
    border-radius: 4px;
    background: #0f1c40;
}
QTableWidget::indicator:hover,
QTableView::indicator:hover {
    border-color: #ffd700;
}
QTableWidget::indicator:checked,
QTableView::indicator:checked {
    background: #ffd700;
    border-color: #ffd700;
}
QListWidget::item { padding: 8px; }
QListWidget::item:selected { background: #2a3a6a; color: #ffd700; }
QHeaderView::section {
    background: #1a2a5a; color: #ffd700; padding: 10px;
    border: none; font-weight: bold;
}
QCheckBox { color: #fff; }
QSplitter::handle { background: #2a3a6a; }
"""


class Worker(QRunnable):
    class Signals(QObject):
        finished = Signal(object)
        error = Signal(str)

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = Worker.Signals()

    def run(self):
        try:
            result = self.fn(*self.args, **self.kwargs)
            self.signals.finished.emit(result)
        except Exception as e:
            self.signals.error.emit(str(e))


_pool = QThreadPool.globalInstance()


def run_async(fn, on_success=None, on_error=None, *args, **kwargs):
    worker = Worker(fn, *args, **kwargs)
    if on_success:
        worker.signals.finished.connect(on_success)
    if on_error:
        worker.signals.error.connect(on_error)
    _pool.start(worker)


def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


def make_qr_pixmap(text: str, size: int = 160) -> QPixmap:
    try:
        import qrcode
        from io import BytesIO
        img = qrcode.make(text)
        buf = BytesIO()
        img.save(buf, format='PNG')
        pm = QPixmap()
        pm.loadFromData(buf.getvalue())
        return pm.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    except Exception:
        pm = QPixmap(size, size)
        pm.fill(QColor("#0f1c40"))
        p = QPainter(pm)
        p.setPen(QColor("#ffd700"))
        p.setFont(QFont("Microsoft YaHei", 10))
        p.drawText(pm.rect(), Qt.AlignCenter, "pip install\nqrcode[pil]")
        p.end()
        return pm


class Editor(QMainWindow):
    def __init__(self, on_switch=None):
        super().__init__()
        self.on_switch = on_switch
        self.setWindowTitle("运动会大屏控制台 · HelloGYM")
        self.resize(1280, 900)
        self.setStyleSheet(STYLE)

        self.local_ip = get_local_ip()
        self._last_fp = None

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        top = QHBoxLayout()
        top.addWidget(QLabel("当前项目"))
        self.event_input = QLineEdit()
        self.event_input.setPlaceholderText("如：男子100米 决赛")
        top.addWidget(self.event_input, 2)

        top.addWidget(QLabel("下一场"))
        self.next_input = QLineEdit()
        self.next_input.setPlaceholderText("如：女子200米 预赛")
        top.addWidget(self.next_input, 2)

        next_btn = QPushButton("更新预告")
        next_btn.clicked.connect(self.push_next)
        top.addWidget(next_btn)

        back_btn = QPushButton("▶ 回到大屏")
        back_btn.setProperty("class", "ghost")
        back_btn.clicked.connect(self.switch_to_screen)
        top.addWidget(back_btn)
        layout.addLayout(top)

        splitter = QSplitter(Qt.Horizontal)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(QLabel("已保存的项目"))
        self.event_list = QListWidget()
        self.event_list.itemClicked.connect(self.load_event)
        left_layout.addWidget(self.event_list)

        list_btns = QHBoxLayout()
        refresh_btn = QPushButton("刷新列表")
        refresh_btn.clicked.connect(self.refresh_event_list)
        list_btns.addWidget(refresh_btn)

        del_event_btn = QPushButton("删除项目")
        del_event_btn.setProperty("class", "danger")
        del_event_btn.clicked.connect(self.delete_event)
        list_btns.addWidget(del_event_btn)
        left_layout.addLayout(list_btns)

        splitter.addWidget(left)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["名次", "姓名", "单位", "成绩", "破纪录"])
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.Stretch)
        h.setSectionResizeMode(2, QHeaderView.Stretch)
        h.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setDefaultSectionSize(42)
        right_layout.addWidget(self.table)

        btns = QHBoxLayout()
        for text, slot, cls in [
            ("添加一行", self.add_row, ""),
            ("删除选中", self.del_row, ""),
            ("按成绩排序", self.auto_sort, ""),
            ("清空全部", self.clear_all, ""),
            ("导入 Excel", self.import_excel, ""),
            ("推送到大屏", self.push, ""),
        ]:
            b = QPushButton(text)
            b.clicked.connect(slot)
            if cls:
                b.setProperty("class", cls)
            btns.addWidget(b)
        right_layout.addLayout(btns)

        self.accept_remote = QCheckBox("接收裁判提交（实时刷新表格）")
        self.accept_remote.setChecked(True)
        right_layout.addWidget(self.accept_remote)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        layout.addWidget(splitter, 1)

        bottom = QHBoxLayout()

        cfg_box = QGroupBox("大屏配置")
        cfg_layout = QGridLayout(cfg_box)
        cfg_layout.setHorizontalSpacing(10)
        cfg_layout.setVerticalSpacing(8)

        cfg_layout.addWidget(QLabel("运动会名称"), 0, 0)
        self.meet_input = QLineEdit()
        cfg_layout.addWidget(self.meet_input, 0, 1, 1, 3)

        cfg_layout.addWidget(QLabel("主题"), 0, 4)
        self.theme_input = QComboBox()
        self.theme_input.addItems(["olympic", "projector", "led"])
        cfg_layout.addWidget(self.theme_input, 0, 5)

        cfg_layout.addWidget(QLabel("轮播(秒)"), 0, 6)
        self.interval_input = QSpinBox()
        self.interval_input.setRange(3, 60)
        cfg_layout.addWidget(self.interval_input, 0, 7)

        cfg_layout.addWidget(QLabel("字段名"), 1, 0)
        cfg_layout.addWidget(QLabel("名次列"), 1, 1)
        self.lbl_rank = QLineEdit("名次")
        cfg_layout.addWidget(self.lbl_rank, 1, 2)
        cfg_layout.addWidget(QLabel("姓名列"), 1, 3)
        self.lbl_name = QLineEdit("姓名")
        cfg_layout.addWidget(self.lbl_name, 1, 4)
        cfg_layout.addWidget(QLabel("单位列"), 1, 5)
        self.lbl_team = QLineEdit("单位")
        cfg_layout.addWidget(self.lbl_team, 1, 6)
        cfg_layout.addWidget(QLabel("成绩列"), 1, 7)
        self.lbl_score = QLineEdit("成绩")
        cfg_layout.addWidget(self.lbl_score, 1, 8)

        save_btn = QPushButton("保存配置并同步大屏")
        save_btn.clicked.connect(self.save_config)
        cfg_layout.addWidget(save_btn, 2, 0, 1, 9)

        bottom.addWidget(cfg_box, 3)

        qr_box = QGroupBox("手机扫码录入")
        qr_layout = QVBoxLayout(qr_box)
        self.qr_label = QLabel()
        self.qr_label.setAlignment(Qt.AlignCenter)
        qr_layout.addWidget(self.qr_label)

        self.qr_url = QLabel(f"http://{self.local_ip}:8000/ref")
        self.qr_url.setAlignment(Qt.AlignCenter)
        self.qr_url.setStyleSheet("color: #667085; font-size: 11px;")
        self.qr_url.setTextInteractionFlags(Qt.TextSelectableByMouse)
        qr_layout.addWidget(self.qr_url)

        bottom.addWidget(qr_box, 1)
        layout.addLayout(bottom)

        self.hint = QLabel("运动会大屏系统 v1.0  ·   Designed by HelloGYM  ·   Ctrl+Shift+M 切换")
        self.hint.setStyleSheet("color: #4a5670; font-size: 12px; letter-spacing: 0.05em;")
        layout.addWidget(self.hint)

        QShortcut(QKeySequence("Ctrl+Shift+M"), self, self.switch_to_screen)

        self.add_row()

        QTimer.singleShot(800, self.load_config)
        QTimer.singleShot(1200, self.refresh_event_list)
        QTimer.singleShot(1500, self.start_polling)

    # ==================== 轮询 ====================
    def start_polling(self):
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll_once)
        self._poll_timer.start(1500)

    def _poll_once(self):
        if not self.accept_remote.isChecked():
            return
        try:
            r = requests.get(f"{BASE}/api/state", timeout=2)
            s = r.json()
        except Exception:
            return

        event_name = s.get("event", "") or ""
        results = s.get("results", []) or []

        fp = (event_name, len(results),
              results[0].get("name", "") if results else "",
              results[0].get("score", "") if results else "")
        if self._last_fp == fp:
            return
        self._last_fp = fp

        self.refresh_event_list()

        current = self.event_input.text().strip()
        if current and current != event_name:
            return

        self.event_input.setText(event_name)
        self.table.setRowCount(0)
        for r in results:
            self.add_row_from(r)

    # ==================== 配置加载 ====================
    def load_config(self):
        try:
            r = requests.get(f"{BASE}/api/config", timeout=3)
            cfg = r.json()
        except Exception:
            return

        self.meet_input.setText(cfg.get("meetName", ""))
        self.theme_input.setCurrentText(cfg.get("theme", "olympic"))
        self.interval_input.setValue(cfg.get("rotationInterval", 8))

        labels = cfg.get("labels", {})
        self.lbl_rank.setText(labels.get("rank", "名次"))
        self.lbl_name.setText(labels.get("name", "姓名"))
        self.lbl_team.setText(labels.get("team", "单位"))
        self.lbl_score.setText(labels.get("score", "成绩"))
        self.refresh_headers()

        self.update_qr()

    def update_qr(self):
        url = f"http://{self.local_ip}:8000/ref"
        self.qr_url.setText(url)
        self.qr_label.setPixmap(make_qr_pixmap(url, 150))

    def refresh_headers(self):
        self.table.setHorizontalHeaderLabels([
            self.lbl_rank.text().strip() or "名次",
            self.lbl_name.text().strip() or "姓名",
            self.lbl_team.text().strip() or "单位",
            self.lbl_score.text().strip() or "成绩",
            "破纪录",
        ])

    def save_config(self):
        payload = {
            "meetName": self.meet_input.text().strip(),
            "theme": self.theme_input.currentText(),
            "rotationInterval": self.interval_input.value(),
            "labels": {
                "rank":  self.lbl_rank.text().strip()  or "名次",
                "name":  self.lbl_name.text().strip()  or "姓名",
                "team":  self.lbl_team.text().strip()  or "单位",
                "score": self.lbl_score.text().strip() or "成绩",
            },
        }

        def do_post():
            r = requests.post(f"{BASE}/api/config", json=payload, timeout=3)
            r.raise_for_status()
            return True

        def on_ok(_):
            self.refresh_headers()
            QMessageBox.information(self, "成功", "配置已保存")

        def on_err(msg):
            QMessageBox.critical(self, "错误", msg)

        run_async(do_post, on_success=on_ok, on_error=on_err)

    # ==================== 项目列表 ====================
    def refresh_event_list(self):
        try:
            r = requests.get(f"{BASE}/api/events", timeout=3)
            names = r.json()
        except Exception:
            names = []
        self.event_list.clear()
        for n in names:
            self.event_list.addItem(QListWidgetItem(n))

    def load_event(self, item):
        name = item.text()
        try:
            r = requests.get(f"{BASE}/api/event/{name}", timeout=3)
            results = r.json()
        except Exception:
            QMessageBox.critical(self, "错误", "加载项目失败")
            return

        self.event_input.setText(name)
        self.table.setRowCount(0)
        for r in results:
            self.add_row_from(r)

    def _make_rec_item(self, checked=False):
        it = QTableWidgetItem()
        it.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        it.setCheckState(Qt.Checked if checked else Qt.Unchecked)
        it.setTextAlignment(Qt.AlignCenter)
        return it

    def add_row(self):
        r = self.table.rowCount()
        self.table.insertRow(r)
        rank_item = QTableWidgetItem(str(r + 1))
        rank_item.setFlags(rank_item.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(r, 0, rank_item)
        for c in range(1, 4):
            self.table.setItem(r, c, QTableWidgetItem(""))
        self.table.setItem(r, 4, self._make_rec_item(False))

    def add_row_from(self, r: dict):
        row = self.table.rowCount()
        self.table.insertRow(row)
        rank_item = QTableWidgetItem(str(row + 1))
        rank_item.setFlags(rank_item.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(row, 0, rank_item)
        self.table.setItem(row, 1, QTableWidgetItem(r.get("name", "")))
        self.table.setItem(row, 2, QTableWidgetItem(r.get("team", "")))
        self.table.setItem(row, 3, QTableWidgetItem(r.get("score", "")))
        self.table.setItem(row, 4, self._make_rec_item(bool(r.get("isRecord", False))))

    def del_row(self):
        r = self.table.currentRow()
        if r >= 0:
            self.table.removeRow(r)
            self.renumber()

    def clear_all(self):
        if QMessageBox.question(self, "确认", "清空所有行？") == QMessageBox.Yes:
            self.table.setRowCount(0)
            self.add_row()

    def renumber(self):
        for r in range(self.table.rowCount()):
            self.table.item(r, 0).setText(str(r + 1))

    def auto_sort(self):
        rows = []
        for r in range(self.table.rowCount()):
            vals = [
                self.table.item(r, c).text() if self.table.item(r, c) else ""
                for c in range(4)
            ]
            rec_item = self.table.item(r, 4)
            rec = rec_item is not None and rec_item.checkState() == Qt.Checked
            rows.append((vals, rec))
        try:
            rows.sort(key=lambda x: float(x[0][3]))
        except (ValueError, TypeError):
            QMessageBox.warning(self, "提示", "成绩必须是数字才能排序")
            return
        for r, (vals, rec) in enumerate(rows):
            self.table.item(r, 0).setText(str(r + 1))
            for c in range(1, 4):
                self.table.item(r, c).setText(vals[c])
            rec_item = self.table.item(r, 4)
            if rec_item is not None:
                rec_item.setCheckState(Qt.Checked if rec else Qt.Unchecked)

    def delete_event(self):
        item = self.event_list.currentItem()
        if not item:
            QMessageBox.warning(self, "提示", "请先在左侧选中一个项目")
            return
        name = item.text()
        if QMessageBox.question(self, "确认", f"删除项目「{name}」及其成绩？") != QMessageBox.Yes:
            return

        def do_delete():
            r = requests.delete(f"{BASE}/api/event/{name}", timeout=3)
            r.raise_for_status()
            return True

        def on_ok(_):
            self.refresh_event_list()

        def on_err(msg):
            QMessageBox.critical(self, "错误", msg)

        run_async(do_delete, on_success=on_ok, on_error=on_err)

    def collect(self):
        results = []
        for r in range(self.table.rowCount()):
            name_item = self.table.item(r, 1)
            if not name_item:
                continue
            name = name_item.text().strip()
            if not name:
                continue
            score_raw = self.table.item(r, 3).text().strip() if self.table.item(r, 3) else ""
            try:
                score = f"{float(score_raw):.2f}"
            except (ValueError, TypeError):
                score = score_raw

            rec_item = self.table.item(r, 4)
            is_rec = rec_item is not None and rec_item.checkState() == Qt.Checked

            results.append({
                "name": name,
                "team": self.table.item(r, 2).text().strip() if self.table.item(r, 2) else "",
                "score": score,
                "isRecord": is_rec,
            })
        return results

    def import_excel(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择 Excel 文件", "", "Excel 文件 (*.xlsx *.xls)"
        )
        if not path:
            return

        def do_upload():
            with open(path, "rb") as f:
                fname = path.replace("\\", "/").split("/")[-1]
                files = {"file": (fname, f,
                                  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
                r = requests.post(f"{BASE}/api/import_excel", files=files, timeout=15)
            return r.json()

        def on_ok(data):
            if not data.get("ok"):
                QMessageBox.critical(self, "导入失败", data.get("error", "未知错误"))
                return
            results = data["results"]
            if not results:
                QMessageBox.warning(self, "提示", "没有解析到任何数据")
                return

            has_data = any(
                self.table.item(r, 1) and self.table.item(r, 1).text().strip()
                for r in range(self.table.rowCount())
            )
            if has_data:
                choice = QMessageBox.question(
                    self, "导入方式",
                    f"解析到 {len(results)} 条数据。\n\n【Yes】替换当前表格\n【No】追加到当前表格"
                )
                if choice == QMessageBox.Yes:
                    self.table.setRowCount(0)

            for r in results:
                self.add_row_from(r)

            QMessageBox.information(self, "成功", f"已导入 {len(results)} 条数据")

        def on_err(msg):
            QMessageBox.critical(self, "错误", f"上传失败：{msg}")

        run_async(do_upload, on_success=on_ok, on_error=on_err)

    def push(self):
        results = self.collect()
        if not results:
            QMessageBox.warning(self, "提示", "请至少录入一名选手")
            return
        event_name = self.event_input.text().strip() or "未命名项目"
        payload = {"event": event_name, "results": results}

        def do_post():
            r = requests.post(f"{BASE}/api/result", json=payload, timeout=3)
            r.raise_for_status()
            return True

        def on_ok(_):
            self.refresh_event_list()
            QMessageBox.information(self, "成功", f"已推送 {len(results)} 条成绩")

        def on_err(msg):
            QMessageBox.critical(self, "错误", f"推送失败：{msg}")

        run_async(do_post, on_success=on_ok, on_error=on_err)

    def push_next(self):
        next_text = self.next_input.text().strip()
        payload = {"nextEvent": next_text}

        def do_post():
            r = requests.post(f"{BASE}/api/next", json=payload, timeout=3)
            r.raise_for_status()
            return True

        def on_err(msg):
            QMessageBox.critical(self, "错误", msg)

        run_async(do_post, on_error=on_err)

    def switch_to_screen(self):
        if self.on_switch:
            self.hide()
            self.on_switch()