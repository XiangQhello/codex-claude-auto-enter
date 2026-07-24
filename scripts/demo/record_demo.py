#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from PyQt5.QtCore import QRect, QRectF, Qt  # noqa: E402
from PyQt5.QtGui import QColor, QFont, QImage, QPainter, QPen  # noqa: E402
from PyQt5.QtWidgets import QApplication, QLabel  # noqa: E402

from app import APP_STYLE, MainWindow, choose_font  # noqa: E402
from handsfree.backends import BaseBackend, TargetInfo  # noqa: E402


class DemoBackend(BaseBackend):
    platform_name = "Demo · Herdr"
    capability = "演示模式：Herdr Pane 定向发送与状态监控"
    managed_target_name = "Herdr AI Agent / Pane"
    window_selection_available = False

    def __init__(self) -> None:
        self.agent_status = "working"
        self.demo_phase = "intro"
        self.target = TargetInfo(
            key="herdr:demo:p1",
            title="demo-project · Codex",
            platform_name="Herdr",
            detail="Herdr Pane demo:p1 · working · /workspace/demo-project",
            metadata={
                "transport": "herdr",
                "pane_id": "demo:p1",
                "agent": "Codex",
                "status": "working",
            },
        )

    def check_environment(self) -> None:
        return

    def select_target(self) -> TargetInfo:
        return self.target

    def list_managed_targets(self) -> list[TargetInfo]:
        return [self.target]

    def target_exists(self, target: TargetInfo) -> bool:
        return True

    def supports_completion_monitoring(self, target: TargetInfo) -> bool:
        return target.metadata.get("agent") == "Codex"

    def completion_check(self, target: TargetInfo):
        return lambda: self.agent_status == "idle"

    def send_enter(self, target: TargetInfo) -> None:
        return

    def terminal_lines(self) -> list[tuple[str, str]]:
        common = [
            ("#94a3b8", "jq@devbox:~/demo-project$ herdr"),
            ("#86efac", "✓ Herdr workspace ready"),
            ("#94a3b8", "pane demo:p1 · Codex"),
            ("#e2e8f0", ""),
            ("#c4b5fd", "Codex > Improve the task scheduler"),
        ]
        phases = {
            "intro": [
                ("#60a5fa", "● working"),
                ("#cbd5e1", "Reading the repository..."),
                ("#64748b", "Waiting for the next confirmation"),
            ],
            "selected": [
                ("#60a5fa", "● working"),
                ("#cbd5e1", "Target locked to pane demo:p1"),
                ("#a5b4fc", "Hands-Free Enter is monitoring"),
            ],
            "working": [
                ("#60a5fa", "● working"),
                ("#cbd5e1", "Editing scheduler.py"),
                ("#cbd5e1", "Running focused tests..."),
                ("#a5b4fc", "↳ Enter sent to this pane only"),
            ],
            "blocked": [
                ("#fbbf24", "● blocked · confirmation needed"),
                ("#e2e8f0", "Run unit tests? [Y/n]"),
                ("#86efac", "Y"),
                ("#a5b4fc", "↳ Directed Enter confirmed here"),
            ],
            "idle": [
                ("#86efac", "✓ Task completed · 24 tests passed"),
                ("#4ade80", "● idle detected"),
                ("#fda4af", "Hands-Free Enter stopped sending"),
                ("#e2e8f0", ""),
                ("#94a3b8", "jq@devbox:~/demo-project$ "),
                ("#64748b", "Your next command stays unsubmitted"),
            ],
        }
        return common + phases[self.demo_phase]


def render_demo_frame(window: MainWindow, backend: DemoBackend) -> QImage:
    canvas = QImage(1600, 900, QImage.Format_RGB32)
    canvas.fill(QColor("#eef2f7"))
    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.Antialiasing)

    painter.setPen(QColor("#0f172a"))
    painter.setFont(QFont("Noto Sans CJK SC", 24, QFont.Bold))
    painter.drawText(30, 45, "Hands-Free Enter + Herdr terminal")
    painter.setPen(QColor("#64748b"))
    painter.setFont(QFont("Noto Sans CJK SC", 12))
    painter.drawText(30, 68, "Simulated demo · no real terminal content or credentials")

    app_rect = QRectF(24, 86, 1060, 770)
    painter.setPen(QPen(QColor("#cbd5e1"), 1))
    painter.setBrush(QColor("#ffffff"))
    painter.drawRoundedRect(app_rect, 14, 14)
    app_frame = window.grab()
    painter.drawPixmap(QRect(36, 100, 1036, 648), app_frame)
    painter.setPen(QColor("#475569"))
    painter.setFont(QFont("Noto Sans CJK SC", 13, QFont.Bold))
    painter.drawText(44, 786, "Hands-Free Enter")
    painter.setFont(QFont("Noto Sans CJK SC", 11))
    painter.setPen(QColor("#64748b"))
    painter.drawText(44, 813, "Locks the target, monitors status, and stops safely on idle")

    terminal_rect = QRectF(1100, 86, 476, 770)
    painter.setPen(QPen(QColor("#334155"), 1))
    painter.setBrush(QColor("#0f172a"))
    painter.drawRoundedRect(terminal_rect, 14, 14)
    painter.setPen(Qt.NoPen)
    for x, color in ((1122, "#fb7185"), (1146, "#fbbf24"), (1170, "#4ade80")):
        painter.setBrush(QColor(color))
        painter.drawEllipse(QRectF(x, 105, 12, 12))
    painter.setPen(QColor("#cbd5e1"))
    painter.setFont(QFont("DejaVu Sans Mono", 12, QFont.Bold))
    painter.drawText(1200, 117, "Herdr · Codex pane demo:p1")

    painter.setFont(QFont("DejaVu Sans Mono", 14))
    line_y = 158
    for color, line in backend.terminal_lines():
        painter.setPen(QColor(color))
        painter.drawText(1122, line_y, line)
        line_y += 34

    status_config = {
        "working": ("#1d4ed8", "working · directed Enter enabled"),
        "blocked": ("#b45309", "blocked · confirmation handled"),
        "idle": ("#15803d", "idle · automatic Enter stopped"),
    }
    status_color, status_text = status_config[backend.agent_status]
    painter.setBrush(QColor(status_color))
    painter.setPen(Qt.NoPen)
    painter.drawRoundedRect(QRectF(1120, 794, 436, 42), 10, 10)
    painter.setPen(QColor("#ffffff"))
    painter.setFont(QFont("DejaVu Sans", 12, QFont.Bold))
    painter.drawText(1138, 821, status_text)

    painter.end()
    return canvas


def capture_for(
    app: QApplication,
    window: MainWindow,
    backend: DemoBackend,
    frames_dir: Path,
    frame_index: int,
    seconds: float,
    fps: int,
) -> int:
    deadline = time.monotonic() + seconds
    frame_period = 1.0 / fps
    while time.monotonic() < deadline:
        started = time.monotonic()
        app.processEvents()
        window.repaint()
        app.processEvents()
        frame = render_demo_frame(window, backend)
        if not frame.save(str(frames_dir / f"frame-{frame_index:05d}.png")):
            raise RuntimeError("无法保存 Demo 帧。")
        frame_index += 1
        remaining = frame_period - (time.monotonic() - started)
        if remaining > 0:
            time.sleep(remaining)
    return frame_index


def main() -> int:
    fps = 10
    assets_dir = ROOT / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    app = QApplication.instance() or QApplication([])
    app.setApplicationName("解放单手 Demo")
    choose_font(app)
    app.setStyleSheet(APP_STYLE)
    backend = DemoBackend()
    window = MainWindow(backend)
    window.setWindowFlags(Qt.Window)
    window.resize(1280, 800)
    window.show()
    app.processEvents()
    for label in window.findChildren(QLabel):
        if "Python：" in label.text():
            label.setText("演示模式 · Herdr Pane 定向发送与状态监控")

    with tempfile.TemporaryDirectory(prefix="handsfree-demo-") as temp_dir:
        frames_dir = Path(temp_dir)
        index = 0

        window._log("Demo：传统定时回车无法知道 Codex 何时完成")
        index = capture_for(app, window, backend, frames_dir, index, 1.2, fps)

        window._set_editor_target(backend.target)
        backend.demo_phase = "selected"
        window.repeat_button.setChecked(True)
        window.interval_spin.setValue(0.5)
        window.agent_radio.setChecked(True)
        window.agent_poll_interval_spin.setValue(0.5)
        window._log("Demo：锁定具体 Herdr Codex Pane，并启用完成自动停止")
        index = capture_for(app, window, backend, frames_dir, index, 1.6, fps)

        window._add_and_start_task()
        backend.demo_phase = "working"
        window._log("Demo：working — Codex 正在执行，定向发送 Enter")
        index = capture_for(app, window, backend, frames_dir, index, 2.0, fps)

        backend.agent_status = "blocked"
        backend.demo_phase = "blocked"
        window._log("Demo：blocked — Codex 等待确认，任务继续运行")
        index = capture_for(app, window, backend, frames_dir, index, 1.5, fps)

        backend.agent_status = "idle"
        backend.demo_phase = "idle"
        window._log("Demo：idle — 本轮已完成，不再发送 Enter")
        index = capture_for(app, window, backend, frames_dir, index, 2.0, fps)

        app.processEvents()
        final_frame = render_demo_frame(window, backend)
        if not final_frame.save(str(assets_dir / "demo-thumbnail.png")):
            raise RuntimeError("无法保存 Demo 缩略图。")

        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-loglevel",
                "error",
                "-framerate",
                str(fps),
                "-i",
                str(frames_dir / "frame-%05d.png"),
                "-c:v",
                "libx264",
                "-preset",
                "slow",
                "-crf",
                "24",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                str(assets_dir / "demo.mp4"),
            ],
            check=True,
        )
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-loglevel",
                "error",
                "-i",
                str(assets_dir / "demo.mp4"),
                "-filter_complex",
                (
                    "fps=10,scale=1120:-1:flags=lanczos,split[gif_src][palette_src];"
                    "[palette_src]palettegen=stats_mode=diff[palette];"
                    "[gif_src][palette]paletteuse=dither=bayer:"
                    "bayer_scale=3:diff_mode=rectangle"
                ),
                "-loop",
                "0",
                str(assets_dir / "demo.gif"),
            ],
            check=True,
        )

    window.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
