from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field

try:
    from .managed_workspace import create_managed_target_provider
except ImportError:
    create_managed_target_provider = None


class BackendError(RuntimeError):
    """可直接显示给用户的平台后端错误。"""


class TargetClosedError(BackendError):
    """目标窗口已经不存在。"""


@dataclass(frozen=True)
class TargetInfo:
    key: str
    title: str
    platform_name: str
    detail: str
    metadata: dict[str, str] = field(default_factory=dict)


class BaseBackend:
    platform_name = "未知平台"
    capability = ""
    managed_target_name = ""
    window_selection_available = True

    def check_environment(self) -> None:
        raise NotImplementedError

    def select_target(self) -> TargetInfo:
        raise NotImplementedError

    def target_exists(self, target: TargetInfo) -> bool:
        raise NotImplementedError

    def send_enter(self, target: TargetInfo) -> None:
        raise NotImplementedError

    def list_managed_targets(self) -> list[TargetInfo]:
        return []


class LinuxX11Backend(BaseBackend):
    platform_name = "Linux X11"
    capability = "完整后台模式：不抬起目标窗口，不改变当前活动窗口"

    def __init__(self) -> None:
        self.xdotool = shutil.which("xdotool")
        self.xprop = shutil.which("xprop")
        self.xwininfo = shutil.which("xwininfo")
        self.managed_provider = (
            create_managed_target_provider()
            if create_managed_target_provider is not None
            else None
        )
        if self.managed_provider:
            self.managed_target_name = self.managed_provider.display_name
            self.capability = self.managed_provider.capability
        self._send_lock = threading.Lock()

    def _run(
        self,
        *args: str,
        timeout: float | None = 3.0,
        check: bool = True,
    ) -> str:
        if not self.xdotool:
            raise BackendError("没有找到 xdotool，请先运行一键安装脚本。")
        try:
            result = subprocess.run(
                [self.xdotool, *args],
                text=True,
                capture_output=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise BackendError(f"X11 操作超时：{' '.join(args)}") from exc
        if check and result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip() or "未知 X11 错误"
            raise BackendError(detail)
        return result.stdout.strip()

    def check_environment(self) -> None:
        if os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland":
            if self.managed_provider and self.managed_provider.works_without_window_injection:
                self.window_selection_available = False
                self.platform_name = "Linux · 托管终端"
                self.capability = self.managed_provider.wayland_capability
                return
            raise BackendError(
                "当前是 Wayland 会话。Wayland 禁止应用向任意后台窗口注入按键；"
                "请在登录界面选择 X11/Xorg 会话。"
            )
        if not os.environ.get("DISPLAY"):
            if self.managed_provider and self.managed_provider.works_without_window_injection:
                self.window_selection_available = False
                return
            raise BackendError("没有检测到 X11 DISPLAY，请从图形桌面启动。")
        if not self.xdotool:
            if self.managed_provider and self.managed_provider.works_without_window_injection:
                self.window_selection_available = False
                return
            raise BackendError("没有找到 xdotool，请运行一键安装脚本。")
        self._run("getmouselocation")

    def list_managed_targets(self) -> list[TargetInfo]:
        if not self.managed_provider:
            return []
        try:
            return self.managed_provider.list_targets(TargetInfo)
        except RuntimeError as exc:
            raise BackendError(str(exc)) from exc

    def _xprop_has_wm_state(self, window_id: str) -> bool:
        if not self.xprop:
            return False
        try:
            result = subprocess.run(
                [self.xprop, "-id", window_id, "WM_STATE"],
                text=True,
                capture_output=True,
                timeout=2,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return False
        output = result.stdout.lower()
        return result.returncode == 0 and "not found" not in output and "wm_state" in output

    def _parent_window_id(self, window_id: str) -> str:
        if not self.xwininfo:
            return ""
        try:
            result = subprocess.run(
                [self.xwininfo, "-id", window_id],
                text=True,
                capture_output=True,
                timeout=2,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return ""
        if result.returncode != 0:
            return ""
        match = re.search(r"Parent window id:\s+(0x[0-9a-fA-F]+)", result.stdout)
        if not match:
            return ""
        return str(int(match.group(1), 16))

    def _top_level_window_id(self, selected_id: str) -> str:
        current = selected_id
        for _ in range(16):
            if self._xprop_has_wm_state(current):
                return current
            parent = self._parent_window_id(current)
            if not parent or parent == current or parent == "0":
                break
            current = parent
        return selected_id

    def _window_title(self, window_id: str) -> str:
        title = self._run("getwindowname", window_id, check=False)
        return " ".join(title.split()) or "未命名终端"

    def _window_class(self, window_id: str) -> str:
        if not self.xprop:
            return ""
        try:
            result = subprocess.run(
                [self.xprop, "-id", window_id, "WM_CLASS"],
                text=True,
                capture_output=True,
                timeout=3,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return ""
        return result.stdout.strip() if result.returncode == 0 else ""

    def select_target(self) -> TargetInfo:
        if not self.window_selection_available:
            suffix = (
                f"，请改用 {self.managed_target_name}"
                if self.managed_target_name
                else ""
            )
            raise BackendError(f"当前环境不能点击选择普通窗口{suffix}。")
        selected_id = self._run("selectwindow", timeout=None)
        if not selected_id.isdigit():
            raise BackendError("没有取得有效的窗口 ID。")
        window_id = self._top_level_window_id(selected_id)
        if not self._window_exists_by_id(window_id):
            raise BackendError("选中的窗口已经关闭。")
        title = self._window_title(window_id)
        window_class = self._window_class(window_id)
        detail = f"窗口 ID {window_id}"
        if selected_id != window_id:
            detail = f"{detail} · 已从内部控件 {selected_id} 提升到主窗口"
        if window_class:
            detail = f"{detail} · {window_class}"
        return TargetInfo(
            key=window_id,
            title=title,
            platform_name=self.platform_name,
            detail=detail,
            metadata={
                "window_id": window_id,
                "selected_window_id": selected_id,
                "window_class": window_class,
            },
        )

    def _window_exists_by_id(self, window_id: str) -> bool:
        try:
            self._run("getwindowgeometry", window_id)
        except BackendError:
            return False
        return True

    def target_exists(self, target: TargetInfo) -> bool:
        if self.managed_provider and self.managed_provider.handles(target):
            return self.managed_provider.target_exists(target)
        return self._window_exists_by_id(target.metadata.get("window_id", target.key))

    def _safe_window_id(self, command: str) -> str:
        value = self._run(command, check=False)
        return value if value.isdigit() else ""

    def send_enter(self, target: TargetInfo) -> None:
        if self.managed_provider and self.managed_provider.handles(target):
            with self._send_lock:
                try:
                    self.managed_provider.send_enter(target)
                except RuntimeError as exc:
                    raise BackendError(str(exc)) from exc
            return

        window_id = target.metadata.get("window_id", target.key)
        with self._send_lock:
            if not self._window_exists_by_id(window_id):
                raise TargetClosedError("目标终端已经关闭。")

            previous_focus = self._safe_window_id("getwindowfocus")
            previous_active = self._safe_window_id("getactivewindow")
            restore_id = previous_focus
            if (
                restore_id in {"", "1"}
                or not self._window_exists_by_id(restore_id)
            ):
                restore_id = previous_active

            send_error: BackendError | None = None
            try:
                # windowfocus 只改变 X 键盘焦点，不抬起窗口，也不改变活动窗口。
                self._run("windowfocus", "--sync", window_id, timeout=2.0)
                self._run("key", "--clearmodifiers", "Return", timeout=2.0)
            except BackendError as exc:
                send_error = exc
            finally:
                if (
                    restore_id
                    and restore_id != window_id
                    and self._window_exists_by_id(restore_id)
                ):
                    try:
                        self._run("windowfocus", "--sync", restore_id, timeout=2.0)
                    except BackendError:
                        pass

            if send_error is not None:
                raise send_error


class WindowsBackend(BaseBackend):
    platform_name = "Windows"
    capability = "后台窗口消息模式：不切换前台；终端需接受 Win32 键盘消息"

    VK_LBUTTON = 0x01
    VK_RETURN = 0x0D
    WM_KEYDOWN = 0x0100
    WM_KEYUP = 0x0101
    GA_ROOT = 2

    def __init__(self) -> None:
        import ctypes
        from ctypes import wintypes

        self.ctypes = ctypes
        self.wintypes = wintypes
        self.user32 = ctypes.windll.user32
        self._send_lock = threading.Lock()

        self.user32.GetAsyncKeyState.argtypes = [wintypes.INT]
        self.user32.GetAsyncKeyState.restype = wintypes.SHORT
        self.user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
        self.user32.GetCursorPos.restype = wintypes.BOOL
        self.user32.WindowFromPoint.argtypes = [wintypes.POINT]
        self.user32.WindowFromPoint.restype = wintypes.HWND
        self.user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
        self.user32.GetAncestor.restype = wintypes.HWND
        self.user32.IsWindow.argtypes = [wintypes.HWND]
        self.user32.IsWindow.restype = wintypes.BOOL
        self.user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
        self.user32.GetWindowTextLengthW.restype = ctypes.c_int
        self.user32.GetWindowTextW.argtypes = [
            wintypes.HWND,
            wintypes.LPWSTR,
            ctypes.c_int,
        ]
        self.user32.GetWindowTextW.restype = ctypes.c_int
        self.user32.GetClassNameW.argtypes = [
            wintypes.HWND,
            wintypes.LPWSTR,
            ctypes.c_int,
        ]
        self.user32.GetClassNameW.restype = ctypes.c_int
        self.user32.PostMessageW.argtypes = [
            wintypes.HWND,
            wintypes.UINT,
            wintypes.WPARAM,
            wintypes.LPARAM,
        ]
        self.user32.PostMessageW.restype = wintypes.BOOL

    def check_environment(self) -> None:
        return

    def _title(self, hwnd: int) -> str:
        length = self.user32.GetWindowTextLengthW(hwnd)
        buffer = self.ctypes.create_unicode_buffer(max(length + 1, 2))
        self.user32.GetWindowTextW(hwnd, buffer, len(buffer))
        return buffer.value.strip() or "未命名终端"

    def _class_name(self, hwnd: int) -> str:
        buffer = self.ctypes.create_unicode_buffer(256)
        self.user32.GetClassNameW(hwnd, buffer, len(buffer))
        return buffer.value.strip()

    def select_target(self) -> TargetInfo:
        point = self.wintypes.POINT()
        while self.user32.GetAsyncKeyState(self.VK_LBUTTON) & 0x8000:
            time.sleep(0.03)
        while not (self.user32.GetAsyncKeyState(self.VK_LBUTTON) & 0x8000):
            time.sleep(0.03)
        self.user32.GetCursorPos(self.ctypes.byref(point))
        clicked_hwnd = int(self.user32.WindowFromPoint(point))
        root_hwnd = int(self.user32.GetAncestor(clicked_hwnd, self.GA_ROOT))
        while self.user32.GetAsyncKeyState(self.VK_LBUTTON) & 0x8000:
            time.sleep(0.03)

        if not root_hwnd or not self.user32.IsWindow(root_hwnd):
            raise BackendError("没有取得有效的 Windows 窗口句柄。")
        title = self._title(root_hwnd)
        class_name = self._class_name(clicked_hwnd) or self._class_name(root_hwnd)
        return TargetInfo(
            key=str(root_hwnd),
            title=title,
            platform_name=self.platform_name,
            detail=f"HWND {root_hwnd} · {class_name or '未知窗口类'}",
            metadata={
                "root_hwnd": str(root_hwnd),
                "input_hwnd": str(clicked_hwnd or root_hwnd),
                "window_class": class_name,
            },
        )

    def target_exists(self, target: TargetInfo) -> bool:
        hwnd = int(target.metadata.get("root_hwnd", target.key))
        return bool(self.user32.IsWindow(hwnd))

    def send_enter(self, target: TargetInfo) -> None:
        root_hwnd = int(target.metadata.get("root_hwnd", target.key))
        input_hwnd = int(target.metadata.get("input_hwnd", root_hwnd))
        if not self.user32.IsWindow(root_hwnd):
            raise TargetClosedError("目标终端已经关闭。")

        key_down_lparam = 1 | (0x1C << 16)
        key_up_lparam = key_down_lparam | (1 << 30) | (1 << 31)
        candidates = [input_hwnd]
        if root_hwnd != input_hwnd:
            candidates.append(root_hwnd)

        with self._send_lock:
            for hwnd in candidates:
                if not self.user32.IsWindow(hwnd):
                    continue
                down_ok = self.user32.PostMessageW(
                    hwnd, self.WM_KEYDOWN, self.VK_RETURN, key_down_lparam
                )
                up_ok = self.user32.PostMessageW(
                    hwnd, self.WM_KEYUP, self.VK_RETURN, key_up_lparam
                )
                if down_ok and up_ok:
                    return
        raise BackendError("Windows 后台键盘消息发送失败。")


class MacOSBackend(BaseBackend):
    platform_name = "macOS"
    capability = "后台进程投递模式：需要在系统设置中授予辅助功能权限"

    def __init__(self) -> None:
        try:
            import Quartz
        except ImportError as exc:
            raise BackendError(
                "缺少 macOS Quartz 支持，请运行一键安装脚本。"
            ) from exc
        self.Quartz = Quartz
        self._send_lock = threading.Lock()

    def check_environment(self) -> None:
        if hasattr(self.Quartz, "AXIsProcessTrusted"):
            if not self.Quartz.AXIsProcessTrusted():
                raise BackendError(
                    "请在“系统设置 → 隐私与安全性 → 辅助功能”中允许本工具控制电脑。"
                )

    def _windows(self) -> list[dict[object, object]]:
        options = (
            self.Quartz.kCGWindowListOptionOnScreenOnly
            | self.Quartz.kCGWindowListExcludeDesktopElements
        )
        return list(
            self.Quartz.CGWindowListCopyWindowInfo(
                options, self.Quartz.kCGNullWindowID
            )
            or []
        )

    def select_target(self) -> TargetInfo:
        q = self.Quartz
        state = q.kCGEventSourceStateCombinedSessionState
        button = q.kCGMouseButtonLeft
        while q.CGEventSourceButtonState(state, button):
            time.sleep(0.03)
        while not q.CGEventSourceButtonState(state, button):
            time.sleep(0.03)
        event = q.CGEventCreate(None)
        point = q.CGEventGetLocation(event)
        while q.CGEventSourceButtonState(state, button):
            time.sleep(0.03)

        for info in self._windows():
            if int(info.get(q.kCGWindowLayer, 0)) != 0:
                continue
            pid = int(info.get(q.kCGWindowOwnerPID, 0))
            if pid == os.getpid():
                continue
            bounds = info.get(q.kCGWindowBounds, {})
            x = float(bounds.get("X", 0))
            y = float(bounds.get("Y", 0))
            width = float(bounds.get("Width", 0))
            height = float(bounds.get("Height", 0))
            if x <= point.x <= x + width and y <= point.y <= y + height:
                window_id = int(info.get(q.kCGWindowNumber, 0))
                owner = str(info.get(q.kCGWindowOwnerName, "终端"))
                name = str(info.get(q.kCGWindowName, "")).strip()
                title = name or owner
                return TargetInfo(
                    key=str(window_id),
                    title=title,
                    platform_name=self.platform_name,
                    detail=f"窗口 {window_id} · 进程 {owner}（PID {pid}）",
                    metadata={"window_id": str(window_id), "pid": str(pid)},
                )
        raise BackendError("没有找到鼠标点击位置对应的窗口。")

    def target_exists(self, target: TargetInfo) -> bool:
        window_id = int(target.metadata.get("window_id", target.key))
        q = self.Quartz
        return any(int(info.get(q.kCGWindowNumber, 0)) == window_id for info in self._windows())

    def send_enter(self, target: TargetInfo) -> None:
        if not self.target_exists(target):
            raise TargetClosedError("目标终端已经关闭。")
        pid = int(target.metadata.get("pid", "0"))
        if pid <= 0 or not hasattr(self.Quartz, "CGEventPostToPid"):
            raise BackendError("当前 macOS 版本不支持按进程后台投递键盘事件。")
        with self._send_lock:
            down = self.Quartz.CGEventCreateKeyboardEvent(None, 36, True)
            up = self.Quartz.CGEventCreateKeyboardEvent(None, 36, False)
            self.Quartz.CGEventPostToPid(pid, down)
            self.Quartz.CGEventPostToPid(pid, up)


def create_backend() -> BaseBackend:
    if sys.platform.startswith("linux"):
        return LinuxX11Backend()
    if sys.platform == "win32":
        return WindowsBackend()
    if sys.platform == "darwin":
        return MacOSBackend()
    raise BackendError(f"暂不支持当前操作系统：{sys.platform}")
