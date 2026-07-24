#!/usr/bin/env python3
from __future__ import annotations

import sys
import threading
import uuid
from dataclasses import dataclass, replace
from datetime import datetime

from PyQt5.QtCore import QObject, QTimer, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QFontDatabase, QIcon, QPainter, QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QButtonGroup,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFrame,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from handsfree.backends import (
    BackendError,
    BaseBackend,
    TargetInfo,
    create_backend,
)
from handsfree.scheduler import TaskConfig, describe_task, run_schedule


UNIT_FACTORS = {"秒": 1.0, "分钟": 60.0, "小时": 3600.0}
TERMINAL_MARKERS = (
    "terminal",
    "terminator",
    "xterm",
    "konsole",
    "kitty",
    "alacritty",
    "wezterm",
    "tilix",
    "powershell",
    "cmd.exe",
    "iterm",
    "codex",
    "claude",
)
INTEGRATION_LABEL = "Herdr 增强版"


APP_STYLE = """
QMainWindow, QWidget#Root {
    background: #f4f7fb;
    color: #172033;
}
QDialog {
    background: #f4f7fb;
    color: #172033;
}
QFrame#Card, QFrame#TaskCard {
    background: #ffffff;
    border: 1px solid #dfe7f2;
    border-radius: 14px;
}
QLabel#AppTitle {
    color: #12213a;
    font-size: 27px;
    font-weight: 700;
}
QLabel#AppSubtitle, QLabel#Muted, QLabel#TaskDetail {
    color: #6b7890;
}
QLabel#SectionTitle {
    color: #1b2b48;
    font-size: 16px;
    font-weight: 700;
}
QLabel#TargetTitle, QLabel#TaskTitle {
    color: #14223b;
    font-size: 14px;
    font-weight: 700;
}
QLabel#LockBadge {
    color: #1d4ed8;
    background: #e8f0ff;
    border: 1px solid #bed2ff;
    border-radius: 10px;
    padding: 4px 9px;
    font-weight: 600;
}
QLabel#PlatformBadge, QLabel#IntegrationBadge {
    color: #0f6b50;
    background: #e6f8f1;
    border: 1px solid #b9e8d7;
    border-radius: 10px;
    padding: 4px 9px;
    font-weight: 600;
}
QLabel#StatusRunning {
    color: #0f6b50;
    background: #e6f8f1;
    border: 1px solid #b9e8d7;
    border-radius: 9px;
    padding: 3px 8px;
    font-weight: 600;
}
QLabel#StatusIdle {
    color: #52606d;
    background: #eef2f7;
    border: 1px solid #d9e1eb;
    border-radius: 9px;
    padding: 3px 8px;
    font-weight: 600;
}
QLabel#StatusError {
    color: #a11c2f;
    background: #fff0f2;
    border: 1px solid #ffc8d0;
    border-radius: 9px;
    padding: 3px 8px;
    font-weight: 600;
}
QPushButton {
    min-height: 34px;
    padding: 0 14px;
    border: 1px solid #cad5e4;
    border-radius: 9px;
    background: #ffffff;
    color: #24334d;
    font-weight: 600;
}
QPushButton:hover {
    background: #f5f8fc;
    border-color: #9fb1c9;
}
QPushButton:disabled {
    color: #9aa6b7;
    background: #f3f5f8;
    border-color: #e1e6ed;
}
QPushButton#PrimaryButton {
    color: #ffffff;
    background: #2563eb;
    border-color: #2563eb;
    min-height: 40px;
}
QPushButton#PrimaryButton:hover {
    background: #1d4ed8;
    border-color: #1d4ed8;
}
QPushButton#DangerButton {
    color: #b42338;
    background: #fff5f6;
    border-color: #ffc7cf;
}
QPushButton#DangerButton:hover {
    background: #ffe9ec;
}
QPushButton#RestartButton {
    color: #1d4ed8;
    background: #eff6ff;
    border-color: #bfdbfe;
}
QPushButton#RestartButton:hover {
    background: #dbeafe;
    border-color: #93c5fd;
}
QPushButton#SegmentButton {
    min-height: 36px;
    min-width: 100px;
    background: #f5f7fb;
    border-color: #d8e0eb;
}
QPushButton#SegmentButton:checked {
    color: #1d4ed8;
    background: #e8f0ff;
    border-color: #8fb2ff;
}
QDoubleSpinBox, QSpinBox, QComboBox {
    min-height: 34px;
    padding: 0 8px;
    background: #ffffff;
    border: 1px solid #cbd6e5;
    border-radius: 8px;
    selection-background-color: #2563eb;
}
QDoubleSpinBox:focus, QSpinBox:focus, QComboBox:focus {
    border-color: #4f7ff0;
}
QRadioButton {
    spacing: 8px;
    min-height: 28px;
}
QProgressBar {
    min-height: 9px;
    max-height: 9px;
    border: none;
    border-radius: 4px;
    background: #e9eef5;
    text-align: center;
}
QProgressBar::chunk {
    border-radius: 4px;
    background: #3b82f6;
}
QScrollArea {
    border: none;
    background: transparent;
}
QScrollBar:vertical {
    width: 10px;
    background: transparent;
}
QScrollBar::handle:vertical {
    min-height: 30px;
    border-radius: 5px;
    background: #c8d3e1;
}
QPlainTextEdit {
    background: #111827;
    color: #dbe7f7;
    border: 1px solid #26344c;
    border-radius: 10px;
    padding: 8px;
}
"""


class EventBridge(QObject):
    task_event = pyqtSignal(str, int, dict)


def split_duration(seconds: float) -> tuple[float, str]:
    for unit in ("小时", "分钟"):
        value = seconds / UNIT_FACTORS[unit]
        if value >= 0.5 and abs(value * 10 - round(value * 10)) < 1e-6:
            return value, unit
    return seconds, "秒"


class TaskSettingsDialog(QDialog):
    def __init__(
        self,
        config: TaskConfig,
        parent: QWidget | None = None,
        auto_stop_available: bool = False,
    ) -> None:
        super().__init__(parent)
        self.original_config = config
        self.auto_stop_available = auto_stop_available
        self.setWindowTitle("修改任务设置")
        self.setMinimumWidth(430)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 18)
        layout.setSpacing(14)

        title = QLabel("修改任务设置")
        title.setObjectName("SectionTitle")
        layout.addWidget(title)
        target = QLabel(f"目标保持不变：{config.target.title}")
        target.setObjectName("Muted")
        target.setWordWrap(True)
        layout.addWidget(target)

        form = QFormLayout()
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(12)

        self.mode_combo = QComboBox()
        self.mode_combo.addItem("按一次", "once")
        self.mode_combo.addItem("循环发送", "repeat")
        self.mode_combo.setCurrentIndex(0 if config.mode == "once" else 1)
        form.addRow("发送方式", self.mode_combo)

        interval_row = QHBoxLayout()
        self.interval_spin = QDoubleSpinBox()
        self.interval_spin.setRange(0.5, 1_000_000)
        self.interval_spin.setDecimals(1)
        interval_value, interval_unit = split_duration(config.interval_seconds)
        self.interval_spin.setValue(interval_value)
        interval_row.addWidget(self.interval_spin, 1)
        self.interval_unit = QComboBox()
        self.interval_unit.addItems(list(UNIT_FACTORS))
        self.interval_unit.setCurrentText(interval_unit)
        interval_row.addWidget(self.interval_unit)
        form.addRow("发送间隔", interval_row)

        self.stop_combo = QComboBox()
        self.stop_combo.addItem("一直运行，手动停止", "manual")
        self.stop_combo.addItem("达到总次数后停止", "count")
        self.stop_combo.addItem("达到总时长后停止", "duration")
        self.stop_combo.addItem("AI 任务完成后自动停止（推荐）", "agent")
        agent_index = self.stop_combo.findData("agent")
        self.stop_combo.model().item(agent_index).setEnabled(auto_stop_available)
        self.stop_combo.setItemData(
            agent_index,
            "仅支持 Herdr 中的 Codex / Claude Code Pane",
            Qt.ToolTipRole,
        )
        stop_index = max(0, self.stop_combo.findData(config.stop_rule))
        self.stop_combo.setCurrentIndex(stop_index)
        form.addRow("停止方式", self.stop_combo)

        self.count_spin = QSpinBox()
        self.count_spin.setRange(1, 1_000_000)
        self.count_spin.setValue(config.max_count or 10)
        self.count_spin.setSuffix(" 次")
        form.addRow("总次数", self.count_spin)

        duration_row = QHBoxLayout()
        self.duration_spin = QDoubleSpinBox()
        self.duration_spin.setRange(0.5, 1_000_000)
        self.duration_spin.setDecimals(1)
        duration_value, duration_unit = split_duration(
            config.max_duration_seconds or 600
        )
        self.duration_spin.setValue(duration_value)
        duration_row.addWidget(self.duration_spin, 1)
        self.duration_unit = QComboBox()
        self.duration_unit.addItems(list(UNIT_FACTORS))
        self.duration_unit.setCurrentText(duration_unit)
        duration_row.addWidget(self.duration_unit)
        form.addRow("总时长", duration_row)
        layout.addLayout(form)

        hint = QLabel("保存后仍绑定当前终端；运行中的任务会自动安全重启以应用新设置。")
        hint.setObjectName("Muted")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText("保存设置")
        buttons.button(QDialogButtonBox.Cancel).setText("取消")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.mode_combo.currentIndexChanged.connect(self._refresh_state)
        self.stop_combo.currentIndexChanged.connect(self._refresh_state)
        self._refresh_state()

    def _refresh_state(self) -> None:
        repeat = self.mode_combo.currentData() == "repeat"
        stop_rule = self.stop_combo.currentData()
        self.stop_combo.setEnabled(repeat)
        self.count_spin.setEnabled(repeat and stop_rule == "count")
        duration_enabled = repeat and stop_rule == "duration"
        self.duration_spin.setEnabled(duration_enabled)
        self.duration_unit.setEnabled(duration_enabled)

    def task_config(self) -> TaskConfig:
        interval = self.interval_spin.value() * UNIT_FACTORS[
            self.interval_unit.currentText()
        ]
        mode = str(self.mode_combo.currentData())
        if mode == "once":
            return replace(
                self.original_config,
                interval_seconds=interval,
                mode="once",
                stop_rule="count",
                max_count=1,
                max_duration_seconds=None,
            )

        stop_rule = str(self.stop_combo.currentData())
        if stop_rule == "manual":
            return replace(
                self.original_config,
                interval_seconds=interval,
                mode="repeat",
                stop_rule="manual",
                max_count=None,
                max_duration_seconds=None,
            )
        if stop_rule == "count":
            return replace(
                self.original_config,
                interval_seconds=interval,
                mode="repeat",
                stop_rule="count",
                max_count=self.count_spin.value(),
                max_duration_seconds=None,
            )

        if stop_rule == "agent":
            if not self.auto_stop_available:
                raise BackendError("当前终端不支持 AI 任务状态监控。")
            return replace(
                self.original_config,
                interval_seconds=interval,
                mode="repeat",
                stop_rule="agent",
                max_count=None,
                max_duration_seconds=None,
            )

        duration = self.duration_spin.value() * UNIT_FACTORS[
            self.duration_unit.currentText()
        ]
        if duration < interval:
            raise BackendError("总时长不能短于发送间隔，否则一次回车也不会发送。")
        return replace(
            self.original_config,
            interval_seconds=interval,
            mode="repeat",
            stop_rule="duration",
            max_count=None,
            max_duration_seconds=duration,
        )

    def accept(self) -> None:
        try:
            self.task_config()
        except BackendError as exc:
            QMessageBox.warning(self, "设置无效", str(exc))
            return
        super().accept()


class TaskCard(QFrame):
    stop_requested = pyqtSignal(str)
    start_requested = pyqtSignal(str)
    restart_requested = pyqtSignal(str)
    edit_requested = pyqtSignal(str)
    change_target_requested = pyqtSignal(str)
    remove_requested = pyqtSignal(str)

    def __init__(self, task_id: str, config: TaskConfig) -> None:
        super().__init__()
        self.task_id = task_id
        self.config = config
        self.setObjectName("TaskCard")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(15, 13, 15, 13)
        outer.setSpacing(8)

        top = QHBoxLayout()
        self.title_label = QLabel(config.target.title)
        self.title_label.setObjectName("TaskTitle")
        self.title_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        top.addWidget(self.title_label, 1)
        self.status_label = QLabel("准备中")
        top.addWidget(self.status_label)
        outer.addLayout(top)

        self.detail_label = QLabel(config.target.detail)
        self.detail_label.setObjectName("TaskDetail")
        self.detail_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        outer.addWidget(self.detail_label)

        self.schedule_label = QLabel(describe_task(config))
        outer.addWidget(self.schedule_label)

        self.metrics_label = QLabel("已发送 0 次 · 下次：--")
        self.metrics_label.setObjectName("Muted")
        outer.addWidget(self.metrics_label)

        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        outer.addWidget(self.progress)

        actions = QHBoxLayout()
        actions.addStretch(1)
        self.start_button = QPushButton("启动")
        self.start_button.clicked.connect(lambda: self.start_requested.emit(self.task_id))
        actions.addWidget(self.start_button)
        self.stop_button = QPushButton("停止")
        self.stop_button.setObjectName("DangerButton")
        self.stop_button.clicked.connect(lambda: self.stop_requested.emit(self.task_id))
        actions.addWidget(self.stop_button)
        self.restart_button = QPushButton("重新运行")
        self.restart_button.setObjectName("RestartButton")
        self.restart_button.clicked.connect(
            lambda: self.restart_requested.emit(self.task_id)
        )
        actions.addWidget(self.restart_button)
        self.edit_button = QPushButton("修改设置")
        self.edit_button.clicked.connect(lambda: self.edit_requested.emit(self.task_id))
        actions.addWidget(self.edit_button)
        self.change_button = QPushButton("更换终端")
        self.change_button.clicked.connect(
            lambda: self.change_target_requested.emit(self.task_id)
        )
        actions.addWidget(self.change_button)
        self.remove_button = QPushButton("删除")
        self.remove_button.clicked.connect(lambda: self.remove_requested.emit(self.task_id))
        actions.addWidget(self.remove_button)
        outer.addLayout(actions)

        self.set_ready("等待启动")

    def _set_status(self, text: str, object_name: str) -> None:
        self.status_label.setText(text)
        self.status_label.setObjectName(object_name)
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

    def update_config(self, config: TaskConfig) -> None:
        self.config = config
        self.title_label.setText(config.target.title)
        self.detail_label.setText(config.target.detail)
        self.schedule_label.setText(describe_task(config))
        self.metrics_label.setText("已发送 0 次 · 下次：--")
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.set_ready("目标已更换")

    def update_schedule(self, config: TaskConfig) -> None:
        self.config = config
        self.schedule_label.setText(describe_task(config))
        self.metrics_label.setText("已发送 0 次 · 新设置将在下次运行时生效")
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self._set_status("设置已更新", "StatusIdle")
        self.start_button.setVisible(False)
        self.stop_button.setVisible(False)
        self.restart_button.setVisible(True)
        self.restart_button.setEnabled(True)
        self.edit_button.setEnabled(True)
        self.change_button.setEnabled(True)
        self.remove_button.setEnabled(True)

    def set_ready(self, status: str = "已停止") -> None:
        self._set_status(status, "StatusIdle")
        self.start_button.setVisible(True)
        self.start_button.setEnabled(True)
        self.stop_button.setVisible(False)
        self.restart_button.setVisible(False)
        self.edit_button.setEnabled(True)
        self.change_button.setEnabled(True)
        self.remove_button.setEnabled(True)

    def set_running(self) -> None:
        self._set_status("运行中", "StatusRunning")
        self.start_button.setVisible(False)
        self.stop_button.setVisible(True)
        self.stop_button.setEnabled(True)
        self.restart_button.setVisible(True)
        self.restart_button.setEnabled(True)
        self.edit_button.setEnabled(True)
        self.change_button.setEnabled(False)
        self.remove_button.setEnabled(False)
        self.metrics_label.setText("已发送 0 次 · 正在等待第一次回车")
        if self.config.stop_rule == "manual":
            self.progress.setRange(0, 0)
        elif self.config.stop_rule == "agent":
            self.progress.setRange(0, 0)
        elif self.config.stop_rule == "duration":
            self.progress.setRange(0, 1000)
            self.progress.setValue(0)
        else:
            self.progress.setRange(0, self.config.max_count or 1)
            self.progress.setValue(0)

    def set_stopping(self) -> None:
        self._set_status("正在停止", "StatusIdle")
        self.stop_button.setEnabled(False)
        self.restart_button.setEnabled(False)
        self.edit_button.setEnabled(False)

    def set_restarting(self) -> None:
        self._set_status("正在重启", "StatusIdle")
        self.stop_button.setEnabled(False)
        self.restart_button.setVisible(True)
        self.restart_button.setEnabled(False)
        self.edit_button.setEnabled(False)

    def update_tick(self, event: dict[str, object]) -> None:
        count = int(event.get("count", 0))
        next_value = event.get("next_in")
        if next_value is None:
            next_text = "等待总时长结束"
        else:
            next_in = float(next_value)
            next_text = f"{next_in:.1f} 秒" if next_in < 10 else f"{next_in:.0f} 秒"
        self.metrics_label.setText(f"已发送 {count} 次 · 下次：{next_text}")

        duration = event.get("duration")
        if duration is not None:
            elapsed = float(event.get("elapsed", 0))
            ratio = min(1.0, elapsed / max(float(duration), 0.001))
            self.progress.setValue(round(ratio * 1000))
        elif self.config.stop_rule == "count":
            self.progress.setValue(count)

    def mark_sent(self, count: int) -> None:
        if self.config.stop_rule == "count":
            self.progress.setValue(count)

    def finish(self, reason: str, count: int, detail: str = "") -> None:
        if reason == "completed":
            status = "已完成"
            object_name = "StatusRunning"
        elif reason == "agent_completed":
            status = "AI 已完成"
            object_name = "StatusRunning"
        elif reason == "duration":
            status = "时间已到"
            object_name = "StatusRunning"
        elif reason == "stopped":
            status = "已停止"
            object_name = "StatusIdle"
        else:
            status = "异常停止"
            object_name = "StatusError"
        self._set_status(status, object_name)
        self.metrics_label.setText(
            f"已发送 {count} 次" + (f" · {detail}" if detail else "")
        )
        self.start_button.setVisible(False)
        self.stop_button.setVisible(False)
        self.restart_button.setVisible(True)
        self.restart_button.setEnabled(reason != "target_closed")
        self.edit_button.setEnabled(True)
        self.change_button.setEnabled(True)
        self.remove_button.setEnabled(True)
        if self.config.stop_rule in {"manual", "agent"}:
            self.progress.setRange(0, 1)
            self.progress.setValue(1 if count else 0)


@dataclass
class TaskRuntime:
    config: TaskConfig
    card: TaskCard
    stop_event: threading.Event
    generation: int = 0
    state: str = "ready"
    count: int = 0
    restart_pending: bool = False


class MainWindow(QMainWindow):
    def __init__(self, backend: BaseBackend) -> None:
        super().__init__()
        self.backend = backend
        self.editor_target: TargetInfo | None = None
        self.agent_poll_interval_seconds = 1.0
        self.tasks: dict[str, TaskRuntime] = {}
        self.bridge = EventBridge()
        self.bridge.task_event.connect(self._handle_task_event)

        self.setWindowTitle(f"解放单手 · {INTEGRATION_LABEL}")
        self.setWindowIcon(make_app_icon())
        self.resize(1200, 850)
        self.setMinimumSize(1040, 720)
        self._build_ui()
        self._refresh_editor_state()
        self._refresh_task_summary()

    def _card(self) -> tuple[QFrame, QVBoxLayout]:
        frame = QFrame()
        frame.setObjectName("Card")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(18, 17, 18, 17)
        layout.setSpacing(12)
        return frame, layout

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)
        page = QVBoxLayout(root)
        page.setContentsMargins(24, 20, 24, 20)
        page.setSpacing(16)

        header = QHBoxLayout()
        title_block = QVBoxLayout()
        title = QLabel("解放单手")
        title.setObjectName("AppTitle")
        managed_name = getattr(self.backend, "managed_target_name", "")
        subtitle_text = (
            f"普通终端与 {managed_name} 均可独立锁定，并行、后台、定时发送回车"
            if managed_name
            else "为多个普通终端建立独立保护锁，并行、后台、定时发送回车"
        )
        subtitle = QLabel(subtitle_text)
        subtitle.setObjectName("AppSubtitle")
        title_block.addWidget(title)
        title_block.addWidget(subtitle)
        header.addLayout(title_block, 1)
        integration_badge = QLabel(INTEGRATION_LABEL)
        integration_badge.setObjectName("IntegrationBadge")
        header.addWidget(integration_badge, 0, Qt.AlignTop)
        platform_badge = QLabel(self.backend.platform_name)
        platform_badge.setObjectName("PlatformBadge")
        header.addWidget(platform_badge, 0, Qt.AlignTop)
        page.addLayout(header)

        content = QHBoxLayout()
        content.setSpacing(16)
        page.addLayout(content, 1)

        editor_card, editor = self._card()
        editor_card.setMinimumWidth(350)
        editor_scroll = QScrollArea()
        editor_scroll.setWidgetResizable(True)
        editor_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        editor_scroll.setFixedWidth(385)
        editor_scroll.setWidget(editor_card)
        content.addWidget(editor_scroll)

        editor_title = QLabel("新建并行任务")
        editor_title.setObjectName("SectionTitle")
        editor.addWidget(editor_title)
        editor_hint = QLabel("选一个终端，设定规则，再添加到右侧任务区。")
        editor_hint.setObjectName("Muted")
        editor_hint.setWordWrap(True)
        editor.addWidget(editor_hint)

        target_box = QFrame()
        target_box.setObjectName("Card")
        target_layout = QVBoxLayout(target_box)
        target_layout.setContentsMargins(13, 12, 13, 12)
        target_layout.setSpacing(6)
        target_top = QHBoxLayout()
        self.editor_target_title = QLabel("尚未选择终端")
        self.editor_target_title.setObjectName("TargetTitle")
        target_top.addWidget(self.editor_target_title, 1)
        self.lock_badge = QLabel("未锁定")
        self.lock_badge.setObjectName("LockBadge")
        target_top.addWidget(self.lock_badge)
        target_layout.addLayout(target_top)
        self.editor_target_detail = QLabel("目标只会在你手工选择时改变")
        self.editor_target_detail.setObjectName("Muted")
        self.editor_target_detail.setWordWrap(True)
        target_layout.addWidget(self.editor_target_detail)
        self.managed_target_button: QPushButton | None = None
        if managed_name:
            self.managed_target_button = QPushButton(f"选择 {managed_name}（推荐）")
            self.managed_target_button.clicked.connect(self._select_editor_managed_target)
            target_layout.addWidget(self.managed_target_button)
        self.select_target_button = QPushButton("点击选择普通终端窗口")
        self.select_target_button.clicked.connect(self._select_editor_target)
        self.select_target_button.setEnabled(
            getattr(self.backend, "window_selection_available", True)
        )
        target_layout.addWidget(self.select_target_button)
        editor.addWidget(target_box)

        mode_label = QLabel("执行模式")
        mode_label.setObjectName("TargetTitle")
        editor.addWidget(mode_label)
        mode_row = QHBoxLayout()
        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)
        self.once_button = QPushButton("按一次")
        self.once_button.setObjectName("SegmentButton")
        self.once_button.setCheckable(True)
        self.repeat_button = QPushButton("循环按")
        self.repeat_button.setObjectName("SegmentButton")
        self.repeat_button.setCheckable(True)
        self.mode_group.addButton(self.once_button)
        self.mode_group.addButton(self.repeat_button)
        self.once_button.setChecked(True)
        self.once_button.toggled.connect(self._refresh_editor_state)
        mode_row.addWidget(self.once_button)
        mode_row.addWidget(self.repeat_button)
        editor.addLayout(mode_row)

        interval_label = QLabel("回车间隔")
        interval_label.setObjectName("TargetTitle")
        editor.addWidget(interval_label)
        interval_row = QHBoxLayout()
        self.interval_spin = QDoubleSpinBox()
        self.interval_spin.setRange(0.5, 86400)
        self.interval_spin.setDecimals(1)
        self.interval_spin.setValue(30)
        self.interval_spin.setSingleStep(1)
        interval_row.addWidget(self.interval_spin, 1)
        self.interval_unit = QComboBox()
        self.interval_unit.addItems(list(UNIT_FACTORS))
        interval_row.addWidget(self.interval_unit)
        editor.addLayout(interval_row)
        interval_help = QLabel("第一次回车也会先等待一个完整间隔。")
        interval_help.setObjectName("Muted")
        interval_help.setWordWrap(True)
        editor.addWidget(interval_help)

        self.stop_options = QFrame()
        stop_layout = QVBoxLayout(self.stop_options)
        stop_layout.setContentsMargins(0, 0, 0, 0)
        stop_layout.setSpacing(7)
        stop_title = QLabel("循环停止条件")
        stop_title.setObjectName("TargetTitle")
        stop_layout.addWidget(stop_title)
        self.stop_group = QButtonGroup(self)
        self.manual_radio = QRadioButton("一直运行，手动停止")
        self.agent_radio = QRadioButton("AI 任务完成后自动停止（推荐）")
        self.agent_radio.setToolTip("仅支持 Herdr 中的 Codex / Claude Code Pane")
        self.count_radio = QRadioButton("达到总次数后停止")
        self.duration_radio = QRadioButton("达到总时长后停止")
        self.manual_radio.setChecked(True)
        for radio in (
            self.manual_radio,
            self.agent_radio,
            self.count_radio,
            self.duration_radio,
        ):
            self.stop_group.addButton(radio)
            radio.toggled.connect(self._refresh_editor_state)
        stop_layout.addWidget(self.manual_radio)
        stop_layout.addWidget(self.agent_radio)

        self.count_controls = QWidget()
        count_row = QHBoxLayout(self.count_controls)
        count_row.setContentsMargins(0, 0, 0, 0)
        count_row.setSpacing(8)
        count_row.addWidget(self.count_radio)
        count_row.addStretch(1)
        self.count_spin = QSpinBox()
        self.count_spin.setRange(1, 1_000_000)
        self.count_spin.setValue(10)
        self.count_spin.setFixedWidth(105)
        count_row.addWidget(self.count_spin)
        count_row.addWidget(QLabel("次"))
        stop_layout.addWidget(self.count_controls)

        self.duration_controls = QWidget()
        duration_row = QHBoxLayout(self.duration_controls)
        duration_row.setContentsMargins(0, 0, 0, 0)
        duration_row.setSpacing(8)
        duration_row.addWidget(self.duration_radio)
        duration_row.addStretch(1)
        self.duration_spin = QDoubleSpinBox()
        self.duration_spin.setRange(0.5, 1_000_000)
        self.duration_spin.setDecimals(1)
        self.duration_spin.setValue(10)
        self.duration_spin.setFixedWidth(85)
        duration_row.addWidget(self.duration_spin)
        self.duration_unit = QComboBox()
        self.duration_unit.addItems(list(UNIT_FACTORS))
        self.duration_unit.setCurrentText("分钟")
        self.duration_unit.setFixedWidth(78)
        duration_row.addWidget(self.duration_unit)
        stop_layout.addWidget(self.duration_controls)
        editor.addWidget(self.stop_options)

        monitor_label = QLabel("AI 状态检查间隔（全局）")
        monitor_label.setObjectName("TargetTitle")
        editor.addWidget(monitor_label)
        monitor_row = QHBoxLayout()
        self.agent_poll_interval_spin = QDoubleSpinBox()
        self.agent_poll_interval_spin.setRange(0.5, 10.0)
        self.agent_poll_interval_spin.setDecimals(1)
        self.agent_poll_interval_spin.setSingleStep(0.5)
        self.agent_poll_interval_spin.setSuffix(" 秒")
        self.agent_poll_interval_spin.setValue(self.agent_poll_interval_seconds)
        self.agent_poll_interval_spin.valueChanged.connect(
            self._update_agent_poll_interval
        )
        monitor_row.addWidget(self.agent_poll_interval_spin)
        monitor_row.addStretch(1)
        editor.addLayout(monitor_row)
        monitor_hint = QLabel(
            "仅控制 Herdr Pane 状态查询；修改后对运行中的 AI 自动停止任务生效。"
        )
        monitor_hint.setObjectName("Muted")
        monitor_hint.setWordWrap(True)
        editor.addWidget(monitor_hint)

        editor.addStretch(1)
        self.add_task_button = QPushButton("添加并启动任务")
        self.add_task_button.setObjectName("PrimaryButton")
        self.add_task_button.clicked.connect(self._add_and_start_task)
        editor.addWidget(self.add_task_button)
        safety = QLabel("安全提示：自动回车会确认目标终端当时显示的内容。")
        safety.setObjectName("Muted")
        safety.setWordWrap(True)
        editor.addWidget(safety)

        tasks_card, tasks_outer = self._card()
        content.addWidget(tasks_card, 1)
        tasks_header = QHBoxLayout()
        tasks_title = QLabel("并行任务")
        tasks_title.setObjectName("SectionTitle")
        tasks_header.addWidget(tasks_title)
        self.task_summary_label = QLabel()
        self.task_summary_label.setObjectName("Muted")
        tasks_header.addWidget(self.task_summary_label)
        tasks_header.addStretch(1)
        self.stop_all_button = QPushButton("全部停止")
        self.stop_all_button.setObjectName("DangerButton")
        self.stop_all_button.clicked.connect(self._stop_all)
        tasks_header.addWidget(self.stop_all_button)
        tasks_outer.addLayout(tasks_header)

        self.empty_label = QLabel("还没有任务\n从左侧选择第一个终端并添加任务")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setObjectName("Muted")
        self.empty_label.setMinimumHeight(180)

        self.task_container = QWidget()
        self.task_layout = QVBoxLayout(self.task_container)
        self.task_layout.setContentsMargins(0, 0, 5, 0)
        self.task_layout.setSpacing(10)
        self.task_layout.addWidget(self.empty_label)
        self.task_layout.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.task_container)
        tasks_outer.addWidget(scroll, 1)

        log_title = QLabel("事件记录")
        log_title.setObjectName("TargetTitle")
        tasks_outer.addWidget(log_title)
        self.log_box = QPlainTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMaximumBlockCount(400)
        self.log_box.setFixedHeight(130)
        tasks_outer.addWidget(self.log_box)

        footer = QLabel(
            f"{self.backend.capability} · 每个任务的目标锁互相独立 · Python：{sys.executable}"
        )
        footer.setObjectName("Muted")
        footer.setWordWrap(True)
        page.addWidget(footer)

    def _log(self, text: str) -> None:
        now = datetime.now().strftime("%H:%M:%S")
        self.log_box.appendPlainText(f"[{now}] {text}")

    def _update_agent_poll_interval(self, value: float) -> None:
        self.agent_poll_interval_seconds = float(value)

    def _refresh_editor_state(self) -> None:
        repeat = self.repeat_button.isChecked()
        auto_stop_available = bool(
            self.editor_target is not None
            and self.backend.supports_completion_monitoring(self.editor_target)
        )
        self.agent_radio.setEnabled(repeat and auto_stop_available)
        if (
            self.agent_radio.isChecked()
            and self.editor_target is not None
            and not auto_stop_available
        ):
            self.manual_radio.setChecked(True)
        self.stop_options.setVisible(repeat)
        self.count_spin.setEnabled(repeat and self.count_radio.isChecked())
        duration_enabled = repeat and self.duration_radio.isChecked()
        self.duration_spin.setEnabled(duration_enabled)
        self.duration_unit.setEnabled(duration_enabled)
        self.add_task_button.setEnabled(self.editor_target is not None)

    def _terminal_likely(self, target: TargetInfo) -> bool:
        text = f"{target.title} {target.detail}".lower()
        return any(marker in text for marker in TERMINAL_MARKERS)

    def _select_target(self) -> TargetInfo | None:
        QMessageBox.information(
            self,
            "手工选择终端",
            "点击“确定”后，控制台会暂时隐藏。\n\n"
            "请用鼠标点击要建立保护锁的终端窗口。只有这次手工选择会改变目标。",
        )
        self.hide()
        QApplication.processEvents()
        try:
            target = self.backend.select_target()
        except BackendError as exc:
            self.show()
            self.raise_()
            self.activateWindow()
            QMessageBox.critical(self, "选择失败", str(exc))
            return None
        self.show()
        self.raise_()
        self.activateWindow()

        if not self._terminal_likely(target):
            answer = QMessageBox.question(
                self,
                "窗口可能不是终端",
                f"选中的窗口看起来不像终端：\n\n{target.title}\n\n仍然使用它吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return None
        return target

    def _select_editor_target(self) -> None:
        target = self._select_target()
        if target is None:
            return
        self._set_editor_target(target)

    def _select_managed_target(self) -> TargetInfo | None:
        try:
            targets = self.backend.list_managed_targets()
        except BackendError as exc:
            managed_name = getattr(self.backend, "managed_target_name", "托管终端")
            QMessageBox.critical(self, f"无法读取 {managed_name}", str(exc))
            return None

        labels: list[str] = []
        mapping: dict[str, TargetInfo] = {}
        for target in targets:
            focus_mark = "★ " if target.metadata.get("focused") == "true" else ""
            label = f"{focus_mark}{target.title} · {target.detail}"
            labels.append(label)
            mapping[label] = target

        managed_name = getattr(self.backend, "managed_target_name", "托管终端")
        selected, accepted = QInputDialog.getItem(
            self,
            f"选择 {managed_name}",
            f"请选择要定时发送回车的 {managed_name}：",
            labels,
            0,
            False,
        )
        if not accepted or not selected:
            return None
        return mapping[selected]

    def _select_editor_managed_target(self) -> None:
        target = self._select_managed_target()
        if target is None:
            return
        self._set_editor_target(target)

    def _set_editor_target(self, target: TargetInfo) -> None:
        self.editor_target = target
        short_title = target.title if len(target.title) <= 35 else f"{target.title[:32]}…"
        self.editor_target_title.setText(short_title)
        self.editor_target_detail.setText(target.detail)
        self.lock_badge.setText("待锁定")
        self.select_target_button.setText("重新选择普通终端窗口")
        self._refresh_editor_state()
        self._log(f"已在编辑区选择：{target.title}")

    def _collect_config(self) -> TaskConfig:
        if self.editor_target is None:
            managed_name = getattr(self.backend, "managed_target_name", "")
            suffix = f"或 {managed_name}" if managed_name else ""
            raise BackendError(f"请先选择普通终端窗口{suffix}。")
        interval = self.interval_spin.value() * UNIT_FACTORS[self.interval_unit.currentText()]
        if self.once_button.isChecked():
            return TaskConfig(
                target=self.editor_target,
                interval_seconds=interval,
                mode="once",
                stop_rule="count",
                max_count=1,
            )

        if self.manual_radio.isChecked():
            return TaskConfig(
                target=self.editor_target,
                interval_seconds=interval,
                mode="repeat",
                stop_rule="manual",
            )
        if self.agent_radio.isChecked():
            if not self.backend.supports_completion_monitoring(self.editor_target):
                raise BackendError("当前终端不支持 AI 任务状态监控。")
            return TaskConfig(
                target=self.editor_target,
                interval_seconds=interval,
                mode="repeat",
                stop_rule="agent",
            )
        if self.count_radio.isChecked():
            return TaskConfig(
                target=self.editor_target,
                interval_seconds=interval,
                mode="repeat",
                stop_rule="count",
                max_count=self.count_spin.value(),
            )

        duration = self.duration_spin.value() * UNIT_FACTORS[
            self.duration_unit.currentText()
        ]
        if duration < interval:
            raise BackendError("总时长不能短于回车间隔，否则一次回车也不会发送。")
        return TaskConfig(
            target=self.editor_target,
            interval_seconds=interval,
            mode="repeat",
            stop_rule="duration",
            max_duration_seconds=duration,
        )

    def _active_target_in_other_task(self, target_key: str, exclude: str = "") -> bool:
        return any(
            task_id != exclude
            and runtime.state in {"running", "stopping"}
            and runtime.config.target.key == target_key
            for task_id, runtime in self.tasks.items()
        )

    def _add_and_start_task(self) -> None:
        try:
            config = self._collect_config()
        except BackendError as exc:
            QMessageBox.warning(self, "无法添加任务", str(exc))
            return
        if self._active_target_in_other_task(config.target.key):
            QMessageBox.warning(self, "目标已在运行", "这个终端已经有一个运行中的任务。")
            return
        if not self.backend.target_exists(config.target):
            QMessageBox.warning(self, "目标已关闭", "目标终端已经关闭，请重新选择。")
            return

        task_id = uuid.uuid4().hex[:10]
        card = TaskCard(task_id, config)
        card.stop_requested.connect(self._stop_task)
        card.start_requested.connect(self._start_task)
        card.restart_requested.connect(self._restart_task)
        card.edit_requested.connect(self._edit_task)
        card.change_target_requested.connect(self._change_task_target)
        card.remove_requested.connect(self._remove_task)
        runtime = TaskRuntime(config=config, card=card, stop_event=threading.Event())
        self.tasks[task_id] = runtime
        self.task_layout.insertWidget(self.task_layout.count() - 1, card)
        self.empty_label.setVisible(False)
        self._log(f"已添加任务：{config.target.title} · {describe_task(config)}")
        self._start_task(task_id)

        # 设置保留，目标清空，方便继续选择下一个终端并行运行。
        self.editor_target = None
        self.editor_target_title.setText("尚未选择终端")
        self.editor_target_detail.setText("目标只会在你手工选择时改变")
        self.lock_badge.setText("未锁定")
        self.select_target_button.setText("点击选择普通终端窗口")
        self._refresh_editor_state()
        self._refresh_task_summary()

    def _start_task(self, task_id: str) -> None:
        runtime = self.tasks.get(task_id)
        if runtime is None or runtime.state in {"running", "stopping"}:
            return
        if self._active_target_in_other_task(runtime.config.target.key, exclude=task_id):
            QMessageBox.warning(self, "目标已在运行", "这个终端已有另一个运行中的任务。")
            return
        if not self.backend.target_exists(runtime.config.target):
            runtime.card.finish("target_closed", runtime.count, "目标终端已经关闭")
            runtime.state = "target_closed"
            QMessageBox.warning(self, "目标已关闭", "请点击“更换终端”重新建立保护锁。")
            return

        runtime.generation += 1
        generation = runtime.generation
        runtime.stop_event = threading.Event()
        runtime.state = "running"
        runtime.count = 0
        runtime.restart_pending = False
        runtime.card.set_running()
        self._log(f"任务启动：{runtime.config.target.title}")
        self._refresh_task_summary()

        completion_check = (
            self.backend.completion_check(runtime.config.target)
            if runtime.config.stop_rule == "agent"
            else None
        )
        if runtime.config.stop_rule == "agent" and completion_check is None:
            runtime.state = "error"
            runtime.card.finish("error", 0, "当前终端不支持 AI 任务状态监控")
            self._log(f"任务无法启动：{runtime.config.target.title} · 不支持状态监控")
            self._refresh_task_summary()
            return

        thread = threading.Thread(
            target=run_schedule,
            args=(
                runtime.config,
                runtime.stop_event,
                self.backend.send_enter,
                lambda event, tid=task_id, gen=generation: self.bridge.task_event.emit(
                    tid, gen, event
                ),
                completion_check,
                lambda: self.agent_poll_interval_seconds,
            ),
            name=f"handsfree-{task_id}",
            daemon=True,
        )
        thread.start()

    def _stop_task(self, task_id: str) -> None:
        runtime = self.tasks.get(task_id)
        if runtime is None:
            return
        if runtime.state == "stopping" and runtime.restart_pending:
            runtime.restart_pending = False
            runtime.card.set_stopping()
            self._log(f"已取消重启：{runtime.config.target.title}")
            return
        if runtime.state != "running":
            return
        runtime.state = "stopping"
        runtime.restart_pending = False
        runtime.card.set_stopping()
        runtime.stop_event.set()
        self._log(f"正在停止：{runtime.config.target.title}")
        self._refresh_task_summary()

    def _restart_task(self, task_id: str) -> None:
        runtime = self.tasks.get(task_id)
        if runtime is None:
            return
        if runtime.state in {"running", "stopping"}:
            runtime.restart_pending = True
            runtime.state = "stopping"
            runtime.card.set_restarting()
            runtime.stop_event.set()
            self._log(f"正在重启：{runtime.config.target.title}")
            self._refresh_task_summary()
            return
        runtime.restart_pending = False
        self._start_task(task_id)

    def _edit_task(self, task_id: str) -> None:
        runtime = self.tasks.get(task_id)
        if runtime is None or runtime.state == "stopping":
            return
        dialog = TaskSettingsDialog(
            runtime.config,
            self,
            auto_stop_available=self.backend.supports_completion_monitoring(
                runtime.config.target
            ),
        )
        if dialog.exec_() != QDialog.Accepted:
            return
        self._apply_task_config(task_id, dialog.task_config())

    def _apply_task_config(self, task_id: str, config: TaskConfig) -> None:
        runtime = self.tasks.get(task_id)
        if runtime is None:
            return
        config = replace(config, target=runtime.config.target)
        was_running = runtime.state == "running"
        runtime.config = config
        runtime.count = 0
        self._log(f"任务设置已更新：{runtime.config.target.title} · {describe_task(config)}")
        if was_running:
            runtime.card.config = config
            runtime.card.schedule_label.setText(describe_task(config))
            self._restart_task(task_id)
            return
        runtime.state = "ready"
        runtime.restart_pending = False
        runtime.card.update_schedule(config)
        self._refresh_task_summary()

    def _stop_all(self) -> None:
        for task_id in list(self.tasks):
            self._stop_task(task_id)

    def _change_task_target(self, task_id: str) -> None:
        runtime = self.tasks.get(task_id)
        if runtime is None or runtime.state in {"running", "stopping"}:
            return
        if getattr(self.backend, "managed_target_name", ""):
            managed_name = self.backend.managed_target_name
            source, accepted = QInputDialog.getItem(
                self,
                "更换目标",
                "选择目标类型：",
                [managed_name, "普通终端窗口"],
                0,
                False,
            )
            if not accepted:
                return
            target = (
                self._select_managed_target()
                if source == managed_name
                else self._select_target()
            )
        else:
            target = self._select_target()
        if target is None:
            return
        if self._active_target_in_other_task(target.key, exclude=task_id):
            QMessageBox.warning(self, "目标已在运行", "这个终端已有一个运行中的任务。")
            return
        runtime.config = replace(runtime.config, target=target)
        runtime.count = 0
        runtime.state = "ready"
        runtime.card.update_config(runtime.config)
        self._log(f"任务已更换目标：{target.title}")
        self._refresh_task_summary()

    def _remove_task(self, task_id: str) -> None:
        runtime = self.tasks.get(task_id)
        if runtime is None or runtime.state in {"running", "stopping"}:
            return
        self.task_layout.removeWidget(runtime.card)
        runtime.card.deleteLater()
        del self.tasks[task_id]
        self._refresh_task_summary()
        self.empty_label.setVisible(not self.tasks)

    def _handle_task_event(self, task_id: str, generation: int, event: dict) -> None:
        runtime = self.tasks.get(task_id)
        if runtime is None or generation != runtime.generation:
            return
        kind = str(event.get("kind", ""))
        if kind == "tick":
            runtime.card.update_tick(event)
            return
        if kind == "sent":
            runtime.count = int(event.get("count", 0))
            runtime.card.mark_sent(runtime.count)
            self._log(f"{runtime.config.target.title}：第 {runtime.count} 次回车")
            return
        if kind != "finished":
            return

        reason = str(event.get("reason", "completed"))
        detail = str(event.get("detail", ""))
        runtime.count = int(event.get("count", runtime.count))
        runtime.state = reason
        runtime.card.finish(reason, runtime.count, detail)
        self._log(
            f"任务结束：{runtime.config.target.title} · {reason} · 共 {runtime.count} 次"
        )
        if runtime.restart_pending:
            runtime.restart_pending = False
            self._log(f"按原配置重新运行：{runtime.config.target.title}")
            self._start_task(task_id)
            return
        self._refresh_task_summary()

    def _refresh_task_summary(self) -> None:
        running = sum(
            runtime.state in {"running", "stopping"} for runtime in self.tasks.values()
        )
        self.task_summary_label.setText(f"{len(self.tasks)} 个任务 · {running} 个运行中")
        self.stop_all_button.setEnabled(running > 0)

    def closeEvent(self, event) -> None:  # type: ignore[override]
        running = any(
            runtime.state in {"running", "stopping"} for runtime in self.tasks.values()
        )
        if running:
            answer = QMessageBox.question(
                self,
                "退出解放单手",
                "仍有并行任务正在运行。全部停止并退出吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                event.ignore()
                return
            for runtime in self.tasks.values():
                runtime.restart_pending = False
                runtime.stop_event.set()
        event.accept()


def make_app_icon() -> QIcon:
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QColor("#2563eb"))
    painter.setPen(Qt.NoPen)
    painter.drawRoundedRect(4, 4, 56, 56, 14, 14)
    painter.setPen(QColor("#ffffff"))
    font = QFont("Sans", 24, QFont.Bold)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignCenter, ">_")
    painter.end()
    return QIcon(pixmap)


def choose_font(app: QApplication) -> None:
    families = set(QFontDatabase().families())
    if sys.platform == "win32":
        preferred = ["Microsoft YaHei UI", "Microsoft YaHei", "Noto Sans CJK SC"]
    elif sys.platform == "darwin":
        preferred = ["PingFang SC", "Hiragino Sans GB", "Noto Sans CJK SC"]
    else:
        preferred = [
            "Noto Sans CJK SC",
            "Source Han Sans SC",
            "WenQuanYi Micro Hei",
            "Microsoft YaHei",
            "DejaVu Sans",
        ]
    family = next((name for name in preferred if name in families), app.font().family())
    app.setFont(QFont(family, 10))


def main() -> int:
    smoke_test = "--smoke-test" in sys.argv
    if smoke_test:
        sys.argv.remove("--smoke-test")

    if hasattr(Qt, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("解放单手")
    app.setOrganizationName("HandsFreeTools")
    choose_font(app)
    app.setStyleSheet(APP_STYLE)

    try:
        backend = create_backend()
        backend.check_environment()
    except BackendError as exc:
        QMessageBox.critical(None, "无法启动解放单手", str(exc))
        return 1

    window = MainWindow(backend)
    window.show()
    if smoke_test:
        QTimer.singleShot(800, window.close)
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
