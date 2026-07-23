from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from handsfree.backends import BackendError, LinuxX11Backend, TargetInfo


class LinuxBackendTests(unittest.TestCase):
    def test_promotes_clicked_child_to_managed_window(self) -> None:
        backend = LinuxX11Backend()
        backend._xprop_has_wm_state = Mock(side_effect=[False, False, True])
        backend._parent_window_id = Mock(side_effect=["200", "300"])

        self.assertEqual(backend._top_level_window_id("100"), "300")

    def test_completion_monitoring_only_supports_known_ai_agents(self) -> None:
        backend = LinuxX11Backend()
        backend.managed_provider = Mock()
        backend.managed_provider.handles.return_value = True
        codex = TargetInfo(
            "herdr:w1:p1",
            "Codex",
            "Herdr",
            "pane",
            metadata={"transport": "herdr", "agent": "Codex"},
        )
        shell = TargetInfo(
            "herdr:w1:p2",
            "Shell",
            "Herdr",
            "pane",
            metadata={"transport": "herdr", "agent": "终端"},
        )

        self.assertTrue(backend.supports_completion_monitoring(codex))
        self.assertFalse(backend.supports_completion_monitoring(shell))

        backend.managed_provider.target_is_idle.side_effect = RuntimeError(
            "status unavailable"
        )
        completion_check = backend.completion_check(codex)
        self.assertIsNotNone(completion_check)
        with self.assertRaises(BackendError):
            completion_check()


if __name__ == "__main__":
    unittest.main()
