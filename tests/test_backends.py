from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from handsfree.backends import LinuxX11Backend


class LinuxBackendTests(unittest.TestCase):
    def test_promotes_clicked_child_to_managed_window(self) -> None:
        backend = LinuxX11Backend()
        backend._xprop_has_wm_state = Mock(side_effect=[False, False, True])
        backend._parent_window_id = Mock(side_effect=["200", "300"])

        self.assertEqual(backend._top_level_window_id("100"), "300")


if __name__ == "__main__":
    unittest.main()
