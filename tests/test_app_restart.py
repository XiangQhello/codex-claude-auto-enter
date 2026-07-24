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

from app import (
    AGENT_STATUS_NOTICE,
    MainWindow,
    TaskCard,
    TaskRuntime,
    TaskSettingsDialog,
)
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

    def test_edit_stopped_task_keeps_target_and_updates_schedule(self) -> None:
        self.runtime.state = "completed"
        updated = TaskConfig(
            TargetInfo("other", "其他终端", "test", "不应替换原目标"),
            interval_seconds=2.5,
            mode="repeat",
            stop_rule="duration",
            max_duration_seconds=120,
        )

        self.window._apply_task_config("task-1", updated)

        self.assertEqual(self.runtime.config.target, self.target)
        self.assertEqual(self.runtime.config.interval_seconds, 2.5)
        self.assertEqual(self.runtime.config.max_duration_seconds, 120)
        self.assertEqual(self.runtime.state, "ready")
        self.assertIn("持续 2 分钟", self.card.schedule_label.text())
        self.assertFalse(self.card.restart_button.isHidden())

    def test_edit_running_task_restarts_with_new_config(self) -> None:
        self.runtime.state = "running"
        self.window._restart_task = Mock()
        updated = TaskConfig(
            self.target,
            interval_seconds=3,
            mode="repeat",
            stop_rule="count",
            max_count=8,
        )

        self.window._apply_task_config("task-1", updated)

        self.assertEqual(self.runtime.config.max_count, 8)
        self.assertIn("共 8 次", self.card.schedule_label.text())
        self.window._restart_task.assert_called_once_with("task-1")

    def test_settings_dialog_builds_once_config(self) -> None:
        dialog = TaskSettingsDialog(self.config)
        dialog.mode_combo.setCurrentIndex(dialog.mode_combo.findData("once"))
        dialog.interval_spin.setValue(4)
        dialog.interval_unit.setCurrentText("秒")

        updated = dialog.task_config()

        self.assertEqual(updated.target, self.target)
        self.assertEqual(updated.interval_seconds, 4)
        self.assertEqual(updated.mode, "once")
        self.assertEqual(updated.max_count, 1)

    def test_settings_dialog_builds_agent_completion_config(self) -> None:
        dialog = TaskSettingsDialog(self.config, auto_stop_available=True)
        dialog.stop_combo.setCurrentIndex(dialog.stop_combo.findData("agent"))

        updated = dialog.task_config()

        self.assertEqual(updated.stop_rule, "agent")
        self.assertIsNone(updated.max_count)
        self.assertIsNone(updated.max_duration_seconds)

    def test_agent_completed_card_is_safe_to_restart(self) -> None:
        config = TaskConfig(
            self.target,
            interval_seconds=1,
            mode="repeat",
            stop_rule="agent",
        )
        card = TaskCard("agent-task", config)

        card.finish("agent_completed", 2)

        self.assertEqual(card.status_label.text(), "AI 已完成")
        self.assertTrue(card.restart_button.isEnabled())

    def test_global_agent_poll_interval_is_editable(self) -> None:
        self.assertEqual(self.window.agent_poll_interval_seconds, 1.0)

        self.window.agent_poll_interval_spin.setValue(2.5)

        self.assertEqual(self.window.agent_poll_interval_seconds, 2.5)

    def test_agent_status_limit_is_visible_in_main_window_and_settings(self) -> None:
        self.assertEqual(self.window.agent_capability_hint.text(), AGENT_STATUS_NOTICE)

        dialog = TaskSettingsDialog(self.config)

        self.assertEqual(dialog.agent_capability_hint.text(), AGENT_STATUS_NOTICE)


if __name__ == "__main__":
    unittest.main()
