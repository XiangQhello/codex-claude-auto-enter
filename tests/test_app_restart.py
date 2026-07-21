from __future__ import annotations

import os
from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import Mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from PyQt5.QtWidgets import QApplication

from app import MainWindow, TaskCard, TaskRuntime
from handsfree.backends import BaseBackend, TargetInfo
from handsfree.scheduler import TaskConfig


class FakeBackend(BaseBackend):
    platform_name = "测试平台"
    capability = "测试后端"

    def target_exists(self, target: TargetInfo) -> bool:
        return True

    def send_enter(self, target: TargetInfo) -> None:
        return None


class RestartTaskTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.target = TargetInfo("terminal-1", "终端一", "test", "测试终端")
        self.config = TaskConfig(
            self.target,
            interval_seconds=1,
            mode="repeat",
            stop_rule="count",
            max_count=3,
        )
        self.window = MainWindow(FakeBackend())
        self.card = TaskCard("task-1", self.config)
        self.runtime = TaskRuntime(
            config=self.config,
            card=self.card,
            stop_event=threading.Event(),
        )
        self.window.tasks["task-1"] = self.runtime

    def tearDown(self) -> None:
        self.runtime.state = "completed"
        self.window.close()

    def test_running_task_queues_safe_restart(self) -> None:
        self.runtime.state = "running"
        self.card.set_running()

        self.window._restart_task("task-1")

        self.assertEqual(self.runtime.state, "stopping")
        self.assertTrue(self.runtime.restart_pending)
        self.assertTrue(self.runtime.stop_event.is_set())
        self.assertEqual(self.card.status_label.text(), "正在重启")

    def test_finished_event_starts_pending_restart(self) -> None:
        self.runtime.state = "stopping"
        self.runtime.restart_pending = True
        self.runtime.generation = 4
        self.window._start_task = Mock()

        self.window._handle_task_event(
            "task-1",
            4,
            {"kind": "finished", "reason": "stopped", "count": 2},
        )

        self.window._start_task.assert_called_once_with("task-1")
        self.assertFalse(self.runtime.restart_pending)

    def test_stop_all_cancels_pending_restart(self) -> None:
        self.runtime.state = "stopping"
        self.runtime.restart_pending = True

        self.window._stop_all()

        self.assertFalse(self.runtime.restart_pending)
        self.assertEqual(self.card.status_label.text(), "正在停止")

    def test_completed_card_offers_restart(self) -> None:
        self.card.set_running()
        self.card.finish("completed", 3)

        self.assertFalse(self.card.restart_button.isHidden())
        self.assertTrue(self.card.restart_button.isEnabled())
        self.assertTrue(self.card.start_button.isHidden())


if __name__ == "__main__":
    unittest.main()
