from __future__ import annotations

import json
import os
import shutil
import subprocess
from typing import Callable


class ManagedWorkspaceProvider:
    display_name = "Herdr AI Agent / Pane"
    capability = "普通终端使用 X11 后台发送；Herdr Pane 使用官方 API 定向发送"
    wayland_capability = "Wayland 下通过 Herdr 官方 API 定向发送回车"
    works_without_window_injection = True

    def __init__(self, executable: str) -> None:
        self.executable = executable

    def _run(self, *args: str, timeout: float = 4.0) -> dict:
        try:
            result = subprocess.run(
                [self.executable, *args],
                text=True,
                capture_output=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("Herdr 操作超时。") from exc
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip() or "未知 Herdr 错误"
            raise RuntimeError(detail)
        if not result.stdout.strip():
            return {}
        for line in reversed(result.stdout.splitlines()):
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                if isinstance(payload.get("error"), dict):
                    message = payload["error"].get("message", "Herdr 操作失败")
                    raise RuntimeError(str(message))
                return payload
        raise RuntimeError("Herdr 返回了无法识别的数据。")

    def handles(self, target) -> bool:
        return target.metadata.get("transport") == "herdr"

    @staticmethod
    def _agent_name(pane: dict) -> str:
        raw_agent = str(pane.get("agent") or "").strip()
        candidates = " ".join(
            str(pane.get(key) or "")
            for key in ("agent", "process_name", "terminal_title_stripped", "label")
        ).lower()
        if raw_agent.lower() == "codex" or "codex" in candidates:
            return "Codex"
        if raw_agent.lower() in {"claude", "claude-code", "claude code"} or (
            "claude" in candidates
        ):
            return "Claude Code"
        return raw_agent or "终端"

    def list_targets(self, target_factory: Callable) -> list:
        payload = self._run("pane", "list")
        panes = payload.get("result", {}).get("panes", [])
        targets = []
        for pane in panes:
            if not isinstance(pane, dict):
                continue
            pane_id = str(pane.get("pane_id", "")).strip()
            if not pane_id:
                continue
            cwd = str(pane.get("foreground_cwd") or pane.get("cwd") or "")
            short_cwd = os.path.basename(cwd.rstrip(os.sep)) or cwd or "未知目录"
            label = str(
                pane.get("label")
                or pane.get("terminal_title_stripped")
                or short_cwd
                or pane_id
            ).strip()
            agent = self._agent_name(pane)
            status = str(pane.get("agent_status") or "unknown").strip()
            focus_mark = "当前 · " if pane.get("focused") else ""
            targets.append(
                target_factory(
                    key=f"herdr:{pane_id}",
                    title=f"{label} · {agent}",
                    platform_name="Herdr",
                    detail=(
                        f"{focus_mark}Herdr Pane {pane_id} · {status} · "
                        f"{cwd or '未知目录'}"
                    ),
                    metadata={
                        "transport": "herdr",
                        "pane_id": pane_id,
                        "terminal_id": str(pane.get("terminal_id", "")),
                        "workspace_id": str(pane.get("workspace_id", "")),
                        "tab_id": str(pane.get("tab_id", "")),
                        "cwd": cwd,
                        "agent": agent,
                        "status": status,
                        "focused": "true" if pane.get("focused") else "false",
                    },
                )
            )
        if not targets:
            raise RuntimeError("Herdr 当前没有可选择的 Pane。")
        return targets

    def target_exists(self, target) -> bool:
        pane_id = target.metadata.get("pane_id", "")
        try:
            self._run("pane", "get", pane_id)
        except RuntimeError:
            return False
        return True

    def target_status(self, target) -> str | None:
        """Return Herdr's live agent status."""
        pane_id = target.metadata.get("pane_id", "")
        if not pane_id:
            raise RuntimeError("Herdr 目标缺少 Pane ID。")
        payload = self._run("pane", "get", pane_id)
        result = payload.get("result", {})
        if not isinstance(result, dict):
            raise RuntimeError("Herdr 没有返回有效的 Pane 状态。")
        pane = result.get("pane", {})
        if not isinstance(pane, dict):
            raise RuntimeError("Herdr 没有返回有效的 Pane 状态。")
        status = str(pane.get("agent_status") or "").strip().lower()
        return status or None

    def target_is_idle(self, target) -> bool:
        # Herdr uses blocked for questions/approval prompts. Those still need Enter;
        # idle is the terminal state after the current agent turn has completed.
        status = self.target_status(target)
        if status == "idle":
            return True
        if status in {"working", "blocked"}:
            return False
        raise RuntimeError(f"无法确认 AI 任务状态（{status or 'unknown'}）。")

    def send_enter(self, target) -> None:
        pane_id = target.metadata.get("pane_id", "")
        if not pane_id:
            raise RuntimeError("Herdr 目标缺少 Pane ID。")
        self._run("pane", "send-keys", pane_id, "enter")


def create_managed_target_provider() -> ManagedWorkspaceProvider | None:
    executable = shutil.which("herdr")
    if not executable:
        local_executable = os.path.expanduser("~/.local/bin/herdr")
        if os.path.isfile(local_executable) and os.access(local_executable, os.X_OK):
            executable = local_executable
    return ManagedWorkspaceProvider(executable) if executable else None
