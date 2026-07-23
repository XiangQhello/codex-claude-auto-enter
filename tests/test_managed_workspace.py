from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, call, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from handsfree.backends import TargetInfo
from handsfree.managed_workspace import ManagedWorkspaceProvider


class ManagedWorkspaceTests(unittest.TestCase):
    @patch("handsfree.managed_workspace.subprocess.run")
    def test_accepts_empty_success_output(self, run: Mock) -> None:
        run.return_value = Mock(returncode=0, stdout="", stderr="")
        provider = ManagedWorkspaceProvider("/fake/herdr")

        self.assertEqual(provider._run("pane", "send-keys", "w1:p7", "enter"), {})

    def test_lists_panes_as_targets(self) -> None:
        provider = ManagedWorkspaceProvider("/fake/herdr")
        provider._run = Mock(
            return_value={
                "result": {
                    "panes": [
                        {
                            "pane_id": "w1:p7",
                            "terminal_id": "term-7",
                            "workspace_id": "w1",
                            "tab_id": "w1:t3",
                            "cwd": "/work/demo",
                            "foreground_cwd": "/work/demo",
                            "label": "简单任务",
                            "agent": "codex",
                            "agent_status": "blocked",
                            "focused": True,
                        }
                    ]
                }
            }
        )

        targets = provider.list_targets(TargetInfo)

        self.assertEqual(len(targets), 1)
        self.assertEqual(targets[0].key, "herdr:w1:p7")
        self.assertEqual(targets[0].metadata["pane_id"], "w1:p7")
        self.assertIn("Codex", targets[0].title)
        self.assertEqual(targets[0].metadata["focused"], "true")
        self.assertIn("简单任务", targets[0].title)

    def test_recognizes_claude_code_from_agent(self) -> None:
        provider = ManagedWorkspaceProvider("/fake/herdr")
        provider._run = Mock(
            return_value={
                "result": {
                    "panes": [
                        {
                            "pane_id": "w2:p3",
                            "label": "review",
                            "agent": "claude",
                            "agent_status": "working",
                            "cwd": "/workspace/project",
                        }
                    ]
                }
            }
        )

        targets = provider.list_targets(TargetInfo)

        self.assertIn("Claude Code", targets[0].title)
        self.assertEqual(targets[0].metadata["agent"], "Claude Code")

    def test_recognizes_claude_code_from_title_without_agent_field(self) -> None:
        provider = ManagedWorkspaceProvider("/fake/herdr")
        provider._run = Mock(
            return_value={
                "result": {
                    "panes": [
                        {
                            "pane_id": "w2:p4",
                            "terminal_title_stripped": "Claude Code",
                            "agent_status": "idle",
                            "cwd": "/workspace/project",
                        }
                    ]
                }
            }
        )

        targets = provider.list_targets(TargetInfo)

        self.assertIn("Claude Code", targets[0].title)

    def test_sends_enter_through_provider(self) -> None:
        provider = ManagedWorkspaceProvider("/fake/herdr")
        provider._run = Mock(return_value={"result": {}})
        target = TargetInfo(
            key="herdr:w1:p7",
            title="Codex",
            platform_name="Herdr",
            detail="Herdr Pane w1:p7",
            metadata={"transport": "herdr", "pane_id": "w1:p7"},
        )

        provider.send_enter(target)

        provider._run.assert_called_once_with(
            "pane", "send-keys", "w1:p7", "enter"
        )

    def test_reads_live_agent_status(self) -> None:
        provider = ManagedWorkspaceProvider("/fake/herdr")
        provider._run = Mock(
            return_value={"result": {"pane": {"agent_status": "idle"}}}
        )
        target = TargetInfo(
            key="herdr:w1:p7",
            title="Codex",
            platform_name="Herdr",
            detail="Herdr Pane w1:p7",
            metadata={"transport": "herdr", "pane_id": "w1:p7"},
        )

        self.assertEqual(provider.target_status(target), "idle")
        self.assertTrue(provider.target_is_idle(target))
        self.assertEqual(
            provider._run.call_args_list,
            [
                call("pane", "get", "w1:p7"),
                call("pane", "get", "w1:p7"),
            ],
        )

    def test_status_probe_failure_is_fail_closed(self) -> None:
        provider = ManagedWorkspaceProvider("/fake/herdr")
        provider._run = Mock(side_effect=RuntimeError("temporarily unavailable"))
        target = TargetInfo(
            key="herdr:w1:p7",
            title="Codex",
            platform_name="Herdr",
            detail="Herdr Pane w1:p7",
            metadata={"transport": "herdr", "pane_id": "w1:p7"},
        )

        with self.assertRaises(RuntimeError):
            provider.target_is_idle(target)


if __name__ == "__main__":
    unittest.main()
