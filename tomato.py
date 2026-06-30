#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Ubuntu 22.04 Pomodoro Timer Desktop App

Features:
1. Countdown timer and count-up timer.
2. Set time by sliders or numeric spin boxes: hours, minutes, seconds.
3. Configurable break duration. After focus countdown ends, automatically enters break countdown.
4. Popup notification and user-selected music when countdown ends.

Dependencies:
    sudo apt update
    sudo apt install python3-pyqt5 mpv

Run:
    python3 tomato.py

Why mpv for music:
    PyQt5.QtMultimedia on Ubuntu sometimes fails because of missing Qt/GStreamer codecs.
    Calling mpv is usually more reliable for mp3/wav/ogg/flac playback.
"""

import csv
import sys
import subprocess
from datetime import datetime
from enum import Enum, auto
from pathlib import Path

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QWidget,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QFileDialog,
    QMessageBox,
    QHBoxLayout,
    QVBoxLayout,
    QGridLayout,
    QGroupBox,
    QRadioButton,
    QButtonGroup,
    QLineEdit,
    QMenu,
    QSystemTrayIcon,
)

BASE_DIR = Path(__file__).resolve().parent
ICON_PATH = BASE_DIR / "assets" / "pomodoro.svg"
DATA_DIR = BASE_DIR / "data"
FOCUS_LOG_PATH = DATA_DIR / "focus_sessions.csv"
WEEKDAYS_CN = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]


class TimerMode(Enum):
    COUNTDOWN = auto()
    COUNTUP = auto()


class Phase(Enum):
    FOCUS = auto()
    BREAK = auto()


class PomodoroApp(QWidget):
    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("Ubuntu 番茄钟")
        self.app_icon = QIcon(str(ICON_PATH))
        self.setWindowIcon(self.app_icon)
        self.resize(620, 520)

        self.mode = TimerMode.COUNTDOWN
        self.phase = Phase.FOCUS
        self.is_running = False

        self.focus_total_seconds = 45 * 60
        self.break_total_seconds = 15 * 60
        self.remaining_seconds = self.focus_total_seconds
        self.elapsed_seconds = 0

        self.music_path: str | None = str(BASE_DIR / "music" / "稻香-周杰伦.mp3")
        self.allow_close = False
        self.tray_icon: QSystemTrayIcon | None = None

        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.on_tick)
        
        self.music_process: subprocess.Popen | None = None

        self.build_ui()
        self.create_tray_icon()
        self.connect_signals()
        self.sync_focus_inputs_from_seconds(self.focus_total_seconds)
        self.sync_break_inputs_from_seconds(self.break_total_seconds)
        self.update_display()

    def create_tray_icon(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return

        self.tray_icon = QSystemTrayIcon(self.app_icon, self)
        self.tray_icon.setToolTip("番茄钟 · 专注时间")

        tray_menu = QMenu(self)
        self.show_action = QAction("隐藏窗口", self)
        self.timer_action = QAction("开始", self)
        reset_action = QAction("重置", self)
        quit_action = QAction("退出番茄钟", self)

        self.show_action.triggered.connect(self.toggle_window)
        self.timer_action.triggered.connect(self.toggle_timer)
        reset_action.triggered.connect(lambda: self.reset_timer())
        quit_action.triggered.connect(self.quit_application)

        tray_menu.addAction(self.show_action)
        tray_menu.addSeparator()
        tray_menu.addAction(self.timer_action)
        tray_menu.addAction(reset_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()

    def toggle_window(self) -> None:
        if self.isVisible():
            self.hide()
        else:
            self.showNormal()
            self.activateWindow()
            self.raise_()
        self.update_tray_actions()

    def on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.toggle_window()

    def toggle_timer(self) -> None:
        if self.is_running:
            self.pause_timer()
        else:
            self.start_timer()

    def quit_application(self) -> None:
        self.allow_close = True
        self.stop_music()
        self.timer.stop()
        if self.tray_icon:
            self.tray_icon.hide()
        QApplication.quit()

    # ---------------- UI ----------------
    def build_ui(self) -> None:
        root = QVBoxLayout()

        self.phase_label = QLabel("专注时间")
        self.phase_label.setAlignment(Qt.AlignCenter)
        self.phase_label.setFont(QFont("Arial", 18, QFont.Bold))

        self.time_label = QLabel("45:00")
        self.time_label.setAlignment(Qt.AlignCenter)
        self.time_label.setFont(QFont("Arial", 52, QFont.Bold))

        root.addWidget(self.phase_label)
        root.addWidget(self.time_label)

        mode_group = QGroupBox("计时模式")
        mode_layout = QHBoxLayout()
        self.countdown_radio = QRadioButton("倒计时")
        self.countup_radio = QRadioButton("正向计时")
        self.countdown_radio.setChecked(True)
        self.mode_buttons = QButtonGroup(self)
        self.mode_buttons.addButton(self.countdown_radio)
        self.mode_buttons.addButton(self.countup_radio)
        mode_layout.addWidget(self.countdown_radio)
        mode_layout.addWidget(self.countup_radio)
        mode_group.setLayout(mode_layout)
        root.addWidget(mode_group)

        self.focus_group = self.create_time_group("专注时间", prefix="focus")
        self.break_group = self.create_time_group("休息时间", prefix="break")
        root.addWidget(self.focus_group)
        root.addWidget(self.break_group)

        music_group = QGroupBox("结束音乐")
        music_layout = QHBoxLayout()
        self.music_line = QLineEdit()
        self.music_line.setReadOnly(True)
        self.music_line.setPlaceholderText("试听稻香.mp3 或选择其他音乐")
        self.choose_music_btn = QPushButton("选择音乐")
        self.test_music_btn = QPushButton("试听")
        self.stop_music_btn = QPushButton("停止音乐")
        music_layout.addWidget(self.music_line)
        music_layout.addWidget(self.choose_music_btn)
        music_layout.addWidget(self.test_music_btn)
        music_layout.addWidget(self.stop_music_btn)
        music_group.setLayout(music_layout)
        root.addWidget(music_group)

        button_layout = QHBoxLayout()
        self.start_btn = QPushButton("开始")
        self.pause_btn = QPushButton("暂停")
        self.reset_btn = QPushButton("重置")
        self.skip_btn = QPushButton("跳过当前阶段")

        self.start_btn.setMinimumHeight(42)
        self.pause_btn.setMinimumHeight(42)
        self.reset_btn.setMinimumHeight(42)
        self.skip_btn.setMinimumHeight(42)

        button_layout.addWidget(self.start_btn)
        button_layout.addWidget(self.pause_btn)
        button_layout.addWidget(self.reset_btn)
        button_layout.addWidget(self.skip_btn)
        root.addLayout(button_layout)

        note = QLabel("提示：倒计时模式下，专注结束后会自动进入休息倒计时。正向计时模式不会自动进入休息。")
        note.setWordWrap(True)
        note.setAlignment(Qt.AlignCenter)
        root.addWidget(note)

        self.setLayout(root)

    def create_time_group(self, title: str, prefix: str) -> QGroupBox:
        group = QGroupBox(title)
        layout = QGridLayout()

        hour_slider = QSlider(Qt.Horizontal)
        minute_slider = QSlider(Qt.Horizontal)
        second_slider = QSlider(Qt.Horizontal)
        hour_spin = QSpinBox()
        minute_spin = QSpinBox()
        second_spin = QSpinBox()

        hour_slider.setRange(0, 23)
        minute_slider.setRange(0, 59)
        second_slider.setRange(0, 59)
        hour_spin.setRange(0, 23)
        minute_spin.setRange(0, 59)
        second_spin.setRange(0, 59)

        hour_spin.setSuffix(" 时")
        minute_spin.setSuffix(" 分")
        second_spin.setSuffix(" 秒")

        layout.addWidget(QLabel("小时"), 0, 0)
        layout.addWidget(hour_slider, 0, 1)
        layout.addWidget(hour_spin, 0, 2)
        layout.addWidget(QLabel("分钟"), 1, 0)
        layout.addWidget(minute_slider, 1, 1)
        layout.addWidget(minute_spin, 1, 2)
        layout.addWidget(QLabel("秒"), 2, 0)
        layout.addWidget(second_slider, 2, 1)
        layout.addWidget(second_spin, 2, 2)

        group.setLayout(layout)

        setattr(self, f"{prefix}_hour_slider", hour_slider)
        setattr(self, f"{prefix}_minute_slider", minute_slider)
        setattr(self, f"{prefix}_second_slider", second_slider)
        setattr(self, f"{prefix}_hour_spin", hour_spin)
        setattr(self, f"{prefix}_minute_spin", minute_spin)
        setattr(self, f"{prefix}_second_spin", second_spin)

        return group

    # ---------------- Signals ----------------
    def connect_signals(self) -> None:
        self.start_btn.clicked.connect(self.start_timer)
        self.pause_btn.clicked.connect(self.pause_timer)
        self.reset_btn.clicked.connect(lambda: self.reset_timer())
        self.skip_btn.clicked.connect(lambda: self.finish_current_phase("skipped"))

        self.countdown_radio.toggled.connect(self.on_mode_changed)
        self.countup_radio.toggled.connect(self.on_mode_changed)

        self.choose_music_btn.clicked.connect(self.choose_music)
        self.test_music_btn.clicked.connect(self.play_music)
        self.stop_music_btn.clicked.connect(self.stop_music)

        self.connect_time_inputs("focus")
        self.connect_time_inputs("break")

    def connect_time_inputs(self, prefix: str) -> None:
        for name in ["hour", "minute", "second"]:
            slider: QSlider = getattr(self, f"{prefix}_{name}_slider")
            spin: QSpinBox = getattr(self, f"{prefix}_{name}_spin")

            slider.valueChanged.connect(spin.setValue)
            spin.valueChanged.connect(slider.setValue)

        getattr(self, f"{prefix}_hour_spin").valueChanged.connect(lambda _: self.on_time_input_changed(prefix))
        getattr(self, f"{prefix}_minute_spin").valueChanged.connect(lambda _: self.on_time_input_changed(prefix))
        getattr(self, f"{prefix}_second_spin").valueChanged.connect(lambda _: self.on_time_input_changed(prefix))

    # ---------------- Time helpers ----------------
    @staticmethod
    def format_seconds(total_seconds: int) -> str:
        total_seconds = max(0, total_seconds)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"

    def read_seconds_from_inputs(self, prefix: str) -> int:
        hours = getattr(self, f"{prefix}_hour_spin").value()
        minutes = getattr(self, f"{prefix}_minute_spin").value()
        seconds = getattr(self, f"{prefix}_second_spin").value()
        return hours * 3600 + minutes * 60 + seconds

    def sync_focus_inputs_from_seconds(self, total_seconds: int) -> None:
        self.sync_inputs_from_seconds("focus", total_seconds)

    def sync_break_inputs_from_seconds(self, total_seconds: int) -> None:
        self.sync_inputs_from_seconds("break", total_seconds)

    def sync_inputs_from_seconds(self, prefix: str, total_seconds: int) -> None:
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        getattr(self, f"{prefix}_hour_spin").setValue(hours)
        getattr(self, f"{prefix}_minute_spin").setValue(minutes)
        getattr(self, f"{prefix}_second_spin").setValue(seconds)

    # ---------------- Logic ----------------
    def on_time_input_changed(self, prefix: str) -> None:
        if prefix == "focus":
            self.focus_total_seconds = self.read_seconds_from_inputs("focus")
            if not self.is_running and self.phase == Phase.FOCUS:
                self.remaining_seconds = self.focus_total_seconds
                self.elapsed_seconds = 0
                self.update_display()
        else:
            self.break_total_seconds = self.read_seconds_from_inputs("break")
            if not self.is_running and self.phase == Phase.BREAK:
                self.remaining_seconds = self.break_total_seconds
                self.elapsed_seconds = 0
                self.update_display()

    def on_mode_changed(self) -> None:
        self.mode = TimerMode.COUNTDOWN if self.countdown_radio.isChecked() else TimerMode.COUNTUP
        self.reset_timer(save_trigger=None)

    def start_timer(self) -> None:
        if self.mode == TimerMode.COUNTDOWN and self.current_phase_total_seconds() <= 0:
            QMessageBox.warning(self, "时间无效", "请至少设置 1 秒。")
            return

        self.is_running = True
        self.timer.start()
        self.update_buttons()

    def pause_timer(self) -> None:
        self.is_running = False
        self.timer.stop()
        self.update_buttons()

    def reset_timer(self, save_trigger: str | None = "reset") -> None:
        self.pause_timer()
        if save_trigger:
            self.maybe_save_focus_session(save_trigger)
        self.phase = Phase.FOCUS
        self.remaining_seconds = self.focus_total_seconds
        self.elapsed_seconds = 0
        self.stop_music()
        self.update_display()

    def current_phase_total_seconds(self) -> int:
        return self.focus_total_seconds if self.phase == Phase.FOCUS else self.break_total_seconds

    def on_tick(self) -> None:
        if self.mode == TimerMode.COUNTDOWN:
            self.remaining_seconds -= 1
            if self.remaining_seconds <= 0:
                self.remaining_seconds = 0
                self.update_display()
                self.finish_current_phase("completed")
                return
        else:
            self.elapsed_seconds += 1

        self.update_display()

    def finish_current_phase(self, save_trigger: str = "completed") -> None:
        self.pause_timer()
        self.play_music()

        if self.phase == Phase.FOCUS:
            self.maybe_save_focus_session(save_trigger)
            QMessageBox.information(self, "专注结束", "专注时间结束，自动进入休息时间。")
            self.phase = Phase.BREAK
            self.remaining_seconds = self.break_total_seconds
            self.elapsed_seconds = 0
            self.update_display()
            if self.mode == TimerMode.COUNTDOWN and self.break_total_seconds > 0:
                self.start_timer()
        else:
            QMessageBox.information(self, "休息结束", "休息时间结束，可以开始下一轮专注。")
            self.phase = Phase.FOCUS
            self.remaining_seconds = self.focus_total_seconds
            self.elapsed_seconds = 0
            self.update_display()

    def update_display(self) -> None:
        if self.phase == Phase.FOCUS:
            self.phase_label.setText("专注时间")
        else:
            self.phase_label.setText("休息时间")

        if self.mode == TimerMode.COUNTDOWN:
            self.time_label.setText(self.format_seconds(self.remaining_seconds))
        else:
            self.time_label.setText(self.format_seconds(self.elapsed_seconds))

        self.update_buttons()

    def update_buttons(self) -> None:
        self.start_btn.setEnabled(not self.is_running)
        self.pause_btn.setEnabled(self.is_running)
        self.update_tray_actions()

    def update_tray_actions(self) -> None:
        if not self.tray_icon:
            return

        phase = "专注" if self.phase == Phase.FOCUS else "休息"
        shown_seconds = self.remaining_seconds if self.mode == TimerMode.COUNTDOWN else self.elapsed_seconds
        state = "进行中" if self.is_running else "已暂停"
        self.tray_icon.setToolTip(f"番茄钟 · {phase} {self.format_seconds(shown_seconds)} · {state}")
        self.show_action.setText("隐藏窗口" if self.isVisible() else "显示窗口")
        self.timer_action.setText("暂停" if self.is_running else "开始")

    # ---------------- Focus log ----------------
    def current_focus_duration_seconds(self) -> int:
        if self.phase != Phase.FOCUS:
            return 0

        if self.mode == TimerMode.COUNTDOWN:
            return max(0, self.focus_total_seconds - self.remaining_seconds)
        return max(0, self.elapsed_seconds)

    def maybe_save_focus_session(self, trigger: str) -> None:
        duration_seconds = self.current_focus_duration_seconds()
        if duration_seconds <= 0:
            return

        duration_text = self.format_seconds(duration_seconds)
        answer = QMessageBox.question(
            self,
            "保存本次专注吗？",
            f"本次专注时长：{duration_text}\n\n是否保存到专注统计记录？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if answer == QMessageBox.Yes:
            self.save_focus_session(duration_seconds, trigger)

    def save_focus_session(self, duration_seconds: int, trigger: str) -> None:
        ended_at = datetime.now().astimezone()
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        file_exists = FOCUS_LOG_PATH.exists()
        with FOCUS_LOG_PATH.open("a", newline="", encoding="utf-8") as log_file:
            fieldnames = [
                "ended_at",
                "date",
                "weekday",
                "duration_seconds",
                "duration_minutes",
                "mode",
                "trigger",
            ]
            writer = csv.DictWriter(log_file, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow(
                {
                    "ended_at": ended_at.isoformat(timespec="seconds"),
                    "date": ended_at.date().isoformat(),
                    "weekday": WEEKDAYS_CN[ended_at.weekday()],
                    "duration_seconds": duration_seconds,
                    "duration_minutes": f"{duration_seconds / 60:.2f}",
                    "mode": "倒计时" if self.mode == TimerMode.COUNTDOWN else "正向计时",
                    "trigger": trigger,
                }
            )

    # ---------------- Music ----------------
    def choose_music(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择结束音乐",
            str(Path.home()),
            "Audio Files (*.mp3 *.wav *.ogg *.flac);;All Files (*)",
        )
        if path:
            self.music_path = path
            self.music_line.setText(path)

    def play_music(self) -> None:
        if not self.music_path:
            return

        self.stop_music()

        try:
            self.music_process = subprocess.Popen(
                ["mpv", "--no-terminal", "--really-quiet", self.music_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            QMessageBox.warning(
                self,
                "无法播放音乐",
                "系统没有安装 mpv。请运行:sudo apt install mpv",
            )

    def stop_music(self) -> None:
        if self.music_process and self.music_process.poll() is None:
            self.music_process.terminate()
            # self.music_process.wait(timeout=1)
        self.music_process = None

    def closeEvent(self, event) -> None:
        if self.tray_icon and self.tray_icon.isVisible() and not self.allow_close:
            event.ignore()
            self.hide()
            self.update_tray_actions()
            self.tray_icon.showMessage(
                "番茄钟仍在运行",
                "窗口已隐藏到系统托盘，右键托盘图标可退出。",
                QSystemTrayIcon.Information,
                2500,
            )
            return

        self.stop_music()
        self.timer.stop()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("Ubuntu Pomodoro")
    app.setWindowIcon(QIcon(str(ICON_PATH)))
    window = PomodoroApp()
    window.show()
    sys.exit(app.exec_())
