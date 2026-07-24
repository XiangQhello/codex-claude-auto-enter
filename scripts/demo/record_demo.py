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

from PyQt5.QtCore import Qt  # noqa: E402
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


def capture_for(
    app: QApplication,
    window: MainWindow,
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
        frame = window.grab()
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
        index = capture_for(app, window, frames_dir, index, 1.2, fps)

        window._set_editor_target(backend.target)
        window.repeat_button.setChecked(True)
        window.interval_spin.setValue(0.5)
        window.agent_radio.setChecked(True)
        window.agent_poll_interval_spin.setValue(0.5)
        window._log("Demo：锁定具体 Herdr Codex Pane，并启用完成自动停止")
        index = capture_for(app, window, frames_dir, index, 1.6, fps)

        window._add_and_start_task()
        window._log("Demo：working — Codex 正在执行，定向发送 Enter")
        index = capture_for(app, window, frames_dir, index, 2.0, fps)

        backend.agent_status = "blocked"
        window._log("Demo：blocked — Codex 等待确认，任务继续运行")
        index = capture_for(app, window, frames_dir, index, 1.5, fps)

        backend.agent_status = "idle"
        window._log("Demo：idle — 本轮已完成，不再发送 Enter")
        index = capture_for(app, window, frames_dir, index, 2.0, fps)

        app.processEvents()
        final_frame = window.grab()
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
                    "fps=10,scale=800:-1:flags=lanczos,split[gif_src][palette_src];"
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
