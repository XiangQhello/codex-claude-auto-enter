from __future__ import annotations

import threading
import time
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from handsfree.backends import TargetInfo
from handsfree.scheduler import TaskConfig, run_schedule


class SchedulerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.target_a = TargetInfo("a", "终端 A", "test", "A")
        self.target_b = TargetInfo("b", "终端 B", "test", "B")

    def test_count_limit(self) -> None:
        sends: list[str] = []
        events: list[dict[str, object]] = []
        config = TaskConfig(
            self.target_a,
            interval_seconds=0.005,
            mode="repeat",
            stop_rule="count",
            max_count=3,
        )
        run_schedule(config, threading.Event(), lambda target: sends.append(target.key), events.append)
        self.assertEqual(sends, ["a", "a", "a"])
        self.assertEqual(events[-1]["reason"], "completed")
        self.assertEqual(events[-1]["count"], 3)

    def test_manual_stop(self) -> None:
        stop_event = threading.Event()
        events: list[dict[str, object]] = []

        def send_once(_: TargetInfo) -> None:
            stop_event.set()

        config = TaskConfig(
            self.target_a,
            interval_seconds=0.005,
            mode="repeat",
            stop_rule="manual",
        )
        run_schedule(config, stop_event, send_once, events.append)
        self.assertEqual(events[-1]["reason"], "stopped")
        self.assertEqual(events[-1]["count"], 1)

    def test_two_targets_run_in_parallel(self) -> None:
        sent: list[tuple[str, float]] = []
        sent_lock = threading.Lock()

        def sender(target: TargetInfo) -> None:
            with sent_lock:
                sent.append((target.key, time.monotonic()))

        configs = [
            TaskConfig(self.target_a, 0.01, "repeat", "count", max_count=4),
            TaskConfig(self.target_b, 0.015, "repeat", "count", max_count=3),
        ]
        threads = [
            threading.Thread(
                target=run_schedule,
                args=(config, threading.Event(), sender, lambda _: None),
            )
            for config in configs
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=2)

        self.assertFalse(any(thread.is_alive() for thread in threads))
        self.assertEqual(sum(key == "a" for key, _ in sent), 4)
        self.assertEqual(sum(key == "b" for key, _ in sent), 3)
        first_a = min(timestamp for key, timestamp in sent if key == "a")
        last_a = max(timestamp for key, timestamp in sent if key == "a")
        first_b = min(timestamp for key, timestamp in sent if key == "b")
        self.assertLess(first_b, last_a)
        self.assertLess(first_a, last_a)


if __name__ == "__main__":
    unittest.main()
