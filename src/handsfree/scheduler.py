from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Callable

from .backends import BackendError, TargetClosedError, TargetInfo


@dataclass(frozen=True)
class TaskConfig:
    target: TargetInfo
    interval_seconds: float
    mode: str
    stop_rule: str
    max_count: int | None = None
    max_duration_seconds: float | None = None


EventCallback = Callable[[dict[str, object]], None]
SendCallback = Callable[[TargetInfo], None]
CompletionCheck = Callable[[], bool]
CompletionCheckInterval = Callable[[], float]


def describe_task(config: TaskConfig) -> str:
    interval = format_duration(config.interval_seconds)
    if config.mode == "once":
        return f"等待 {interval}后按一次"
    if config.stop_rule == "agent":
        return f"每 {interval}一次 · AI 任务完成后停止"
    if config.stop_rule == "manual":
        return f"每 {interval}一次 · 手动停止"
    if config.stop_rule == "count":
        return f"每 {interval}一次 · 共 {config.max_count} 次"
    return f"每 {interval}一次 · 持续 {format_duration(config.max_duration_seconds or 0)}"


def format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:g} 秒"
    if seconds < 3600 and seconds % 60 == 0:
        return f"{seconds / 60:g} 分钟"
    if seconds >= 3600 and seconds % 3600 == 0:
        return f"{seconds / 3600:g} 小时"
    return f"{seconds:g} 秒"


def run_schedule(
    config: TaskConfig,
    stop_event: threading.Event,
    send_enter: SendCallback,
    emit: EventCallback,
    completion_check: CompletionCheck | None = None,
    completion_check_interval: CompletionCheckInterval | None = None,
) -> None:
    started = time.monotonic()
    next_due = started + config.interval_seconds
    deadline = (
        started + config.max_duration_seconds
        if config.max_duration_seconds is not None
        else None
    )
    count = 0
    # Herdr 状态查询是跨进程调用，不需要在调度器的 100ms 唤醒频率下重复执行。
    # 间隔由界面中的全局设置提供；发送按键前仍会强制再检查一次。
    last_completion_check: float | None = None
    emit({"kind": "started", "count": 0})

    def current_completion_check_interval() -> float:
        value = completion_check_interval() if completion_check_interval else 1.0
        return min(10.0, max(0.5, float(value)))

    def completion_requires_stop() -> bool:
        if completion_check is None:
            return False
        try:
            completed = completion_check()
        except BackendError as exc:
            emit(
                {
                    "kind": "finished",
                    "reason": "error",
                    "count": count,
                    "detail": f"AI 状态监控失败：{exc}",
                }
            )
            return True
        if not completed:
            return False
        emit(
            {
                "kind": "finished",
                "reason": "agent_completed",
                "count": count,
            }
        )
        return True

    while True:
        if stop_event.is_set():
            emit({"kind": "finished", "reason": "stopped", "count": count})
            return

        now = time.monotonic()
        if completion_check is not None and (
            last_completion_check is None
            or now - last_completion_check >= current_completion_check_interval()
        ):
            last_completion_check = now
            if completion_requires_stop():
                return
        if deadline is not None and now >= deadline and next_due > deadline:
            emit({"kind": "finished", "reason": "duration", "count": count})
            return

        if deadline is not None and next_due > deadline:
            next_in: float | None = None
            wake_at = deadline
        else:
            next_in = max(0.0, next_due - now)
            wake_at = next_due
        emit(
            {
                "kind": "tick",
                "count": count,
                "elapsed": now - started,
                "next_in": next_in,
                "duration": config.max_duration_seconds,
            }
        )

        wait_time = max(0.0, min(0.1, wake_at - now))
        if wait_time > 0:
            stop_event.wait(wait_time)
            continue

        now = time.monotonic()
        if deadline is not None and next_due > deadline and now >= deadline:
            emit({"kind": "finished", "reason": "duration", "count": count})
            return
        if now < next_due:
            continue

        # 即使上一轮状态探测刚刚发生，真正注入按键前仍再确认一次，尽量缩小
        # “刚检查还是 working、下一瞬间已经 idle”造成的误发送窗口。
        if completion_check is not None:
            last_completion_check = now
            if completion_requires_stop():
                return

        try:
            send_enter(config.target)
        except TargetClosedError as exc:
            emit(
                {
                    "kind": "finished",
                    "reason": "target_closed",
                    "count": count,
                    "detail": str(exc),
                }
            )
            return
        except BackendError as exc:
            emit(
                {
                    "kind": "finished",
                    "reason": "error",
                    "count": count,
                    "detail": str(exc),
                }
            )
            return

        count += 1
        emit({"kind": "sent", "count": count})

        if config.mode == "once":
            emit({"kind": "finished", "reason": "completed", "count": count})
            return
        if config.max_count is not None and count >= config.max_count:
            emit({"kind": "finished", "reason": "completed", "count": count})
            return

        now = time.monotonic()
        if deadline is not None and now >= deadline:
            emit({"kind": "finished", "reason": "duration", "count": count})
            return
        next_due = now + config.interval_seconds
